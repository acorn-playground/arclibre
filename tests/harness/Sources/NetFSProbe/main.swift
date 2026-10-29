// SPDX-License-Identifier: Apache-2.0
// An A440/1 client (Econet station 1) against a file server at station 254
// that runs on the host: an in-memory Acorn file server written here from the
// documented file-server protocol (the PRM's "File server protocol
// interface") and the NetFS client source. It is attached to the emulated
// line through MacArch's public EconetGateway, which hands it each frame of
// a transaction (scout, data) and puts its answers (acknowledgements, its own
// replies) on the line, one transaction at a time.
//
//   NetFSProbe ROM ROM_DIRECTORY OUTPUT SERVER MODE STEP...
//     SERVER   on | off (off: nothing answers for station 254)
//     MODE     cli (F12 command line) | desktop
//   Steps, in order:
//     WAIT:n               run n emulated seconds
//     F12                  press F12
//     KEY:n                press key number n (ArcKey code)
//     CLICK:x,y[,n]        select n times at OS coordinates x,y
//     MENU:x,y             menu button at x,y
//     MOVE:x,y             move the pointer
//     SHOT:name            save the screen as OUTPUT/name.png
//     WATCH:name           run until NetStatus shows a part-done percentage,
//                          then save that screen as name.png
//     TYPE:text            typed without Return
//     anything else        typed, then Return; at the command line, run until
//                          the prompt is back
// After each step the screen text is recorded. result.json has the steps,
// screens, every request the server answered, and the server's store before
// and after. No guest code injection or module loading: the client is driven
// by keyboard and mouse only; the guest is only read for assertions.
import Foundation
import ArchimedesCore
import ProbeSupport

// MARK: - The store

let fsDate: UInt16 = 0xDA4F                 // 15 Oct 2026 in the server's format
let stampHigh: UInt32 = 0x5D, stampLow: UInt32 = 0x2824_8300   // 15 Oct 2026 12:00 in centiseconds
var nextSIN: UInt32 = 0x100

final class Node {
 var name: String
 let isDir: Bool
 var load: UInt32 = 0, exec: UInt32 = 0
 var data: [UInt8] = []
 var access: UInt8
 var children: [Node] = []
 weak var parent: Node?
 let sin: UInt32
 var date: UInt16 = fsDate
 init(_ name: String, dir: Bool) {
  self.name = name; isDir = dir; access = dir ? 0x20 : 0x0D
  sin = nextSIN; nextSIN += 1
 }
 static func file(_ name: String, type: UInt32, _ data: [UInt8]) -> Node {
  let n = Node(name, dir: false); n.load = 0xFFF0_0000 | (type << 8) | stampHigh; n.exec = stampLow; n.data = data; return n
 }
 func add(_ n: Node) { n.parent = self; children.append(n); children.sort { $0.name.uppercased() < $1.name.uppercased() } }
 func remove(_ n: Node) { children.removeAll { $0 === n }; n.parent = nil }
 func child(_ name: String) -> Node? { children.first { $0.name.uppercased() == name.uppercased() } }
 var path: String { parent.map { $0.path + "." + name } ?? "$" }
 // FS format access: bits 0/1 public R/W, 2/3 owner R/W, 4 locked, 5 directory.
 var accessString: String {
  var s = isDir ? "D" : ""
  if access & 0x10 != 0 { s += "L" }
  if access & 0x08 != 0 { s += "W" }
  if access & 0x04 != 0 { s += "R" }
  s += "/"
  if access & 0x02 != 0 { s += "W" }
  if access & 0x01 != 0 { s += "R" }
  return s
 }
 var sectors: Int { isDir ? 2 + children.reduce(0) { $0 + $1.sectors } : 1 + (data.count + 255) / 256 }
 func dump() -> [String: Any] {
  var d: [String: Any] = ["name": name, "type": isDir ? "directory" : "file", "access": accessString, "sin": Int(sin)]
  if isDir { d["children"] = children.map { $0.dump() } }
  else { d["load"] = String(format: "%08X", load); d["exec"] = String(format: "%08X", exec); d["length"] = data.count; d["hex"] = data.map { String(format: "%02X", $0) }.joined() }
  return d
 }
}

struct FSError: Error { let code: UInt8; let text: String }
let notFound = FSError(code: 0xD6, text: "Not found")
let badName = FSError(code: 0xCC, text: "Bad name")
let channel = FSError(code: 0xDE, text: "Channel")
let whoAreYou = FSError(code: 0xBF, text: "Who are you?")
let badCommand = FSError(code: 0xFE, text: "Bad command")
let isAFile = FSError(code: 0xBD, text: "Is a file")
let isADir = FSError(code: 0xB5, text: "Is a directory")
let locked = FSError(code: 0xC3, text: "Locked")

// MARK: - The file server

final class OpenFile { let node: Node; var ptr = 0; let update: Bool; init(_ n: Node, update u: Bool) { node = n; update = u } }
enum Handle { case dir(Node), file(OpenFile) }
final class User { let name: String; var password: String; var boot: UInt8 = 0; let privileged: Bool
 init(_ n: String, _ p: String, privileged: Bool) { name = n; password = p; self.privileged = privileged } }
final class Session {
 let station: UInt8; let user: User; var urd: UInt8 = 0
 var handles: [UInt8: Handle] = [:]
 init(_ s: UInt8, _ u: User) { station = s; user = u }
 func alloc(_ h: Handle) throws -> UInt8 {
  guard let n = (1...255).first(where: { handles[UInt8($0)] == nil }) else { throw FSError(code: 0xC0, text: "Too many open files") }
  handles[UInt8(n)] = h; return UInt8(n)
 }
 func dir(_ h: UInt8) throws -> Node { if case .dir(let n)? = handles[h] { return n }; throw channel }
 func file(_ h: UInt8) throws -> OpenFile { if case .file(let f)? = handles[h] { return f }; throw channel }
}
struct Outbound { let station: UInt8; let port: UInt8; let payload: [UInt8]; let what: String; var tries = 0 }
final class Receiver {
 let station: UInt8, replyPort: UInt8, ackPort: UInt8, expected: Int
 var data: [UInt8] = []
 let finish: ([UInt8]) throws -> [UInt8]   // the final reply's data
 init(station: UInt8, replyPort: UInt8, ackPort: UInt8, expected: Int, finish: @escaping ([UInt8]) throws -> [UInt8]) {
  self.station = station; self.replyPort = replyPort; self.ackPort = ackPort; self.expected = expected; self.finish = finish
 }
}

let myStation: UInt8 = 254
let blockSize = 1280
let discName = "Harness"

final class FileServer {
 let gateway = EconetGateway()
 let root = Node("$", dir: true)
 var users: [User] = [User("SYST", "", privileged: true), User("GUEST", "SECRET", privileged: false)]
 var sessions: [UInt8: Session] = [:]
 var requests: [[String: Any]] = []
 var transport: [String: Int] = [:]
 var now: UInt64 = 0
 private var queue: [Outbound] = []
 private var current: (id: UInt32, since: UInt64)?
 private var nextID: UInt32 = 0x8000_0000
 private var notBefore: UInt64 = 0
 private var incoming: [UInt32: (src: UInt8, port: UInt8, ctrl: UInt8)] = [:]
 private var receivers: [UInt8: Receiver] = [:]
 private var nextDataPort: UInt8 = 0x90

 init() {
  gateway.remoteStations = [myStation]
  gateway.send = { [unowned self] in self.fromLine($0) }
 }
 var busy: Bool { current != nil || !queue.isEmpty || !receivers.isEmpty }

 // MARK: Transport

 private func count(_ k: String) { transport[k, default: 0] += 1 }
 private func fromLine(_ m: EconetGatewayMessage) {
  switch m {
  case .frame(let id, let stage, _, let b) where stage == 0 && b.count >= 6:
   let src = b[2], ctrl = b[4], port = b[5]
   if port == 0 {
    // Immediate operations: only machine type (what NetFS's logon peeks) is answered.
    if ctrl | 0x80 == 0x88 { count("machine-type"); gateway.receive(.frame(transaction: id, stage: 1, final: true, bytes: [src, 0, myStation, 0, 0x07, 0x00, 0x00, 0x01])) }
    else { count("immediate-refused"); gateway.receive(.noReply(transaction: id, from: myStation, to: src)) }
    return
   }
   guard port == 0x99 || receivers[port]?.station == src else { count("not-listening"); gateway.receive(.noReply(transaction: id, from: myStation, to: src)); return }
   incoming[id] = (src, port, ctrl)
   gateway.receive(.frame(transaction: id, stage: 1, final: false, bytes: [src, 0, myStation, 0]))
  case .frame(let id, 2, _, let b):
   guard let t = incoming.removeValue(forKey: id), b.count >= 4 else { return }
   gateway.receive(.frame(transaction: id, stage: 3, final: true, bytes: [t.src, 0, myStation, 0]))
   let payload = Array(b[4...])
   if t.port == 0x99 { count("command"); request(t.src, payload) } else { count("data-in"); dataBlock(t.port, payload) }
  case .frame(let id, 1, _, _):
   guard current?.id == id, let m = queue.first else { return }
   gateway.receive(.frame(transaction: id, stage: 2, final: false, bytes: [m.station, 0, myStation, 0] + m.payload))
  case .frame(let id, 3, _, _):
   guard current?.id == id else { return }
   count("sent-" + queue[0].what); queue.removeFirst(); current = nil
  case .noReply(let id, _, _):
   incoming[id] = nil
   guard current?.id == id else { return }
   current = nil; queue[0].tries += 1; notBefore = now + 480_000
   if queue[0].tries > 400 { count("dropped-" + queue[0].what); queue.removeFirst() }
  case .broadcast(let b):
   guard b.count >= 8, b[5] == 0x99 else { return }
   count("broadcast")
   request(b[2], Array(b[6...]), broadcast: true)
  default: break
  }
 }
 /// Between slices of the network's time: start the next queued transaction.
 func pump(_ t: UInt64) {
  now = t
  if let c = current, t > c.since + 5 * 24_000_000 { current = nil; notBefore = t }
  guard current == nil, let m = queue.first, t >= notBefore else { return }
  let id = nextID; nextID &+= 1; current = (id, t)
  gateway.receive(.frame(transaction: id, stage: 0, final: false, bytes: [m.station, 0, myStation, 0, 0x80, m.port]))
 }
 private func send(_ station: UInt8, _ port: UInt8, _ payload: [UInt8], _ what: String) { queue.append(Outbound(station: station, port: port, payload: payload, what: what)) }
 private func reply(_ station: UInt8, _ port: UInt8, cc: UInt8 = 0, _ data: [UInt8] = []) { send(station, port, [cc, 0] + data, "reply") }
 private func allocPort() -> UInt8 { repeat { nextDataPort = nextDataPort == 0x98 ? 0x90 : nextDataPort + 1 } while receivers[nextDataPort] != nil; return nextDataPort }
 private func dataBlock(_ port: UInt8, _ data: [UInt8]) {
  guard let r = receivers[port] else { return }
  r.data += data
  if r.data.count < r.expected { send(r.station, r.ackPort, [0], "ack"); return }
  receivers[port] = nil
  do { reply(r.station, r.replyPort, try r.finish(Array(r.data.prefix(r.expected)))) }
  catch let e as FSError { send(r.station, r.replyPort, [0, e.code] + Array(e.text.utf8) + [13], "error") } catch {}
 }
 private func sendData(_ station: UInt8, _ port: UInt8, _ data: [UInt8]) {
  var i = 0
  while i < data.count { let n = min(blockSize, data.count - i); send(station, port, Array(data[i..<i + n]), "data"); i += n }
 }

 // MARK: Requests

 private func request(_ src: UInt8, _ p: [UInt8], broadcast: Bool = false) {
  guard p.count >= 2 else { return }
  let rp = p[0], fn = p[1]
  var entry: [String: Any] = ["station": Int(src), "function": Int(fn)]
  if broadcast { entry["broadcast"] = true }
  do {
   try handle(src, fn, p, &entry)
   entry["result"] = "ok"
  } catch let e as FSError {
   entry["result"] = String(format: "&%02X %@", e.code, e.text)
   send(src, rp, [0, e.code] + Array(e.text.utf8) + [13], "error")
  } catch {}
  requests.append(entry)
 }
 private func string(_ b: [UInt8], _ from: Int) -> (String, Int) {
  var i = from, s: [UInt8] = []
  while i < b.count && b[i] != 13 { s.append(b[i]); i += 1 }
  return (String(decoding: s, as: UTF8.self).trimmingCharacters(in: .whitespaces), i + 1)
 }
 private func le(_ v: UInt32, _ n: Int) -> [UInt8] { (0..<n).map { UInt8(truncatingIfNeeded: v >> (8 * UInt32($0))) } }
 private func num(_ b: [UInt8], _ at: Int, _ n: Int) -> Int { (0..<n).reduce(0) { $0 | Int(at + $1 < b.count ? b[at + $1] : 0) << (8 * $1) } }
 private func padded(_ s: String, _ n: Int) -> [UInt8] { Array((s + String(repeating: " ", count: n)).utf8.prefix(n)) }

 /// Wildcard match (`*` any run, `#` any one character), ignoring case.
 private func matches(_ pattern: String, _ name: String) -> Bool {
  let p = Array(pattern.uppercased()), n = Array(name.uppercased())
  func m(_ i: Int, _ j: Int) -> Bool {
   if i == p.count { return j == n.count }
   if p[i] == "*" { return (j...n.count).contains { m(i + 1, $0) } }
   return j < n.count && (p[i] == "#" || p[i] == n[j]) && m(i + 1, j + 1)
  }
  return m(0, 0)
 }
 private func validLeaf(_ s: String) throws {
  guard !s.isEmpty, s.count <= 10, !s.contains(where: { " .:*#$&@^%\"".contains($0) || $0.asciiValue.map { $0 < 33 || $0 > 126 } ?? true }) else { throw badName }
 }
 /// The components of a name, after any ":disc." prefix.
 private func components(_ name: String) throws -> [String] {
  var s = name
  if s.hasPrefix(":") {
   let rest = s.dropFirst(); let disc = rest.prefix { $0 != "." }
   guard disc.uppercased() == discName.uppercased() else { throw FSError(code: 0xCD, text: "Bad drive") }
   s = String(rest.dropFirst(disc.count)); if s.hasPrefix(".") { s.removeFirst() }
   if s.isEmpty { s = "$" }
  }
  return s.isEmpty ? [] : s.split(separator: ".", omittingEmptySubsequences: false).map(String.init)
 }
 struct Ctx { let s: Session; let urd: Node; let csd: Node; let lib: Node }
 private func step(_ c: String, from d: Node, _ x: Ctx) throws -> Node {
  switch c {
  case "^": return d.parent ?? d
  case "@": return x.csd
  case "$": return root
  case "&": return x.urd
  case "%": return x.lib
  default:
   guard d.isDir else { throw isAFile }
   guard let n = d.children.first(where: { matches(c, $0.name) }) else { throw notFound }
   return n
  }
 }
 /// Resolves a name relative to the CSD slot's directory; nil if the last component isn't there.
 private func resolve(_ name: String, _ x: Ctx) throws -> Node? {
  let cs = try components(name)
  var d = x.csd
  for (i, c) in cs.enumerated() {
   if i == 0 && c == "$" { d = root; continue }
   do { d = try step(c, from: d, x) } catch let e as FSError where e.code == 0xD6 && i == cs.count - 1 { return nil }
  }
  return d
 }
 private func existing(_ name: String, _ x: Ctx) throws -> Node { guard let n = try resolve(name, x) else { throw notFound }; return n }
 /// The directory a new object goes in, and its leaf name.
 private func parentAndLeaf(_ name: String, _ x: Ctx) throws -> (Node, String) {
  let cs = try components(name)
  guard let leaf = cs.last else { throw badName }
  try validLeaf(leaf)
  var d = x.csd
  for (i, c) in cs.dropLast().enumerated() { d = (i == 0 && c == "$") ? root : try step(c, from: d, x) }
  guard d.isDir else { throw isAFile }
  return (d, leaf)
 }
 private func info5(_ n: Node) -> [UInt8] {
  [n.isDir ? 2 : 1] + le(n.load, 4) + le(n.exec, 4) + le(UInt32(n.isDir ? 0 : n.data.count), 3) + [n.access] + le(UInt32(n.date), 2) + [0]
 }
 private var freeSectors: Int { 3200 - root.sectors }
 private func logon(_ src: UInt8, _ u: User) throws -> Session {
  if let old = sessions[src] { old.handles = [:] }
  let s = Session(src, u); sessions[src] = s
  s.urd = try s.alloc(.dir(root))
  _ = try s.alloc(.dir(root)); _ = try s.alloc(.dir(root))
  return s
 }

 private func handle(_ src: UInt8, _ fn: UInt8, _ p: [UInt8], _ entry: inout [String: Any]) throws {
  let rp = p[0]
  let open: Set<UInt8> = [0, 14, 16, 25]
  let session = sessions[src]
  guard session != nil || open.contains(fn) else { throw whoAreYou }
  // GetByte and PutByte have a short header; the rest the standard one.
  if fn == 8 || fn == 9 {
   guard let s = session, p.count >= 3 else { throw badCommand }
   let f = try s.file(p[2])
   if fn == 8 {
    let d = f.node.data
    if f.ptr < d.count { let b = d[f.ptr]; f.ptr += 1; reply(src, rp, [b, f.ptr == d.count ? 0x80 : 0]) }
    else { f.ptr = d.count + 1; reply(src, rp, [0xFE, 0xC0]) }
   } else {
    guard f.update, p.count >= 4 else { throw FSError(code: 0xC1, text: "Not open for update") }
    if f.ptr >= f.node.data.count { f.node.data += [UInt8](repeating: 0, count: f.ptr - f.node.data.count + 1) }
    f.node.data[f.ptr] = p[3]; f.ptr += 1; reply(src, rp)
   }
   return
  }
  guard p.count >= 5 else { throw badCommand }
  let a = Array(p[5...])
  // The directories the header's handles name (the URD slot is a port for 1, 2, 10 and 11).
  var x: Ctx? = nil, ctxError = whoAreYou
  if let s = session {
   do {
    let urdNode = try s.dir(s.urd), csd = try s.dir(p[3]), lib = (try? s.dir(p[4])) ?? root
    let u = [1, 2, 10, 11].contains(fn) ? urdNode : ((try? s.dir(p[2])) ?? urdNode)
    x = Ctx(s: s, urd: u, csd: csd, lib: lib)
   } catch let e as FSError { ctxError = e }
  }
  func ctx() throws -> Ctx { guard let x else { throw ctxError }; return x }
  switch fn {
  case 0: try command(src, p, string(a, 0).0, x, ctxError, &entry)
  case 1:   // Save: load, exec, size, name
   let x = try ctx(); let (name, _) = string(a, 11); entry["name"] = name
   let (d, leaf) = try parentAndLeaf(name, x)
   if let old = d.child(leaf) { if old.isDir { throw isADir }; if old.access & 0x10 != 0 { throw locked } }
   let load = UInt32(num(a, 0, 4)), exec = UInt32(num(a, 4, 4)), size = num(a, 8, 3)
   let port = allocPort()
   let commit: ([UInt8]) throws -> [UInt8] = { data in
    let n = d.child(leaf) ?? { let n = Node(leaf, dir: false); d.add(n); return n }()
    n.load = load; n.exec = exec; n.data = data; n.date = fsDate
    return [n.access] + self.le(UInt32(fsDate), 2)
   }
   reply(src, rp, cc: 3, [port] + le(UInt32(blockSize), 2) + Array(leaf.utf8) + [13])
   if size == 0 { reply(src, rp, try commit([])) }
   else { receivers[port] = Receiver(station: src, replyPort: rp, ackPort: p[2], expected: size, finish: commit) }
  case 2, 5:   // Load, LoadAsCommand
   let x = try ctx(); let (name, _) = string(a, 0); entry["name"] = name
   var n = try resolve(name, x)
   if fn == 5 && n == nil { n = try? resolve(name, Ctx(s: x.s, urd: x.urd, csd: x.lib, lib: x.lib)) ?? nil }
   guard let n else { throw fn == 5 ? badCommand : notFound }
   guard !n.isDir else { throw isADir }
   reply(src, rp, cc: 14, le(n.load, 4) + le(n.exec, 4) + le(UInt32(n.data.count), 3) + [n.access] + le(UInt32(n.date), 2) + padded(n.name, 10) + [13])
   sendData(src, p[2], n.data)
   reply(src, rp)
  case 3:   // Examine: argument, entry point, count, directory
   let x = try ctx(); let (name, _) = string(a, 3); entry["name"] = name; entry["argument"] = Int(a[0])
   let d = name.isEmpty ? x.csd : try existing(name, x)
   guard d.isDir else { throw isAFile }
   let start = Int(a[1])
   guard [0, 2, 3].contains(a[0]) else { throw FSError(code: 0x8E, text: "Bad INFO argument") }
   // The reply must fit a 256-byte buffer, as the client's *Cat asks for more than that.
   let cap = a[0] == 3 ? 13 : 255
   var want = Int(a[2]) == 0 ? 255 : Int(a[2]); want = min(want, cap)
   let items = Array(d.children.dropFirst(start).prefix(want))
   entry["entries"] = items.map(\.name)
   var out: [UInt8] = [UInt8(items.count), UInt8(d.children.count)]
   for n in items {
    switch a[0] {
    case 0: out += padded(n.name, 10) + le(n.load, 4) + le(n.exec, 4) + [n.access] + le(UInt32(n.date), 2) + le(n.sin, 3) + le(UInt32(n.isDir ? 0 : n.data.count), 3)
    case 2: out += [10] + padded(n.name, 10)
    default: out += padded(n.name, 10) + [0x20] + padded(n.accessString, 7) + [0]
    }
   }
   reply(src, rp, out + [0x80])
  case 4:   // Catalogue header
   let x = try ctx(); let (name, _) = string(a, 0)
   let d = name.isEmpty ? x.csd : try existing(name, x)
   reply(src, rp, padded(d.name, 11) + Array("O   ".utf8) + padded(discName, 16) + [13, 0x80])
  case 6:   // Open: create flag (0 creates), access (0 update), name
   let x = try ctx(); let (name, _) = string(a, 2); entry["name"] = name
   let mustExist = a[0] != 0, readOnly = a[1] != 0
   var n = try resolve(name, x)
   if n == nil {
    guard !mustExist else { throw notFound }
    let (d, leaf) = try parentAndLeaf(name, x); let f = Node(leaf, dir: false); f.load = 0; f.exec = 0; d.add(f); n = f
   } else if !mustExist {
    guard !n!.isDir else { throw isADir }
    if n!.access & 0x10 != 0 { throw locked }
    n!.data = []
   }
   let h: UInt8 = n!.isDir ? try x.s.alloc(.dir(n!)) : try x.s.alloc(.file(OpenFile(n!, update: !readOnly)))
   reply(src, rp, [h])
  case 7:   // Close (0: all open files)
   let s = try ctx().s
   if a[0] == 0 { for (k, v) in s.handles { if case .file = v { s.handles[k] = nil } } }
   else { guard s.handles[a[0]] != nil, a[0] != s.urd else { throw channel }; s.handles[a[0]] = nil }
   reply(src, rp)
  case 10, 11:   // GetBytes, PutBytes: handle, mode, count, offset
   let s = try ctx().s; let f = try s.file(a[0])
   let n = num(a, 2, 3); if a[1] == 0 { f.ptr = num(a, 5, 3) }
   entry["count"] = n
   if fn == 10 {
    let d = f.node.data, from = min(f.ptr, d.count), got = min(n, d.count - from)
    reply(src, rp)
    sendData(src, p[2], Array(d[from..<from + got]) + [UInt8](repeating: 0, count: n - got))
    f.ptr += got
    reply(src, rp, [f.ptr >= d.count ? 0x80 : 0] + le(UInt32(got), 3))
   } else {
    guard f.update else { throw FSError(code: 0xC1, text: "Not open for update") }
    let port = allocPort(), at = f.ptr
    let commit: ([UInt8]) throws -> [UInt8] = { data in
     if at + data.count > f.node.data.count { f.node.data += [UInt8](repeating: 0, count: at + data.count - f.node.data.count) }
     f.node.data.replaceSubrange(at..<at + data.count, with: data); f.ptr = at + data.count
     return [0] + self.le(UInt32(data.count), 3)
    }
    reply(src, rp, [port] + le(UInt32(blockSize), 2))
    if n == 0 { reply(src, rp, try commit([])) }
    else { receivers[port] = Receiver(station: src, replyPort: rp, ackPort: p[2], expected: n, finish: commit) }
   }
  case 12:   // Read random access info: 0 PTR, 1 EXT, 2 allocated size
   let f = try ctx().s.file(a[0]); let ext = f.node.data.count
   guard a[1] <= 2 else { throw FSError(code: 0x8E, text: "Bad INFO argument") }
   reply(src, rp, le(UInt32([f.ptr, ext, (ext + 255) / 256 * 256][Int(a[1])]), 3))
  case 13:   // Set random access info: 0 PTR, 1 EXT
   let f = try ctx().s.file(a[0]); let v = num(a, 2, 3)
   if a[1] == 0 { f.ptr = v }
   else if a[1] == 1 {
    guard f.update else { throw FSError(code: 0xC1, text: "Not open for update") }
    if v < f.node.data.count { f.node.data.removeLast(f.node.data.count - v) } else { f.node.data += [UInt8](repeating: 0, count: v - f.node.data.count) }
    f.ptr = min(f.ptr, v)
   } else { throw FSError(code: 0x8E, text: "Bad INFO argument") }
   reply(src, rp)
  case 14:   // Disc names: first drive, count
   reply(src, rp, a[0] == 0 ? [1, 0] + padded(discName, 16) : [0])
  case 15:   // Logged-on users: first entry, count
   let all = sessions.values.sorted { $0.station < $1.station }.dropFirst(Int(a[0])).prefix(a[1] == 0 ? 255 : Int(a[1]))
   reply(src, rp, [UInt8(all.count)] + all.flatMap { [$0.station, 0] + Array($0.user.name.utf8) + [13, $0.user.privileged ? 1 : 0] })
  case 16: reply(src, rp, le(UInt32(fsDate), 2) + [12, 0, 0])
  case 17: let f = try ctx().s.file(a[0]); reply(src, rp, [f.ptr >= f.node.data.count ? 0xFF : 0])
  case 18:   // Read object info: argument, name
   let x = try ctx(); let (name, _) = string(a, 1); entry["name"] = name; entry["argument"] = Int(a[0])
   if a[0] == 6 {
    let d = name.isEmpty ? x.csd : try existing(name, x)
    guard d.isDir else { throw isAFile }
    reply(src, rp, [0, 0, 10] + padded(d.name, 10) + [0, UInt8(min(d.children.count, 255))]); return
   }
   guard let n = try resolve(name, x) else { reply(src, rp, [0]); return }
   let i = info5(n)
   switch a[0] {
   case 1: reply(src, rp, [i[0]] + le(UInt32(n.date), 2))
   case 2: reply(src, rp, Array(i[0..<9]))
   case 3: reply(src, rp, [i[0]] + Array(i[9..<12]))
   case 4: reply(src, rp, [i[0], n.access])
   case 5: reply(src, rp, i)
   case 7: reply(src, rp, [i[0]] + le(n.sin, 3) + [0, 0, 0])
   default: throw FSError(code: 0x8E, text: "Bad INFO argument")
   }
  case 19:   // Set object attributes: argument, values, name
   let x = try ctx(); let sizes = [1: 9, 2: 4, 3: 4, 4: 1, 5: 2]
   guard let size = sizes[Int(a[0])] else { throw FSError(code: 0x8E, text: "Bad INFO argument") }
   let (name, _) = string(a, 1 + size); entry["name"] = name; entry["argument"] = Int(a[0])
   let n = try existing(name, x)
   func setAccess(_ v: UInt8) { n.access = (v & 0x1F) | (n.isDir ? 0x20 : 0) }
   switch a[0] {
   case 1: n.load = UInt32(num(a, 1, 4)); n.exec = UInt32(num(a, 5, 4)); setAccess(a[9])
   case 2: n.load = UInt32(num(a, 1, 4))
   case 3: n.exec = UInt32(num(a, 1, 4))
   case 4: setAccess(a[1])
   default: n.date = UInt16(num(a, 1, 2))
   }
   reply(src, rp)
  case 20:   // Delete
   let x = try ctx(); let (name, _) = string(a, 0); entry["name"] = name
   let n = try existing(name, x)
   guard n !== root, let d = n.parent else { throw FSError(code: 0xBD, text: "Insufficient access") }
   if n.access & 0x10 != 0 { throw locked }
   if n.isDir && !n.children.isEmpty { throw FSError(code: 0xB4, text: "Dir not empty") }
   if x.s.handles.values.contains(where: { if case .file(let f) = $0 { return f.node === n }; return false }) { throw FSError(code: 0xC2, text: "Already open") }
   d.remove(n)
   reply(src, rp, le(n.load, 4) + le(n.exec, 4) + le(UInt32(n.data.count), 3) + [n.access])
  case 21: let x = try ctx(); reply(src, rp, [16] + padded(discName, 16) + padded(x.csd.name, 10) + padded(x.lib.name, 10))
  case 22: let s = try ctx().s; s.user.boot = a[0] & 0x0F; reply(src, rp)
  case 23: sessions[src] = nil; reply(src, rp)
  case 24:
   let (name, _) = string(a, 0)
   guard let s = sessions.values.first(where: { $0.user.name == name.uppercased() }) else { throw FSError(code: 0xBC, text: "User not known") }
   reply(src, rp, [s.user.privileged ? 1 : 0, s.station, 0])
  case 25: reply(src, rp, padded("ArcLibre", 9) + Array(" 1.00".utf8) + [13])
  case 26:
   let (name, _) = string(a, 0)
   guard name.isEmpty || name.uppercased() == discName.uppercased() else { throw FSError(code: 0xCD, text: "Bad drive") }
   reply(src, rp, le(UInt32(freeSectors), 3) + le(3200, 3))
  case 27:   // Create directory: size, name
   let x = try ctx(); let (name, _) = string(a, 1); entry["name"] = name
   let (d, leaf) = try parentAndLeaf(name, x)
   guard d.child(leaf) == nil else { throw FSError(code: 0xC4, text: "Already exists") }
   d.add(Node(leaf, dir: true)); reply(src, rp)
  case 29:   // Create file: load, exec, size, name
   let x = try ctx(); let (name, _) = string(a, 11); entry["name"] = name
   let (d, leaf) = try parentAndLeaf(name, x)
   if let old = d.child(leaf) { if old.isDir { throw isADir }; if old.access & 0x10 != 0 { throw locked } }
   let n = d.child(leaf) ?? { let n = Node(leaf, dir: false); d.add(n); return n }()
   n.load = UInt32(num(a, 0, 4)); n.exec = UInt32(num(a, 4, 4)); n.data = [UInt8](repeating: 0, count: num(a, 8, 3))
   reply(src, rp, [n.access] + le(UInt32(fsDate), 2))
  case 30:
   let (name, _) = string(a, 0)
   guard name.isEmpty || users.contains(where: { $0.name == name.uppercased() }) else { throw FSError(code: 0xBC, text: "User not known") }
   reply(src, rp, le(UInt32(freeSectors * 256), 4))
  case 32: reply(src, rp, Array(try ctx().s.user.name.utf8) + [13])
  default: throw badCommand
  }
 }

 /// Function 0: a command line.
 private func command(_ src: UInt8, _ p: [UInt8], _ line: String, _ x: Ctx?, _ ctxError: FSError, _ entry: inout [String: Any]) throws {
  let rp = p[0]
  let words = line.split(separator: " ").map(String.init)
  let verb = words.first?.uppercased() ?? ""
  entry["command"] = line.uppercased().hasPrefix("I AM") || verb == "PASS" ? words.prefix(3).joined(separator: " ") : line
  func ctx() throws -> Ctx { guard let x else { throw ctxError }; return x }
  if verb == "I" || verb == "I." || verb == "IAM" {
   let rest = verb == "IAM" ? Array(words.dropFirst()) : Array(words.dropFirst(words.count > 1 && words[1].uppercased() == "AM" ? 2 : 1))
   guard let name = rest.first else { throw FSError(code: 0xAC, text: "Bad user name") }
   guard let u = users.first(where: { $0.name == name.uppercased() }) else { throw FSError(code: 0xBC, text: "User not known") }
   let pw = rest.count > 1 ? rest[1].trimmingCharacters(in: CharacterSet(charactersIn: "\"")) : ""
   guard pw.uppercased() == u.password.uppercased() else { throw FSError(code: 0xBB, text: "Wrong password") }
   let s = try logon(src, u)
   reply(src, rp, cc: 5, [s.urd, s.urd + 1, s.urd + 2, u.boot])
   return
  }
  switch verb {
  case "DIR", "LIB":
   let x = try ctx()
   let arg = words.dropFirst().joined(separator: " ")
   let d = arg.isEmpty ? x.urd : try existing(arg, x)
   guard d.isDir else { throw FSError(code: 0xBE, text: "Not a directory") }
   // The handle in the slot being replaced is released (except the URD).
   let slot = verb == "DIR" ? p[3] : p[4]
   if slot != x.s.urd && slot != p[2] && (verb == "DIR" ? slot != p[4] : slot != p[3]) { x.s.handles[slot] = nil }
   let h = try x.s.alloc(.dir(d))
   reply(src, rp, cc: verb == "DIR" ? 7 : 9, [h])
  case "SDISC":
   let x = try ctx()
   guard words.count > 1, words[1].uppercased() == discName.uppercased() else { throw FSError(code: 0xCD, text: "Bad drive") }
   let s = try logon(src, x.s.user)
   reply(src, rp, cc: 6, [s.urd, s.urd + 1, s.urd + 2])
  case "RENAME":
   let x = try ctx()
   guard words.count == 3 else { throw FSError(code: 0xB0, text: "Bad rename") }
   let n = try existing(words[1], x)
   let (d, leaf) = try parentAndLeaf(words[2], x)
   guard n !== root, d.child(leaf) == nil || d.child(leaf) === n else { throw FSError(code: 0xC4, text: "Already exists") }
   var up: Node? = d; while let u = up { if u === n { throw FSError(code: 0xB0, text: "Bad rename") }; up = u.parent }
   n.parent?.remove(n); n.name = leaf; d.add(n)
   reply(src, rp)
  case "ACCESS":
   let x = try ctx()
   guard words.count >= 2 else { throw FSError(code: 0xCF, text: "Invalid access string") }
   let n = try existing(words[1], x)
   let spec = words.count > 2 ? words[2].uppercased() : ""
   let parts = spec.split(separator: "/", maxSplits: 1, omittingEmptySubsequences: false).map(String.init)
   guard spec.allSatisfy({ "LWR/".contains($0) }), !(parts.count > 1 && parts[1].contains("L")) else { throw FSError(code: 0xCF, text: "Invalid access string") }
   var v: UInt8 = 0
   if parts[0].contains("L") { v |= 0x10 }; if parts[0].contains("W") { v |= 0x08 }; if parts[0].contains("R") { v |= 0x04 }
   if parts.count > 1 { if parts[1].contains("W") { v |= 0x02 }; if parts[1].contains("R") { v |= 0x01 } }
   n.access = v | (n.isDir ? 0x20 : 0)
   reply(src, rp)
  case "INFO", "I.":
   let x = try ctx()
   guard words.count > 1 else { throw badName }
   let n = try existing(words[1], x)
   var t = padded(n.name, 10) + [0x20]
   t += Array(String(format: "%08X %08X   %06X   ", n.load, n.exec, n.isDir ? 0 : n.data.count).utf8)
   t += padded(n.accessString, 6) + Array("     15:10:26 ".utf8) + Array(String(format: "%06X", n.sin).utf8) + [13, 0x80]
   reply(src, rp, cc: 4, t)
  case "PASS":
   let x = try ctx()
   let old = words.count > 1 ? words[1].trimmingCharacters(in: CharacterSet(charactersIn: "\"")) : ""
   guard old.uppercased() == x.s.user.password.uppercased() else { throw FSError(code: 0xBB, text: "Wrong password") }
   x.s.user.password = words.count > 2 ? words[2].trimmingCharacters(in: CharacterSet(charactersIn: "\"")) : ""
   reply(src, rp)
  default:
   // Not a server command: say so (command code 8), echoing it, as the protocol has it.
   _ = try ctx()
   reply(src, rp, cc: 8, Array(line.utf8) + [13])
  }
 }
}

// MARK: - The machine

let a = CommandLine.arguments
precondition(a.count >= 6, "NetFSProbe ROM ROM_DIRECTORY OUTPUT on|off cli|desktop STEP...")
let root = URL(fileURLWithPath: a[2]), out = URL(fileURLWithPath: a[3]), serverOn = a[4] == "on", desktop = a[5] == "desktop", steps = Array(a[6...])
try FileManager.default.createDirectory(at: out, withIntermediateDirectories: true)
let rom = try ROMImage.load(paths: [a[1]])
let layout = try JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("rom-layout.json"))) as! [String: Any]
precondition(rom.sha256 == layout["rom_sha256"] as! String)
var c = MachineConfiguration(model: .a440)
c.cpu = .arm2; c.ramKB = 4096; c.romPaths = [a[1]]; c.hardDiscs = []; c.monitor = "standard"; c.powerOnKeys = [0x34]; c.econetStation = 1
c.cmosSettings = [.init(byte: 135, value: 1), .drive(0), .init(byte: 16, mask: 0x10, value: 0), .init(byte: 185, value: 10), .init(byte: 196, value: 12)]
let m = try Machine(configuration: c, rom: rom)
let net = EconetNetwork(); net.add(m)

// The store: a few files and a directory, the same every run.
let server = FileServer()
var seed: UInt32 = 1996
func rnd() -> UInt8 { seed = seed &* 1_103_515_245 &+ 12345; return UInt8(truncatingIfNeeded: seed >> 16) }
server.root.add(.file("ReadMe", type: 0xFFF, Array("This file is on a host-side Econet file server.\n".utf8)))
server.root.add(.file("Data", type: 0xFFD, (0..<5000).map { _ in rnd() }))
server.root.add(.file("Big", type: 0xFFF, Array((1...1600).map { String(format: "Line %05d of a file loaded across the network.\n", $0) }.joined().utf8)))
let docs = Node("Docs", dir: true); server.root.add(docs)
docs.add(.file("Note", type: 0xFFF, Array("A note in a subdirectory.\n".utf8)))
let initialStore = server.root.dump()
if serverOn { net.line.attach(device: server.gateway) }

// Hourglass_Percentage from NetStatus's own code: its EconetV handler turning NetFS's upcalls into the hourglass.
var percentages: [Int] = []
// From NetFiler's code: its *commands, and the text of the icons it makes; and every desktop error box.
func range(_ name: String) -> Range<UInt32> {
 let e = (layout["modules"] as! [[String: Any]]).first { $0["component"] as? String == name }!
 let b = (e["base"] as! NSNumber).uint32Value; return b..<(b + (e["length"] as! NSNumber).uint32Value)
}
let netFiler = range("NetFiler"), netStatus = range("NetStatus")
var netFilerCommands: [String] = [], netFilerIcons: [String] = [], reportedErrors: [String] = []
func text(_ p: UInt32) -> String { var b: [UInt8] = []; for i in 0..<256 { guard let v = m.memc.debugRead(p + UInt32(i), space: .logical), v >= 32 else { break }; b.append(v) }; return String(bytes: b, encoding: .isoLatin1) ?? "?" }
m.cpu.swiObserver = { pc, n in
 let swi = n & ~UInt32(0x20000), r = m.cpu.r
 if swi == 0x406C4 && netStatus.contains(pc) { percentages.append(Int(Int32(bitPattern: r[0]))) }
 if swi == 0x400DF { reportedErrors.append(text(r[0] + 4)) }
 if netFiler.contains(pc) {
  if swi == 0x05 { netFilerCommands.append(text(r[0])) }
  if swi == 0x400C2, let flags = m.memc.debugReadWord(r[1] + 20, space: .logical), flags & 1 != 0 {
   netFilerIcons.append(flags & 0x100 != 0 ? text(m.memc.debugReadWord(r[1] + 24, space: .logical) ?? 0) : text(r[1] + 24))
  }
 }
}
func run(_ ticks: UInt64) {
 var left = ticks
 while left > 0 { let q = min(left, 24_000); net.run(ticks: q); server.pump(net.ticks); left -= q }
}
let second: UInt64 = 24_000_000
func word(_ p: UInt32) -> UInt32 { m.memc.debugReadWord(p, space: .logical) ?? 0xffffffff }
func press(_ k: UInt8) { m.keyDown(k); run(1_920_000); m.keyUp(k); run(2_400_000) }
func type(_ s: String) { for ch in s { let (k, shift) = ArcKey.forCharacter(ch)!; if shift { m.keyDown(0x4c); run(720_000) }; press(k); if shift { m.keyUp(0x4c); run(720_000) } } }
func move(_ x: Int, _ y: Int) { m.mouseMove(dx: (x - Int(word(1452))) / 2, dy: (y - Int(word(1456))) / 2); run(4_800_000) }
func click(_ button: UInt8) { m.keyDown(button); run(1_920_000); m.keyUp(button); run(1_920_000) }
func numbers(_ s: Substring) -> [Int] { s.split(separator: ",").map { Int($0)! } }
func json(_ x: Any, _ name: String) { try! JSONSerialization.data(withJSONObject: x, options: [.prettyPrinted, .sortedKeys]).write(to: out.appendingPathComponent(name + ".json")) }
func shot(_ name: String) { precondition(writePNG(m.currentFrame, to: out.appendingPathComponent(name + ".png"))) }
run(second * 35)
if !desktop { press(0x0c); run(second * 2) }
var screens: [[String]] = [], shots: [String: Int] = [:]
for s in steps {
 if s.hasPrefix("WAIT:") { run(second * UInt64(s.dropFirst(5))!) }
 else if s == "F12" { press(0x0c); run(second * 2) }
 else if s.hasPrefix("KEY:") { press(UInt8(s.dropFirst(4))!); run(second) }
 else if s.hasPrefix("CLICK:") { let v = numbers(s.dropFirst(6)); move(v[0], v[1]); for _ in 0..<(v.count > 2 ? v[2] : 1) { click(0x70) }; run(second * 2) }
 else if s.hasPrefix("MENU:") { let v = numbers(s.dropFirst(5)); move(v[0], v[1]); click(0x71); run(second * 2) }
 else if s.hasPrefix("MOVE:") { let v = numbers(s.dropFirst(5)); move(v[0], v[1]); run(second) }
 else if s.hasPrefix("SHOT:") { shot(String(s.dropFirst(5))); shots[String(s.dropFirst(5))] = screens.count }
 else if s.hasPrefix("WATCH:") {
  // Through the next transfer: the first frame NetStatus's hourglass shows a part-done percentage.
  let before = percentages.count; var waited: UInt64 = 0
  while waited < second * 30 && !percentages.dropFirst(before).contains(where: { $0 > 0 && $0 < 100 }) { run(second / 50); waited += second / 50 }
  run(second / 2); shot(String(s.dropFirst(6))); shots[String(s.dropFirst(6))] = screens.count
 }
 else if s.hasPrefix("TYPE:") { type(String(s.dropFirst(5))); run(second) }
 else {
  // Typed with Return; at the command line, until the prompt is back and the server is idle.
  type(s + "\n"); run(second * 2); var w = 0
  func prompt() -> Bool { ["*", "*_", ">", ">_"].contains(m.screenText.last { !$0.trimmingCharacters(in: .whitespaces).isEmpty }?.trimmingCharacters(in: .whitespaces) ?? "") }
  while w < 30 && (server.busy || (!desktop && !prompt())) { run(second); w += 1 }
  run(second)
 }
 screens.append(m.screenText)
}
json(["status": "PASS", "rom_sha256": rom.sha256, "server": serverOn ? "on" : "off", "mode": desktop ? "desktop" : "cli", "steps": steps, "screens": screens, "shots": shots,
      "requests": server.requests, "transport": server.transport, "netstatus_percentages": percentages, "netfiler_commands": netFilerCommands, "netfiler_icons": netFilerIcons, "reported_errors": reportedErrors,
      "store_before": initialStore, "store_after": server.root.dump(),
      "gateway": ["frames_in": server.gateway.counters.framesIn, "frames_out": server.gateway.counters.framesOut, "broadcasts_out": server.gateway.counters.broadcastsOut,
                  "no_replies": server.gateway.counters.noReplies, "refused_busy": server.gateway.counters.refusedBusy, "timeouts": server.gateway.counters.timeouts]], "result")
print("PASS")
