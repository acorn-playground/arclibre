// SPDX-License-Identifier: Apache-2.0
// Disc-loaded DOSFS: type commands at the real F12 command line of a
// power-on desktop with an ADFS floppy in drive 0 and, optionally, a PC disc
// (HFE track image) in drive 1. No guest code injection or module loading:
// the guest loads DOSFS itself with *RMLoad. Errors are recorded, not fatal.
//
// A command "DUMP:name" saves drive 1's sectors (IDs 1-9, 512 bytes, in
// track/side/sector order, as a PC reads the disc) to name.img; "WAIT:n"
// runs n more emulated seconds; "KEYS:text" types text without Return;
// "INSERT0:path" swaps the disc in drive 0 for a PC disc (HFE) and
// "DUMP0:name" saves that disc like DUMP.
// At the end drive 0 is saved as disc0.adf and drive 1 as final.img.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count>=6,"DOSFSProbe ROM ROM_DIRECTORY DISC0 DISC1|- OUTPUT COMMAND...")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[5]),commands=Array(a[6...])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
precondition(rom.sha256==layout["rom_sha256"] as! String)
let pc=a[4] != "-"
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[];config.monitor="standard";config.powerOnKeys=[0x34]
// Floppy drive count (byte 135), drive 0, the usual desktop settings and
// FileSwitch's "truncate long names" bit (byte 28 bit 0) set, so DOSFS's
// 8.3 truncation is the deterministic behaviour under test.
config.cmosSettings=[.init(byte:135,value:pc ? 2 : 1),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12),.init(byte:28,mask:1,value:1)]
let m=try Machine(configuration:config,rom:rom)
let disc0=try FloppyImage.open(path:a[3],writeProtected:false)
m.insertFloppy(disc0,drive:0)
let disc1:FloppyImage?=pc ? try FloppyImage.open(path:a[4],writeProtected:false) : nil
if let d1=disc1 {m.insertFloppy(d1,drive:1)}
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
// Drive 1 as a PC sees it. Missing sectors or CRC faults are recorded.
var faults:[String]=[]
var inserted0:FloppyImage?=nil
func dump(_ name:String,_ which:FloppyImage?=disc1){
 guard let d1=which else {return}
 var img=[UInt8](repeating:0,count:80*2*9*512)
 for t in 0..<80 {for side in 0..<2 {let hs=d1.layout(side:side,track:t)
  for r in 1...9 {
   let o=((t*2+side)*9+r-1)*512
   guard let h=hs.first(where:{Int($0.id)==r && Int($0.cylinder)==t && $0.size==512}) else {faults.append("\(name) t\(t) s\(side) r\(r) missing");continue}
   if h.idCRCError || h.dataCRCError {faults.append("\(name) t\(t) s\(side) r\(r) crc")}
   let data=d1.readData(h);for i in 0..<512 {img[o+i]=data[i]}
  }
  if hs.count != 9 {faults.append("\(name) t\(t) s\(side) has \(hs.count) sectors")}
 }}
 try! Data(img).write(to:out.appendingPathComponent(name+".img"))
}
run(24_000_000*35)
press(0x0c);run(24_000_000*2)
var screens:[[String]]=[]
for (i,c) in commands.enumerated() {
 current=i
 if c.hasPrefix("DUMP:"){dump(String(c.dropFirst(5)));screens.append([]);continue}
 if c.hasPrefix("DUMP0:"){dump(String(c.dropFirst(6)),inserted0);screens.append([]);continue}
 if c.hasPrefix("INSERT0:"){let im=try FloppyImage.open(path:String(c.dropFirst(8)),writeProtected:false);m.ejectFloppy(drive:0);run(24_000_000);m.insertFloppy(im,drive:0);inserted0=im;run(24_000_000*2);screens.append(m.screenText);continue}
 if c.hasPrefix("WAIT:"){run(24_000_000*UInt64(c.dropFirst(5))!);screens.append(m.screenText);continue}
 if c.hasPrefix("KEYS:"){type(String(c.dropFirst(5)));run(24_000_000*3);screens.append(m.screenText);continue}
 type(c+"\n");run(24_000_000*5);screens.append(m.screenText)
}
current=commands.count
let screen=m.screenText
press(0x47);run(24_000_000*2)
try Data(disc0.mergedImage()).write(to:out.appendingPathComponent("disc0.adf"))
dump("final")
json(["status":"PASS","rom_sha256":rom.sha256,"commands":commands,"screen":screen,"screens":screens,"errors":errors,"undefined_traps":undefined,"drive1_faults":faults],"result")
print("PASS")
