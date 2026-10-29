// SPDX-License-Identifier: Apache-2.0
// The A5000 family's "new I/O" (IOEB and 82C711: 765 floppy controller, IDE,
// serial, parallel): a power-on desktop on the given model and monitor, with
// a writable ADFS floppy in drive 0 and, on a model with IDE, a host-built
// ADFS hard disc as drive 4. Commands are typed at the real F12 command line;
// no guest code injection or module loading. "WAIT:n" runs n more emulated
// seconds. Before each command "COMMAND i" goes to stderr, so the 82C711 and
// IOEB accesses MacArch traces there (MACARCH_SIO_TRACE) can be attributed.
// Set up before power-on: "DISC1:path" puts a floppy (an HFE track image) in
// drive 1; "IDE:name,type,path" adds a host file to the hard disc's root.
// "DUMP1:name,sectors,cylinders[,double]" saves drive 1's 512-byte sectors,
// as a PC reads the disc (a 40-track disc double-stepped), to name.img.
// At the end drive 0 is saved as disc0.adf and the hard disc's files, read
// back by MacArch's ADFS reader, go into result.json and the ide directory.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count>=7,"NewIOProbe ROM ROM_DIRECTORY MODEL MONITOR DISC0 OUTPUT COMMAND...")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[6])
let setup=a[7...].filter{$0.hasPrefix("DISC1:") || $0.hasPrefix("IDE:")},commands=a[7...].filter{!setup.contains($0)}
let disc1Path=setup.first{$0.hasPrefix("DISC1:")}.map{String($0.dropFirst(6))}
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
precondition(rom.sha256==layout["rom_sha256"] as! String)
let model=MachineModel(rawValue:a[3])!
var config=MachineConfiguration(model:model)
config.cpu=model.defaultCPU;config.ramKB=model.defaultRAMKB;config.romPaths=[a[1]];config.monitor=a[4];config.powerOnKeys=[0x34]
let hdf=out.appendingPathComponent("ide.hdf").path
config.hardDiscs=model.hasIDE ? [hdf] : []
// One or two floppies and, with IDE, one IDE drive (ADFS's byte 135: floppies
// in bits 0-2, IDE drives in bits 6-7); drive 0, and the usual desktop settings.
let floppies:UInt8=disc1Path==nil ? 1 : 2
config.cmosSettings=[.init(byte:135,value:floppies|(model.hasIDE ? 0x40 : 0)),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12)]
if model.hasIDE {
 try? FileManager.default.removeItem(atPath:hdf)
 try ADFSHardDiscBuilder.create(path:hdf,geometry:HardDiscGeometry.idePresets[0].geometry,name:"IDEDisc",
  items:[.init(path:["ReadMe"],data:Array("ArcLibre IDE hard disc, built on the host.\n".utf8),type:0xfff)]+setup.filter{$0.hasPrefix("IDE:")}.map{
   let f=$0.dropFirst(4).split(separator:",",maxSplits:2).map(String.init)
   return .init(path:[f[0]],data:Array(try! Data(contentsOf:URL(fileURLWithPath:f[2]))),type:UInt16(f[1],radix:16)!)})
}
let m=try Machine(configuration:config,rom:rom)
let disc0=try FloppyImage.open(path:a[5],writeProtected:false)
m.insertFloppy(disc0,drive:0)
let disc1=try disc1Path.map{try FloppyImage.open(path:$0,writeProtected:false)}
if let d1=disc1 {m.insertFloppy(d1,drive:1)}
// NEWIO_FDC_LOG=1: the 765's commands and results to stderr, for diagnosis.
if ProcessInfo.processInfo.environment["NEWIO_FDC_LOG"] != nil {m.superIO?.fdc.log={fputs("FDC "+$0+"\n",stderr)}}
m.powerOn();let d=m.debugger
var errors:[[String:Any]]=[],current=0,undefined=0
func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical) ?? 0xffffffff}
func text(_ p:UInt32)->String {var b:[UInt8]=[];for i in 0..<256 {guard let v=m.memc.debugRead(p+UInt32(i),space:.logical),v>=32 else{break};b.append(v)};return String(bytes:b,encoding:.isoLatin1) ?? "?"}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
func check(_ b:Bool,_ s:String){if !b{json(["failure":s,"pc":m.cpu.pc,"errors":errors,"text":m.screenText],"failure");fputs("FAIL: \(s)\n",stderr);exit(1)}}
m.cpu.swiObserver={pc,n in if n & ~UInt32(0x20000)==0x400df{errors.append(["command":current,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}}
// Aborts fail the run; undefined instructions (the FPEmulator's) are counted.
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
func run(_ ticks:UInt64){let end=m.ticks+ticks;d.resume();while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2_400_000),maxInstructions:300_000)
 if d.isStopped {check(m.cpu.pc==4,"processor fault at \(String(format:"%08X",m.cpu.pc))");undefined+=1;d.resume()}
 }}
func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
let second:UInt64=24_000_000
var faults:[String]=[]
func dump(_ spec:String){
 let f=spec.split(separator:",").map(String.init),spt=Int(f[1])!,cylinders=Int(f[2])!,step=f.count>3 ? 2 : 1
 guard let d1=disc1 else {return}
 var img=[UInt8](repeating:0,count:cylinders*2*spt*512)
 for c in 0..<cylinders {for side in 0..<2 {let hs=d1.layout(side:side,track:c*step)
  for r in 1...spt {
   guard let h=hs.first(where:{Int($0.id)==r && Int($0.cylinder)==c && $0.size==512}) else {faults.append("\(f[0]) c\(c) s\(side) r\(r) missing");continue}
   if h.idCRCError || h.dataCRCError {faults.append("\(f[0]) c\(c) s\(side) r\(r) crc")}
   let data=d1.readData(h),o=((c*2+side)*spt+r-1)*512;for i in 0..<512 {img[o+i]=data[i]}
  }}}
 try! Data(img).write(to:out.appendingPathComponent(f[0]+".img"))
}
run(second*35)
fputs("DESKTOP\n",stderr)
let desktop=m.screenText
press(0x0c);run(second*2)
var screens:[[String]]=[]
for (i,c) in commands.enumerated() {
 current=i;fputs("COMMAND \(i)\n",stderr)
 if c.hasPrefix("DUMP1:"){dump(String(c.dropFirst(6)));screens.append([]);continue}
 if c.hasPrefix("WAIT:"){run(second*UInt64(c.dropFirst(5))!);screens.append(m.screenText);continue}
 type(c+"\n");run(second*5);screens.append(m.screenText)
}
current=commands.count;fputs("END\n",stderr)
press(0x47);run(second*2)
try Data(disc0.mergedImage()).write(to:out.appendingPathComponent("disc0.adf"))
var hard:[[String:Any]]=[]
if model.hasIDE {
 let files=out.appendingPathComponent("ide");try FileManager.default.createDirectory(at:files,withIntermediateDirectories:true)
 for item in try ADFSDiscReader.read(path:hdf).items {
  try Data(item.data).write(to:files.appendingPathComponent(item.path.joined(separator:".")))
  hard.append(["path":item.path.joined(separator:"."),"length":item.data.count,"sha256":SHA256.hex(item.data),"load":item.load,"exec":item.exec])
 }
}
json(["status":"PASS","rom_sha256":rom.sha256,"model":model.rawValue,"cpu":config.cpu.rawValue,"monitor":a[4],"commands":commands,"desktop":desktop,"screens":screens,
 "errors":errors,"undefined_traps":undefined,"drive1_faults":faults,"hard_disc":hard,"vidc_clock_select":Int(m.superIO?.clockSelect ?? 255)],"result")
print("PASS")
