// SPDX-License-Identifier: Apache-2.0
// Actual FileSwitch/FileCore/ADFS calls against an original generated, protected disc.
import Foundation
import ArchimedesCore
func check(_ b:Bool,_ s:String) { if !b { fputs("FAIL: \(s)\n",stderr);exit(1) } }
let a=CommandLine.arguments;check(a.count==5,"FloppyProbe ROM SNAPSHOT DISC_DIRECTORY OUTPUT")
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let out=a[4];try FileManager.default.createDirectory(atPath:out,withIntermediateDirectories:true)
let manifest=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]+"/manifest.json"))) as! [String:Any]
let files=manifest["files"] as! [[String:Any]]
let disc=try FloppyImage.open(path:a[3]+"/arm2-test.adf",writeProtected:true)
m.insertFloppy(disc,drive:0);m.fdc.trace=RingBuffer<WD1772.TraceEvent>(capacity:16384)
try Data(m.snapshot(createdBy:"Open Archimedes protected floppy at Supervisor")).write(to:URL(fileURLWithPath:out+"/mounted-supervisor.macarch-state"))
let d=m.debugger;d.setTracing(4096)
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
let returnBP=try d.addBreakpoint(.init(id:0,kind:.execute,start:0x800c))
var calls:[[String:Any]]=[],swis:[String]=[],fiqs:[[String:Any]]=[]
m.cpu.swiObserver={pc,n in swis.append("\(m.ticks) \(String(pc,radix:16)) \(String(n,radix:16))")}
func bytes(_ p:UInt32,_ n:Int)->[UInt8] { (0..<n).map { m.memc.debugRead(p+UInt32($0),space:.logical)! } }
func word(_ p:UInt32)->UInt32 { m.memc.debugReadWord(p,space:.logical)! }
func write(_ p:UInt32,_ b:[UInt8]) { for (i,v) in b.enumerated() { check(m.memc.debugWrite(p+UInt32(i),v,space:.logical),"client memory") } }
func words(_ p:UInt32,_ w:[UInt32]) { write(p,w.flatMap { v in (0..<4).map { UInt8(truncatingIfNeeded:v>>($0*8)) } }) }
func string(_ p:UInt32,_ s:String) { write(p,Array(s.utf8)+[0]) }
func readString(_ p:UInt32)->String { String(bytes:bytes(p,1024).prefix{$0 != 0},encoding:.isoLatin1) ?? "<invalid>" }
func dump(_ stage:String) throws {
 for (tag,b) in m.stateSections() { try Data(b).write(to:URL(fileURLWithPath:out+"/\(stage)-\(tag).bin")) }
 try JSONSerialization.data(withJSONObject:["calls":calls,"fiqs":fiqs,"exceptions":m.cpu.exceptionCounts,"screen":m.screenText,"pc":m.cpu.pc,"psr":m.cpu.psr],options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/progress.json"))
 try m.fdc.trace.elements.map{$0.description}.joined(separator:"\n").write(toFile:out+"/fdc.log",atomically:true,encoding:.utf8)
 try swis.joined(separator:"\n").write(toFile:out+"/swis.log",atomically:true,encoding:.utf8)
 let trace=(d.trace?.last(4096) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
 try trace.write(toFile:out+"/instructions.log",atomically:true,encoding:.utf8)
}
@discardableResult func call(_ name:String,_ swi:UInt32,_ args:[UInt32],error:Bool=false)throws->[UInt32] {
 words(0x8000,[0xe59f8008,0xe89800ff,0xef020000|swi,0xeafffffe,0x8020]);words(0x8020,args+Array(repeating:0,count:8-args.count))
 let before=m.cpu.exceptionCounts;let f=try d.addBreakpoint(.init(id:0,kind:.execute,start:0x1c))
 var captured=false
 m.cpu.pc=0x8000;d.resume();let deadline=m.ticks+240_000_000
 while m.ticks<deadline {
  _=m.run(untilTick:min(deadline,m.ticks+240_000),maxInstructions:20000)
  if d.isStopped {
   if m.cpu.pc==0x1c && !captured {
    captured=true;check(m.cpu.mode == .fiq && m.cpu.psr&0x0c000003==0x0c000001,"FIQ26 with both masks")
    let n=fiqs.count;try Data(bytes(0x1c,512)).write(to:URL(fileURLWithPath:out+"/fiq-\(n).bin"))
    var observation:[String:Any]=["call":name,"tick":m.ticks,"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]},"capture":"fiq-\(n).bin"]
    _=d.removeBreakpoint(f.id);d.resume()
    var path:[[String:Any]]=[]
    while m.cpu.mode == .fiq && path.count<4096 && !d.isStopped {
     path.append(["pc":m.cpu.pc,"word":word(m.cpu.pc),"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]}])
     _=m.run(untilTick:m.ticks+24000,maxInstructions:1)
    }
    check(m.cpu.mode != .fiq,"sampled FIQ returned")
    observation["instructions"]=path;observation["return_pc"]=m.cpu.pc;observation["return_psr"]=m.cpu.psr
    fiqs.append(observation);continue
   }
   break
  }
 }
 if !captured {_=d.removeBreakpoint(f.id)}
 let r=(0..<8).map{m.cpu.r[$0]};let v=m.cpu.psr&0x10000000 != 0
 let row:[String:Any]=["name":name,"swi":swi,"input":args,"output":r,"psr":m.cpu.psr,"pc":m.cpu.pc,"tick":m.ticks,"exceptions_before":before,"exceptions_after":m.cpu.exceptionCounts,"error_text":v ? readString(r[0]+4):""]
 calls.append(row);try dump("latest")
 print("\(name): pc=\(String(m.cpu.pc,radix:16)) V=\(v) \(v ? readString(r[0]+4):"")");fflush(stdout)
 check(d.isStopped && m.cpu.pc==0x800c,"SWI timeout/fault: "+name)
 check(v==error,"unexpected V: "+name)
 check(disc.writeProtected && !disc.isModified && disc.overlay.isEmpty,"disc stayed read-only")
 check([1,3,4,5].allSatisfy{m.cpu.exceptionCounts[$0]==0},"CPU fault")
 return r
}
let client=try call("Claim client workspace",0x1e,[6,0,0,65536])[2]
let filename=client,buffer=client+1024
string(filename,"ADFS::0.$");try call("Catalogue",0x29,[5,filename])
for f in files {
 let name=f["name"] as! String;let data=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/"+name)))
 string(filename,"ADFS::0.$."+name)
 let info=try call("Info "+name,8,[5,filename])
 check(info[0]==1 && info[2]==(f["load"] as! NSNumber).uint32Value && info[3]==(f["execute"] as! NSNumber).uint32Value && info[4]==data.count && info[5]==0x11,"catalogue attributes: "+name)
 let handle=try call("Open "+name,0x0d,[0x40,filename])[0];check(handle != 0,"real open handle")
 let size=try call("Length "+name,9,[2,handle]);check(size[2]==data.count,"stream length")
 let first=try call("BGet "+name,0x0a,[0,handle]);check(first[0]==data[0],"first byte")
 try call("Seek "+name,9,[1,handle,0])
 write(buffer,Array(repeating:0xa5,count:data.count))
 let read=try call("Read "+name,0x0c,[4,handle,buffer,UInt32(data.count)])
 check(read[3]==0 && bytes(buffer,data.count)==data,"byte-exact stream "+name)
 try Data(bytes(buffer,data.count)).write(to:URL(fileURLWithPath:out+"/read-"+name+".bin"))
 let position=try call("Position "+name,9,[0,handle]);check(position[2]==data.count,"stream position")
 let eof=try call("EOF "+name,0x0a,[0,handle]);_ = eof;check(m.cpu.psr&0x20000000 != 0,"real EOF carry")
 if name=="Pattern" {
  let partial=try call("Cross-side random read",0x0c,[3,handle,buffer,4096,9500])
  check(partial[3]==0 && bytes(buffer,4096)==Array(data[9500..<13596]),"random read bytes")
 }
 try call("Close "+name,0x0d,[0,handle])
 write(buffer,Array(repeating:0xa5,count:data.count));try call("Load "+name,8,[255,filename,buffer,0])
 check(bytes(buffer,data.count)==data,"byte-exact OS_File load "+name)
 try Data(bytes(buffer,data.count)).write(to:URL(fileURLWithPath:out+"/load-"+name+".bin"))
}
string(filename,"ADFS::0.$.Absent");try call("Missing file",8,[255,filename,buffer,0],error:true)
try call("Free client workspace",0x1e,[7,0,client])
// Real OS_CLI run performs the load. The inherited application exit handler
// returns to Supervisor (it does not return through this injected SWI client).
// An execute breakpoint observes its first instruction before allowing it to run.
let programName:UInt32=0x8100;string(programName,"ADFS::0.$.Hello")
let entry=try d.addBreakpoint(.init(id:0,kind:.execute,start:0x10000))
words(0x8000,[0xe59f0004,0xef020005,0xeafffffe,programName]);m.cpu.pc=0x8000;d.resume()
_=m.run(untilTick:m.ticks+240_000_000,maxInstructions:20_000_000)
try dump("program-entry");check(d.isStopped && m.cpu.pc==0x10000,"loaded program entry")
let hello=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/Hello")))
check(bytes(0x10000,hello.count)==hello,"program loaded from disc at catalogue address")
check(m.cpu.mode == .user,"application USR26")
let programEntry:[String:Any]=["pc":m.cpu.pc,"psr":m.cpu.psr,"bytes":hello.count,"tick":m.ticks]
_=d.removeBreakpoint(entry.id);_=d.removeBreakpoint(returnBP.id)
let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[1]).deletingLastPathComponent().appendingPathComponent("symbols.json"))) as! [String:NSNumber]
let rdch=symbols["RdchLoop"]!.uint32Value
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:rdch));d.resume()
_=m.run(untilTick:m.ticks+24_000_000,maxInstructions:2_000_000)
try dump("program-return");check(d.isStopped && m.cpu.pc==rdch,"OS_Exit returns to Supervisor input")
check(m.screenText.contains{$0.contains("ARM2 FLOPPY PROGRAM EXECUTED")},"program output")
check(m.cpu.exceptionCounts[7]>0 && [1,3,4,5].allSatisfy{m.cpu.exceptionCounts[$0]==0},"real FIQ, no faults")
check(!disc.isModified && disc.overlay.isEmpty,"no disc writes")
try JSONSerialization.data(withJSONObject:["status":"PASS","rom_sha256":rom.sha256,"calls":calls,"fiqs":fiqs,"exceptions":m.cpu.exceptionCounts,"screen":m.screenText,"fdc_commands":m.fdc.commandCount,"write_protected":disc.writeProtected,"overlay_entries":disc.overlay.count,"program_entry":programEntry,"program_exit_pc":m.cpu.pc],options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/result.json"))
print("PASS: catalogue, streams, random read, load, genuine program execution")
