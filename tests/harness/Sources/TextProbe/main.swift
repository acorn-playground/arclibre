// SPDX-License-Identifier: Apache-2.0
// Focused framebuffer/font observation using the unchanged MacArch host core.
import ArchimedesCore
import Foundation
import ProbeSupport
func check(_ b: Bool, _ s: String) { if !b { fatalError(s) } }
let a = CommandLine.arguments
check(a.count == 5, "TextProbe ROM SNAPSHOT OUTPUT banner|fixture")
let rom = try ROMImage.load(paths: [a[1]])
let m = try Machine.restore(snapshot: Array(Data(contentsOf: URL(fileURLWithPath: a[2]))), rom: rom)
let out = a[3]
try FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
let d = m.debugger
d.setTracing(4096)
_ = try d.addBreakpoint(.init(id: 0, kind: .execute, start: 4))
_ = try d.addBreakpoint(.init(id: 0, kind: .execute, start: 12, end: 20))
var missing: [String] = []
_ = try d.addBreakpoint(.init(id: 0, kind: .execute, start: 0x38005c4, logMessage: "MISSING SWI={R11}"))
_ = try d.addBreakpoint(.init(id: 0, kind: .execute, start: 0x38072d4, logMessage: "CAM-MISS old={R0} new={R3} flags={R1} index={R2} cam={R4} lr={R14}"))
let end: UInt32
if a[4] == "fixture" {
    // Test-owned application RAM. This invokes the actual OS_Write0 handler;
    // no kernel routine is bypassed, replaced or given a synthetic return value.
    // LDR r0,[pc,#4]; SWI OS_Write0; B .; DCD string-address
    let words: [UInt32] = [0xe59f0004, 0xef000002, 0xeafffffe, 0x8100]
    let code = words.flatMap { w in (0..<4).map { UInt8(truncatingIfNeeded: w >> ($0*8)) } }
    var text: [UInt8] = [12] // genuine VDU clear/home
    for first in stride(from: 32, through: 96, by: 32) {
        text += (first...min(first+31,126)).map { UInt8($0) }; text += [13,10]
    }
    text += [0]
    for (address, bytes): (UInt32, [UInt8]) in [(0x8000,code),(0x8100,text)] {
        for (i,b) in bytes.enumerated() { check(m.memc.debugWrite(address+UInt32(i),b,space:.logical),"fixture RAM mapping") }
    }
    m.cpu.pc = 0x8000
    end = 0x8008
    try Data(text).write(to: URL(fileURLWithPath: out+"/fixture-text.bin"))
} else { end = 0x3822440 }
let bp = try d.addBreakpoint(.init(id: 0, kind: .execute, start: end))
d.resume()
let deadline = m.ticks + 240_000_000 // Real FileCore/ADFS initialization precedes the banner.
while !d.isStopped && m.ticks < deadline {
    _ = m.run(untilTick: min(deadline,m.ticks+24000), maxInstructions: 1000)
    missing += d.log.map { "\($0.ticks) \($0.text)" }; d.clearLog()
}
check(d.isStopped && m.cpu.pc == end,"failed to reach text test endpoint")
_ = d.removeBreakpoint(bp.id)
// Let VIDC consume four frames, including a complete frame after the initial cursor blink. The fixture spins in its own B .;
// the natural banner path remains in the real input loop.
d.resume(); _ = m.runFrames(4,maxSeconds:0.2)
check(!d.isStopped,"unexpected fault while displaying text")
let f = m.currentFrame
var rgba: [UInt8] = []
for p in f.pixels { rgba += [UInt8(truncatingIfNeeded:p>>16),UInt8(truncatingIfNeeded:p>>8),UInt8(truncatingIfNeeded:p),255] }
try Data(rgba).write(to: URL(fileURLWithPath: out+"/frame.rgba"))
check(writePNG(f,to:URL(fileURLWithPath:out+"/frame.png")),"PNG write")
for (tag,bytes) in m.stateSections() { try Data(bytes).write(to: URL(fileURLWithPath: out+"/\(tag).bin")) }
try Data(m.snapshot(createdBy:"ArcLibre text rendering investigation")).write(to:URL(fileURLWithPath:out+"/state.macarch-state"))
let font = (0..<1792).map { m.memc.debugRead(0x3700+UInt32($0),space:.logical)! }
try Data(font).write(to:URL(fileURLWithPath:out+"/soft-font.bin"))
let trace = (d.trace?.last(4096) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
try trace.write(toFile:out+"/instructions.log",atomically:true,encoding:.utf8)
try missing.joined(separator:"\n").write(toFile:out+"/missing-swis.log",atomically:true,encoding:.utf8)
let report: [String:Any] = ["status":"PASS","test":a[4],"rom_sha256":rom.sha256,"width":f.width,"height":f.height,"bpp":f.bitsPerPixel,"scale_x":f.scaleX,"scale_y":f.scaleY,"pc":m.cpu.pc,"psr":m.cpu.psr,"exceptions":m.cpu.exceptionCounts,"screen_start":m.memc.debugReadWord(0x10c0,space:.logical)!,"line_length":m.memc.debugReadWord(0x1088,space:.logical)!,"row_mult":m.memc.debugReadWord(0x10d8,space:.logical)!,"hardware":m.hardwareState.map { ["name":$0.name,"rows":$0.rows.map { ["label":$0.label,"value":$0.value] }] }]
try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/result.json"))
print("PASS: \(a[4]) endpoint and frame/font capture, \(rom.sha256)")
