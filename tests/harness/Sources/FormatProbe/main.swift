// SPDX-License-Identifier: Apache-2.0
// Disc formatting and low-level writes through the real F12 command line of a
// power-on desktop: an ADFS floppy in drive 0 and a generated ST506 hard disc
// as drive 4. No guest code injection or module loading. Errors are recorded,
// not fatal. "WAIT:n" runs n more emulated seconds; "KEYS:text" types text
// without Return. At the end drive 0 is saved as disc0.adf.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count>=5,"FormatProbe ROM ROM_DIRECTORY DISC0 OUTPUT COMMAND...")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[4]),commands=Array(a[5...])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[out.appendingPathComponent("test.hdf").path];config.monitor="standard";config.powerOnKeys=[0x34]
// One floppy and one ST506 drive (byte 135), drive 0 and the usual desktop settings.
config.cmosSettings=[.init(byte:135,value:9),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12)]
try? FileManager.default.removeItem(atPath:config.hardDiscs[0]!)
try ADFSHardDiscBuilder.create(path:config.hardDiscs[0]!,geometry:HardDiscGeometry(cylinders:615,heads:4,sectorsPerTrack:32,sectorSize:256),name:"ArcDisc",items:[.init(path:["ReadMe"],data:Array("ArcLibre original ST506 hard disc.\n".utf8),type:0xfff)])
let m=try Machine(configuration:config,rom:rom)
let disc0=try FloppyImage.open(path:a[3],writeProtected:false)
m.insertFloppy(disc0,drive:0)
m.powerOn();let d=m.debugger
var errors:[[String:Any]]=[],undefined=0,current=0
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
run(24_000_000*35)
press(0x0c);run(24_000_000*2)
var screens:[[String]]=[]
for (i,c) in commands.enumerated() {
 current=i
 if c.hasPrefix("WAIT:"){run(24_000_000*UInt64(c.dropFirst(5))!);screens.append(m.screenText);continue}
 if c.hasPrefix("KEYS:"){type(String(c.dropFirst(5)));run(24_000_000*3);screens.append(m.screenText);continue}
 type(c+"\n");run(24_000_000*5);screens.append(m.screenText)
}
current=commands.count
let screen=m.screenText
press(0x47);run(24_000_000*2)
try Data(disc0.mergedImage()).write(to:out.appendingPathComponent("disc0.adf"))
json(["status":"PASS","rom_sha256":rom.sha256,"commands":commands,"screen":screen,"screens":screens,"errors":errors,"undefined_traps":undefined],"result")
print("PASS")
