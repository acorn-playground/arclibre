// SPDX-License-Identifier: Apache-2.0
// Real keyboard events only; observes the unchanged MacArch core and guest kernel.
import Foundation
import ArchimedesCore
import ProbeSupport
func check(_ b:Bool,_ s:String) { if !b { fputs("FAIL: \(s)\n",stderr);exit(1) } }
let a=CommandLine.arguments
check(a.count==5,"KeyboardSelectProbe ROM SUPERVISOR_SNAPSHOT SYMBOLS OUTPUT")
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]))) as! [String:NSNumber]
func sym(_ n:String)->UInt32 { symbols[n]!.uint32Value }
let out=a[4];try FileManager.default.createDirectory(atPath:out,withIntermediateDirectories:true)
func json(_ x:Any,_ name:String) throws { try JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/"+name+".json")) }
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]).deletingLastPathComponent().appendingPathComponent("rom-layout.json"))) as! [String:Any]
let km=(layout["modules"] as! [[String:Any]]).first { $0["component"] as? String == "IntKey" }!
let ks=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]).deletingLastPathComponent().appendingPathComponent("modules/IntKey/symbols.json"))) as! [String:[String:NSNumber]]
func keyAddress(_ name:String)->UInt32 { UInt32(km["base"] as! Int)+ks[name]!["value"]!.uint32Value }
let d=m.debugger;d.setTracing(4096)
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
for (name,format) in [("KeyVector","KEY reason={R0} key={R1}"),("ReturnChar","CHAR r0={R0}"),("DoHelpOnNextKeyWord","HELP"),("NoHighSWIHandler","MISSING swi={R11}")] {
    _ = try d.addBreakpoint(.init(id:0,kind:.execute,start:sym(name),logMessage:format))
}
_ = try d.addBreakpoint(.init(id:0,kind:.access,start:0x03200004,logMessage:"KART pc={PC} r0={R0} r1={R1} r2={R2}"))
for name in ["SetUpKeyStructureAndHandlerIfUs","KeyStructInit","ProcessKShift","ProcessKCtrl","ProcessKAlt","ProcessK1Pad"] {
    _ = try d.addBreakpoint(.init(id:0,kind:.execute,start:keyAddress(name),logMessage:"INTKEY "+name+" r0={R0} r1={R1} r12={R12}"))
}
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
let keys:[Character:UInt8] = ["a":0x3c,"b":0x52,"c":0x50,"d":0x3e,"e":0x29,"f":0x3f,"g":0x40,"h":0x41,"i":0x2e,"j":0x42,"k":0x43,"l":0x44,"m":0x54,"n":0x53,"o":0x2f,"p":0x30,"q":0x27,"r":0x2a,"s":0x3d,"t":0x2b,"u":0x2d,"v":0x51,"w":0x28,"x":0x4f,"y":0x2c,"z":0x4e," ":0x5f]
func command(_ text:String) { for c in text { press(keys[c]!) };press(0x47);run(0.2) }
run(0.2);try stage("ready")
for i in 1...3 {
    command("keyboard uk");try stage("select-\(i)")
    press(0x3c);press(0x3e,[0x4c]);press(0x2d,[0x3b]);try stage("input-\(i)")
}
command("keyboard");try stage("query")
check(m.screenText.contains("UK"),"keyboard query UK")
command("keyboard nonsense");try stage("invalid")
check(m.screenText.contains { $0.lowercased().contains("unknown keyboard") },"real invalid keyboard error")
command("keyboard");try stage("query-after-error")
press(0x33);press(0x33,[0x4c]);try stage("backslash-bar")
press(0x2d,[0x3b]);press(0x4a);press(0x49);try stage("keypad")
press(0x2d,[0x3b])
down(0x5e);run(0.03);press(0x4a);press(0x49);up(0x5e);run(0.3);try stage("alt-digits")
press(0x2d,[0x3b]);press(0x3c);try stage("recovery")
press(0x2d,[0x3b]);command("help keyboard");try stage("help-keyboard")
check(!m.screenText.contains { $0.contains("NoSuchSWI") || $0.contains("TokNFnd") },"keyboard help translation error")
check(protocolErrors.isEmpty,"keyboard protocol errors")
check([1,3,4,5,7].allSatisfy { m.cpu.exceptionCounts[$0]==0 },"CPU fault")
try json(inputs,"input-events");try json(stages,"stages");try json(protocolErrors,"protocol-errors")
try events.joined(separator:"\n").write(toFile:out+"/events.log",atomically:true,encoding:.utf8)
try Data(m.snapshot(createdBy:"Open Archimedes keyboard selection experiment")).write(to:URL(fileURLWithPath:out+"/final.macarch-state"))
for (tag,b) in m.stateSections() { try Data(b).write(to:URL(fileURLWithPath:out+"/final-\(tag).bin")) }
let trace=(d.trace?.last(4096) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
try trace.write(toFile:out+"/final-instructions.log",atomically:true,encoding:.utf8)
let f=m.currentFrame
check(writePNG(f,to:URL(fileURLWithPath:out+"/final.png")),"PNG")
try json(["status":"CAPTURED","rom_sha256":rom.sha256,"key_events":inputs.count,"exceptions":m.cpu.exceptionCounts],"result")
