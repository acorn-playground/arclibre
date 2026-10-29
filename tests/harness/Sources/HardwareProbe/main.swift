// SPDX-License-Identifier: Apache-2.0
// Commands at the real F12 command line of a power-on desktop on an emulated
// A3000 or A440/1 (IOC, 6551 serial, IOC printer port). After each command it
// records the screen, IOC's IRQ A mask and status, the printer strobe latch,
// and every guest write to the printer data latch (bank 5 register &10) and
// to the 6551 (bank 3), which the emulator reports as unmodelled accesses.
// No guest code injection or module loading.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count>=5 && ["A3000","A440"].contains(a[3]),"HardwareProbe ROM ROM_DIRECTORY A3000|A440 OUTPUT COMMAND...")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[4]),commands=Array(a[5...])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:a[3]=="A3000" ? .a3000 : .a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[];config.monitor="standard";config.powerOnKeys=[0x34]
config.cmosSettings=[.init(byte:135,value:1),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12)]
let m=try Machine(configuration:config,rom:rom)
m.powerOn();let d=m.debugger
var errors:[[String:Any]]=[],undefined=0,current=0
var printerData:[[String:Any]]=[],acia:[[String:Any]]=[],otherUnmodelled:[String:Int]=[:]
m.ioc.unknownAccess={s in
 if s.hasPrefix("IOC write bank 5 reg 10 = "){printerData.append(["command":current,"byte":Int(s.suffix(2),radix:16)!])}
 else if s.hasPrefix("IOC write bank 3 "){acia.append(["command":current,"access":s])}
 else {otherUnmodelled[s.replacingOccurrences(of:#" = [0-9A-F]{2}$"#,with:"",options:.regularExpression),default:0]+=1}
}
func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical) ?? 0xffffffff}
func text(_ p:UInt32)->String {var b:[UInt8]=[];for i in 0..<256 {guard let v=m.memc.debugRead(p+UInt32(i),space:.logical),v>=32 else{break};b.append(v)};return String(bytes:b,encoding:.isoLatin1) ?? "?"}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
func check(_ b:Bool,_ s:String){if !b{json(["failure":s,"pc":m.cpu.pc,"errors":errors,"text":m.screenText],"failure");fputs("FAIL: \(s)\n",stderr);exit(1)}}
m.cpu.swiObserver={pc,n in if n & ~UInt32(0x20000)==0x400df{errors.append(["command":current,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}}
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
func run(_ ticks:UInt64){let end=m.ticks+ticks;d.resume();while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2_400_000),maxInstructions:300_000)
 if d.isStopped {check(m.cpu.pc==4,"processor fault");undefined+=1;d.resume()}
 }}
func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
// IOC IRQ A: bit 0 printer busy (0 => busy), bit 2 printer acknowledge.
func state()->[String:Any] {["irq_a_mask":Int(m.ioc.irqAMask),"irq_a_status":Int(m.ioc.irqAStatus),"latch_a":Int(m.ioc.latchA),"printer_data_writes":printerData.count,"acia_writes":acia.count]}
run(24_000_000*35)
let desktop=state()
press(0x0c);run(24_000_000*2)
var screens:[[String]]=[],states:[[String:Any]]=[]
for (i,c) in commands.enumerated() {
 current=i
 if c.hasPrefix("WAIT:"){run(24_000_000*UInt64(c.dropFirst(5))!)}
 else {type(c+"\n");run(24_000_000*5)}
 screens.append(m.screenText);states.append(state())
}
current=commands.count
json(["status":"PASS","rom_sha256":rom.sha256,"model":a[3],"commands":commands,"desktop":desktop,"screens":screens,"states":states,"errors":errors,
 "printer_data":printerData,"acia":acia,"other_unmodelled":otherUnmodelled,"undefined_traps":undefined],"result")
print("PASS")
