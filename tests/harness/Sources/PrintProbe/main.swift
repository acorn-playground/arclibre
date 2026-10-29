// SPDX-License-Identifier: Apache-2.0
// Drive the real desktop of a power-on A440/1 with the printing floppy in
// drive 0, then save the floppy. Steps, in order:
//   CLICK:x,y[,n]        select n times at OS coordinates x,y
//   DRAG:x0,y0,x1,y1     select-drag from one point to another
//   WAIT:n               run for n seconds
//   F12                  the command line
//   SHOT:name            save the screen as name.png (for working out coordinates)
//   anything else        typed, then Return
// Used by tests/run_printing.py to install a printer in !Printers and print.
// No guest code injection or module loading.
import Foundation
import ArchimedesCore
import ProbeSupport
let a=CommandLine.arguments
precondition(a.count>=6,"PrintProbe ROM BUILD_DIRECTORY DISC OUTPUT STEP...")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[4]),steps=Array(a[5...])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[];config.monitor="standard";config.powerOnKeys=[0x34]
config.cmosSettings=[.init(byte:135,value:1),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12)]
let m=try Machine(configuration:config,rom:rom)
let disc=try FloppyImage.open(path:a[3],writeProtected:false)
m.insertFloppy(disc,drive:0)
m.powerOn();let d=m.debugger
var errors:[[String:Any]]=[],undefined=0,current=0
func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical) ?? 0xffffffff}
func text(_ p:UInt32)->String {var b:[UInt8]=[];for i in 0..<256 {guard let v=m.memc.debugRead(p+UInt32(i),space:.logical),v>=32 else{break};b.append(v)};return String(bytes:b,encoding:.isoLatin1) ?? "?"}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
func check(_ b:Bool,_ s:String){if !b{json(["failure":s,"pc":m.cpu.pc,"errors":errors,"text":m.screenText],"failure");fputs("FAIL: \(s)\n",stderr);exit(1)}}
// Wimp_ReportError: the desktop's error boxes, with the step that raised them.
m.cpu.swiObserver={pc,n in if n & ~UInt32(0x20000)==0x400df{errors.append(["step":current,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}}
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
func run(_ ticks:UInt64){let end=m.ticks+ticks;d.resume();while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2_400_000),maxInstructions:300_000)
 if d.isStopped {check(m.cpu.pc==4,"processor fault");undefined+=1;d.resume()}
 }}
func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
// The pointer position in OS units is the kernel's at &5AC/&5B0; a mouse count is two OS units.
func move(_ x:Int,_ y:Int){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000)}
func numbers(_ s:Substring)->[Int]{s.split(separator:",").map{Int($0)!}}
run(24_000_000*35)
var screens:[[String]]=[]
for (i,s) in steps.enumerated() {
 current=i
 if s.hasPrefix("CLICK:"){let v=numbers(s.dropFirst(6));move(v[0],v[1]);for _ in 0..<(v.count>2 ? v[2]:1){m.keyDown(0x70);run(1_920_000);m.keyUp(0x70);run(1_920_000)};run(24_000_000*2)}
 else if s.hasPrefix("DRAG:"){let v=numbers(s.dropFirst(5));move(v[0],v[1]);m.keyDown(0x70);run(4_800_000);move((v[0]+v[2])/2,(v[1]+v[3])/2);move(v[2],v[3]);run(4_800_000);m.keyUp(0x70);run(24_000_000*2)}
 else if s.hasPrefix("WAIT:"){run(24_000_000*UInt64(s.dropFirst(5))!)}
 else if s=="F12"{press(0x0c);run(24_000_000*2)}
 else if s.hasPrefix("SHOT:"){check(writePNG(m.currentFrame,to:out.appendingPathComponent(String(s.dropFirst(5))+".png")),"PNG")}
 else {type(s+"\n");run(24_000_000*2)}
 screens.append(m.screenText)
}
current=steps.count
press(0x47);run(24_000_000*2)
try Data(disc.mergedImage()).write(to:out.appendingPathComponent("disc.adf"))
json(["status":"PASS","rom_sha256":rom.sha256,"steps":steps,"screens":screens,"errors":errors,"undefined_traps":undefined],"result")
print("PASS")
