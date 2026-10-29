// External diagnostic harness, 2026. SPDX-License-Identifier: Apache-2.0
// Uses the unmodified GPL-covered MacArch core as a host dependency.
import ArchimedesCore
import Foundation
import zlib

func check(_ condition: Bool, _ message: String) {
    if !condition { fputs("FAIL: \(message)\n", stderr); exit(1) }
}
func json(_ value: Any, _ path: String) throws {
    try JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys]).write(to: URL(fileURLWithPath: path))
}
final class Gzip {
    let file: gzFile
    init(_ path: String) { file = gzopen(path, "wb1")! }
    func put(_ text: String) { let b = Array(text.utf8); let n = b.withUnsafeBytes { gzwrite(file, $0.baseAddress, UInt32($0.count)) }; check(n == b.count, "gzip write") }
    deinit { gzclose(file) }
}
let args = CommandLine.arguments
check(args.count == 4, "usage: BootProbe ROM OUTPUT_DIRECTORY RUN_COUNT")
let rom = try ROMImage.load(paths: [args[1]])
let manifest = try JSONSerialization.jsonObject(with: Data(contentsOf: URL(fileURLWithPath: args[1]).deletingLastPathComponent().appendingPathComponent("rom-layout.json"))) as! [String:Any]
check(rom.sha256 == manifest["rom_sha256"] as! String, "exact packaged experiment")
let out = args[2]
try FileManager.default.createDirectory(atPath: out, withIntermediateDirectories: true)
let checkpoints: [(String, UInt32)] = [
    ("reset-entry", 0), ("physical-entry", 0x380dcdc),
    ("memsize-return", 0x0380dd3c), ("fixed-mappings", 0x380da78),
    ("reset-part1", 0x380e264), ("vectors-installed", 0x380fb9c),
    ("pre-module", 0x380419c)]
var reports: [[String: Any]] = []
for iteration in 1...Int(args[3])! {
    let dir = out + "/cold-\(iteration)"
    try FileManager.default.createDirectory(atPath: dir, withIntermediateDirectories: true)
    var config = MachineConfiguration(model: .a440)
    config.cpu = .arm2; config.ramKB = 4096; config.romPaths = [args[1]]
    config.hardDiscs = []; config.monitor = "standard"; config.powerOnKeys = [0x34]
    let m = try Machine(configuration: config, rom: rom)
    m.powerOn()
    let d = m.debugger
    d.setTracing(4096)
    let hardware = iteration == 1 ? Gzip(dir + "/hardware-writes.log.gz") : nil
    let swis = Gzip(dir + "/swis.log.gz")
    m.cpu.swiObserver = { pc, number in swis.put("\(m.ticks) \(String(pc,radix:16)) \(String(number,radix:16))\n") }
    let hwMessage = iteration == 1 ? "HW PC={PC} " + (0...14).map { "R\($0)={R\($0)}" }.joined(separator: " ") : "HW"
    let hw = try d.addBreakpoint(.init(id: 0, kind: .write, start: 0x03000000, end: 0x03ffffff, logMessage: hwMessage))
    _ = try d.addBreakpoint(.init(id: 0, kind: .execute, start: 4))
    _ = try d.addBreakpoint(.init(id: 0, kind: .execute, start: 12, end: 20))
    _ = try d.addBreakpoint(.init(id: 0, kind: .execute, start: 0x38005c4, logMessage: "MISSING SWI={R11} LR={R14}"))
    let missing = Gzip(dir + "/missing-swis.log.gz")
    var totalLogs = 0, largestDrain = 0
    var stages: [[String: Any]] = []
    for (name, address) in checkpoints {
        let bp = try d.addBreakpoint(.init(id: 0, kind: .execute, start: address))
        if name != "reset-entry" { d.resume() }
        while m.cpu.pc != address || (name != "reset-entry" && !d.isStopped) {
            let before = d.logTotal
            _ = m.run(untilTick: m.ticks + 24000, maxInstructions: 500)
            let count = d.logTotal - before
            check(count == d.log.count, "debug log overflow or undrained entries")
            largestDrain = max(largestDrain, count); totalLogs += count
            if let hardware { hardware.put(d.log.filter { $0.text.hasPrefix("HW") }.map { "\($0.ticks) \($0.text)\n" }.joined()) }
            missing.put(d.log.filter { $0.text.hasPrefix("MISSING") }.map { "\($0.ticks) \($0.text)\n" }.joined())
            d.clearLog()
            if d.isStopped { check(m.cpu.pc == address, "unexpected exception/breakpoint at \(String(m.cpu.pc,radix:16))") }
            check(m.ticks < 24_000_000 * 20, "20 second boot bound")
        }
        _ = d.removeBreakpoint(bp.id)
        check(m.cpu.mode == .supervisor, "SVC26 at \(name)")
        check(!m.cpu.hasSWP && m.cpu.cp15 == nil, "ARM2 CPU configuration")
        if name == "reset-entry" { check(m.cpu.psr == 0x0c000003 && m.cpu.instructionCount == 0, "reset masks and initial PC") }
        if name == "physical-entry" { check(m.cpu.instructionCount == 1, "one reset-vector instruction") }
        if name == "memsize-return" { check(m.cpu.r[0] == 32768 && m.cpu.r[1] == 4194304 && m.cpu.r[2] == 0x036e010c, "real RAM detection") }
        if name == "fixed-mappings" {
            for (logical, physical): (UInt32, UInt32) in [(0,0x80000),(0x1c00000,0x88000),(0x1f00000,0x78000)] {
                for offset: UInt32 in [0, 0x1234, 0x7ffc] {
                    check(m.memc.debugTranslate(logical + offset) == physical + offset, "fixed physical map")
                }
            }
        }
        if name == "reset-part1" || name == "vectors-installed" || name == "pre-module" {
            check(m.cpu.bankedRegisters(.irq)[5] == 0x1f0136c, "IRQ stack")
            check(m.cpu.r[13] <= 0x1c02000 && m.cpu.r[13] >= 0x1c00000, "SVC stack bounds")
            check(m.memc.debugReadWord(0xc28, space: .logical) == 32768, "workspace Page_Size")
        }
        check(m.cpu.exceptionCounts[1] == 0 && m.cpu.exceptionCounts[3] == 0 && m.cpu.exceptionCounts[4] == 0 && m.cpu.exceptionCounts[5] == 0, "no undefined/abort/address exceptions")
        let regs = (0..<15).map { m.cpu.r[$0] }
        var record: [String: Any] = ["checkpoint":name,"pc":m.cpu.pc,"psr":m.cpu.psr,"instructions":m.cpu.instructionCount,"ticks":m.ticks,"registers":regs,"exceptions":m.cpu.exceptionCounts,
            "irq_bank":m.cpu.bankedRegisters(.irq),"fiq_bank":m.cpu.bankedRegisters(.fiq),"user_bank":m.cpu.bankedRegisters(.user),
            "page_size":4096 << m.memc.pageSizeCode,"rom_overlay":m.memc.romOverlay,"rom_sha256":rom.sha256]
        record["hardware"] = m.hardwareState.map { section in ["name":section.name,"rows":section.rows.map { ["label":$0.label,"value":$0.value] }] }
        try json(record, dir + "/\(name).json"); stages.append(record)
        let trace = (d.trace?.last(4096) ?? []).map { e -> String in
            if let irq = e.interrupt { return "\(e.ticks) \(irq)\n" }
            return "\(e.ticks) \(String(format:"%08X %08X",e.pc,e.instruction)) \(e.registerText)\n"
        }.joined()
        try trace.write(toFile: dir + "/\(name)-instructions.log", atomically: true, encoding: .utf8)
        try Data(m.snapshot(createdBy: "ArcLibre kernel boot experiment")).write(to: URL(fileURLWithPath: dir + "/\(name).macarch-state"))
        // Export the public diagnostic sections; each has its upstream documented layout.
        if ["fixed-mappings","vectors-installed","pre-module"].contains(name) {
            for (tag, bytes) in m.stateSections() { try Data(bytes).write(to: URL(fileURLWithPath: dir + "/\(name)-\(tag).bin")) }
        }
        print("cold \(iteration): \(name) PC=\(String(m.cpu.pc,radix:16)) instructions=\(m.cpu.instructionCount) ticks=\(m.ticks)")
        fflush(stdout)
    }
    let hwHits = d.breakpoints.first { $0.id == hw.id }!.hitCount
    let report: [String: Any] = ["status":"PASS","cold_run":iteration,"hardware_write_events":hwHits,"drained_log_events":totalLogs,"largest_drain":largestDrain,"log_limit":Debugger.logLimit,"no_log_loss":true,"stages":stages]
    try json(report,dir + "/result.json"); reports.append(report)
    m.cpu.swiObserver = nil
}
try json(["status":"PASS","runs":reports], out + "/repeatability.json")
