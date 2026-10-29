// SPDX-License-Identifier: Apache-2.0
// Real keyboard events only; observes the unchanged MacArch core and guest kernel.
import Foundation
import ArchimedesCore
import ProbeSupport
func check(_ b:Bool,_ s:String) { if !b { fputs("FAIL: \(s)\n",stderr);exit(1) } }
let a=CommandLine.arguments
check(a.count==5,"KeyboardProbe ROM SUPERVISOR_SNAPSHOT SYMBOLS OUTPUT")
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]))) as! [String:NSNumber]
func sym(_ n:String)->UInt32 { symbols[n]!.uint32Value }
let out=a[4];try FileManager.default.createDirectory(atPath:out,withIntermediateDirectories:true)
func json(_ x:Any,_ name:String) throws { try JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/"+name+".json")) }
let d=m.debugger;d.setTracing(4096)
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
for (name,format) in [("KeyVector","KEY reason={R0} key={R1}"),("ReturnChar","CHAR r0={R0}"),("DoHelpOnNextKeyWord","HELP"),("NoHighSWIHandler","MISSING swi={R11}")] {
    _ = try d.addBreakpoint(.init(id:0,kind:.execute,start:sym(name),logMessage:format))
}
_ = try d.addBreakpoint(.init(id:0,kind:.access,start:0x03200004,logMessage:"KART pc={PC} r0={R0} r1={R1} r2={R2}"))
var events:[String]=[],inputs:[[String:Any]]=[],stages:[[String:Any]]=[],protocolErrors:[String]=[]
m.keyboard.log={protocolErrors.append($0)}
func run(_ seconds:Double) {
    let end=m.ticks+UInt64(seconds*24_000_000);d.resume()
    while m.ticks<end && !d.isStopped {
        _=m.run(untilTick:min(end,m.ticks+24000),maxInstructions:1000)
        check(d.log.count<Debugger.logLimit,"log overflow")
        events += d.log.map { "\($0.ticks) \($0.text)" };d.clearLog()
    }
    check(!d.isStopped,"unexpected exception stop")
}
func down(_ k:UInt8) { inputs.append(["tick":m.ticks,"action":"down","code":k]);m.keyDown(k) }
func up(_ k:UInt8) { inputs.append(["tick":m.ticks,"action":"up","code":k]);m.keyUp(k) }
func press(_ k:UInt8,_ modifiers:[UInt8]=[]) {
    for c in modifiers { down(c) };if !modifiers.isEmpty { run(0.03) }
    down(k);run(0.08);up(k);run(0.06)
    for c in modifiers.reversed() { up(c) };run(0.1)
}
func chars()->[UInt32] { events.filter{$0.contains("CHAR r0=&")}.map { UInt32($0.components(separatedBy:"CHAR r0=&")[1],radix:16)! } }
func stage(_ name:String) throws {
    check(m.keyboard.held.isEmpty,"held host keys at \(name)")
    let workspace=(0..<128).map { m.memc.debugRead(sym("KeyWorkSpace")+UInt32($0),space:.logical)! }
    let rec:[String:Any]=["stage":name,"tick":m.ticks,"instructions":m.cpu.instructionCount,"pc":m.cpu.pc,"psr":m.cpu.psr,"exceptions":m.cpu.exceptionCounts,"leds":m.keyboard.leds,"screen":m.screenText,"chars":chars(),"workspace":workspace]
    stages.append(rec);try json(rec,name)
    for (tag,b) in m.stateSections() where tag=="KBD" { try Data(b).write(to:URL(fileURLWithPath:out+"/\(name)-KBD.bin")) }
    print(name+": "+m.screenText.joined(separator:" | "));fflush(stdout)
}
run(0.2);try stage("ready")
press(0x3c);press(0x52);press(0x50);try stage("abc")
press(0x1e);try stage("backspace")
press(0x3e,[0x4c]);press(0x29,[0x58]);press(0x3f);try stage("shift-release")
press(0x2d,[0x3b]);try stage("ctrl-u")
press(0x2d);try stage("ctrl-release")
press(0x5d);press(0x3c);try stage("caps-on")
press(0x5d);press(0x52);try stage("caps-off")
press(0);try stage("escape")
let start=chars().count
down(0x4f);run(1.2);up(0x4f);run(0.15);let afterRelease=chars().count
run(0.8);check(chars().count==afterRelease,"repeat continued after release")
check(afterRelease-start>=3,"OS autorepeat did not occur")
try stage("repeat-release")
press(0x2d,[0x3b]);press(0x3c);try stage("repeat-recovery")
press(0x2d,[0x3b]);press(0x41);press(0x29);press(0x44);press(0x30);try stage("help-typed")
press(0x47);run(0.3);try stage("help-return")
check(m.screenText.contains { $0.contains("Explain the syntax message format") }, "complete Help output")
check(!m.screenText.contains { $0.contains("NoSuchSWI") || $0.contains("TokNFnd") }, "Help translation error")
check(protocolErrors.isEmpty,"keyboard protocol errors")
check([1,3,4,5,7].allSatisfy { m.cpu.exceptionCounts[$0]==0 },"CPU fault")
try json(inputs,"input-events");try json(stages,"stages");try json(protocolErrors,"protocol-errors")
try events.joined(separator:"\n").write(toFile:out+"/events.log",atomically:true,encoding:.utf8)
try Data(m.snapshot(createdBy:"ArcLibre keyboard experiment")).write(to:URL(fileURLWithPath:out+"/final.macarch-state"))
for (tag,b) in m.stateSections() { try Data(b).write(to:URL(fileURLWithPath:out+"/final-\(tag).bin")) }
let trace=(d.trace?.last(4096) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
try trace.write(toFile:out+"/final-instructions.log",atomically:true,encoding:.utf8)
let f=m.currentFrame
check(writePNG(f,to:URL(fileURLWithPath:out+"/final.png")),"PNG")
try json(["status":"CAPTURED","rom_sha256":rom.sha256,"repeat_characters":afterRelease-start,"key_events":inputs.count,"exceptions":m.cpu.exceptionCounts],"result")
