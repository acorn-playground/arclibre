// SPDX-License-Identifier: Apache-2.0
// Read-only public filing interfaces; faults reside on the supplied media.
import Foundation
import ArchimedesCore
func check(_ b:Bool,_ message:String) { if !b { fputs("FAIL: \(message)\n",stderr);exit(1) } }
func json(_ v:Any,_ path:String)throws {try JSONSerialization.data(withJSONObject:v,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:path))}
let a=CommandLine.arguments;check(a.count>=5,"FilingProbe ROM SNAPSHOT DISCS OUTPUT [CASE]")
let rom=try ROMImage.load(paths:[a[1]])
let snapshot=Array(try Data(contentsOf:URL(fileURLWithPath:a[2])))
let manifest=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]+"/manifest.json"))) as! [String:Any]
let images=manifest["images"] as! [[String:Any]]
let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[1]).deletingLastPathComponent().appendingPathComponent("symbols.json"))) as! [String:NSNumber]
final class Client {
 let m:Machine;let out:String;var media:[FloppyImage]=[];var calls:[[String:Any]]=[];var events:[[String:Any]]=[];var swis:[String]=[];var wp:UInt32=0
 var name:UInt32 {wp};var wildcard:UInt32 {wp+512};var buffer:UInt32 {wp+1024}
 init(_ caseName:String)throws {
  out=a[4]+"/"+caseName;try FileManager.default.createDirectory(atPath:out,withIntermediateDirectories:true)
  m=try Machine.restore(snapshot:snapshot,rom:rom);m.debugger.setTracing(4096);m.fdc.trace=RingBuffer<WD1772.TraceEvent>(capacity:32768)
  _=try m.debugger.addBreakpoint(.init(id:0,kind:.execute,start:4));_=try m.debugger.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20));_=try m.debugger.addBreakpoint(.init(id:0,kind:.execute,start:0x800c))
  if ProcessInfo.processInfo.environment["FILING_IDENTIFY_DEBUG"] != nil { _=try m.debugger.addBreakpoint(.init(id:0,kind:.execute,start:0x3854600)) }
  m.cpu.swiObserver={ [unowned self] pc,n in self.swis.append("\(self.m.ticks) \(String(pc,radix:16)) \(String(n,radix:16))") }
  wp=try call("Claim client",0x1e,[6,0,0,65536])[2]
 }
 func read(_ p:UInt32,_ n:Int)->[UInt8] {(0..<n).map{m.memc.debugRead(p+UInt32($0),space:.logical)!}}
 func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical)!}
 func write(_ p:UInt32,_ b:[UInt8]) {for (i,v) in b.enumerated(){check(m.memc.debugWrite(p+UInt32(i),v,space:.logical),"test RAM")}}
 func words(_ p:UInt32,_ w:[UInt32]) {write(p,w.flatMap{v in (0..<4).map{UInt8(truncatingIfNeeded:v>>($0*8))}})}
 func string(_ p:UInt32,_ s:String) {write(p,Array(s.utf8)+[0])}
 func text(_ p:UInt32)->String {String(bytes:read(p,1024).prefix{$0 != 0},encoding:.isoLatin1) ?? "invalid string"}
 func mount(_ file:String)throws {
  let image=try FloppyImage.open(path:a[3]+"/"+file,writeProtected:true);media.append(image);m.insertFloppy(image)
  events.append(["event":"insert","image":file,"sha256":image.sha256,"tick":m.ticks]);print("Mount \(file)");fflush(stdout)
 }
 func eject() {m.ejectFloppy();events.append(["event":"eject","tick":m.ticks])}
 func idle(_ seconds:Double) {words(0x8200,[0xeafffffe]);m.cpu.pc=0x8200;m.debugger.resume();_=m.run(untilTick:m.ticks+UInt64(seconds*24000000),maxInstructions:20_000_000);check(!m.debugger.isStopped,"idle fault")}
 func dump(_ tag:String)throws {
  try json(["calls":calls,"events":events,"pc":m.cpu.pc,"psr":m.cpu.psr,"screen":m.screenText,"exceptions":m.cpu.exceptionCounts],out+"/progress.json")
  try m.fdc.trace.elements.map{$0.description}.joined(separator:"\n").write(toFile:out+"/fdc.log",atomically:true,encoding:.utf8)
  try swis.joined(separator:"\n").write(toFile:out+"/swis.log",atomically:true,encoding:.utf8)
  let trace=(m.debugger.trace?.last(4096) ?? []).map{"\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)"}.joined(separator:"\n")
  try trace.write(toFile:out+"/"+tag+"-instructions.log",atomically:true,encoding:.utf8)
 }
 @discardableResult func call(_ label:String,_ swi:UInt32,_ args:[UInt32],error:Bool=false,cancelAfter:Double?=nil)throws->[UInt32] {
  let d=m.debugger;words(0x8000,[0xe59f8008,0xe89800ff,0xef020000|swi,0xeafffffe,0x8020]);words(0x8020,args+Array(repeating:0,count:8-args.count))
  let start=m.ticks;let deadline=start+60*24_000_000;var escapeDown=false,escapeUp=false
  m.cpu.pc=0x8000;d.resume()
  while !d.isStopped && m.ticks<deadline {
   _=m.run(untilTick:min(deadline,m.ticks+240000),maxInstructions:20000)
   if let seconds=cancelAfter {
    if !escapeDown && m.ticks>=start+UInt64(seconds*24000000) {m.keyDown(0);escapeDown=true;events.append(["event":"escape-down","tick":m.ticks])}
    if escapeDown && !escapeUp && m.ticks>=start+UInt64((seconds+0.1)*24000000){m.keyUp(0);escapeUp=true;events.append(["event":"escape-up","tick":m.ticks])}
   }
  }
  if escapeDown && !escapeUp {m.keyUp(0);events.append(["event":"escape-up","tick":m.ticks])}
  let r=(0..<8).map{m.cpu.r[$0]};let v=m.cpu.psr&0x10000000 != 0
  let message=v && r[0]<0x4000000 ? text(r[0]+4):""
  calls.append(["name":label,"swi":swi,"input":args,"output":r,"psr":m.cpu.psr,"pc":m.cpu.pc,"start_tick":start,"end_tick":m.ticks,"error":v,"error_number":v ? word(r[0]):0,"message":message,"cancelled":escapeDown])
  try dump("latest");print("\(label): \(v ? message:"OK") PC=\(String(m.cpu.pc,radix:16))");fflush(stdout)
  check(d.isStopped && m.cpu.pc==0x800c,"bounded SWI completion: "+label)
  check(v==error,"unexpected V for "+label)
  check([1,3,4,5].allSatisfy{m.cpu.exceptionCounts[$0]==0},"CPU exception")
  check(media.allSatisfy{$0.writeProtected && !$0.isModified && $0.overlay.isEmpty},"media remain read-only")
  return r
 }
 func cli(_ command:String)throws {string(name,command);try call(command,5,[name])}
 func load(_ path:String,_ label:String,error:Bool=false,cancelAfter:Double?=nil)throws->[UInt32] {string(name,path);return try call(label,8,[255,name,buffer,0],error:error,cancelAfter:cancelAfter)}
 func enumeration(_ path:String,_ pattern:String,_ wanted:[String])throws {
  string(name,path);string(wildcard,pattern);var offset:UInt32=0;var names:[String]=[];var rounds=0
  repeat {
   write(buffer,Array(repeating:0xa5,count:256))
   let r=try call("Enumerate \(path) \(pattern) \(offset)",0x0c,[9,name,buffer,1,offset,256,wildcard]);check(r[3]<=1,"one entry per page")
   if r[3]==1 {names.append(text(buffer))};check(r[4] != offset || r[4]==0xffffffff,"directory progression");offset=r[4];rounds+=1;check(rounds<100,"directory bound")
  }while offset != 0xffffffff
  check(names==wanted,"directory names: \(names) expected \(wanted)");events.append(["event":"enumeration","path":path,"pattern":pattern,"names":names])
 }
 func application()throws {
  string(0x8100,"ADFS::0.$.CheckFile");words(0x8000,[0xe59f0004,0xef020005,0xeafffffe,0x8100])
  let d=m.debugger;let entry=try d.addBreakpoint(.init(id:0,kind:.execute,start:0x10000));m.cpu.pc=0x8000;d.resume()
  _=m.run(untilTick:m.ticks+240_000_000,maxInstructions:20_000_000)
  try dump("application-entry");check(d.isStopped && m.cpu.pc==0x10000 && m.cpu.psr==0,"actual USR26 app entry")
  let expected=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]).deletingLastPathComponent().appendingPathComponent("CheckFile.bin")))
  check(read(0x10000,expected.count)==expected,"actual loaded client bytes");events.append(["event":"application-entry","pc":m.cpu.pc,"psr":m.cpu.psr,"tick":m.ticks])
  _=d.removeBreakpoint(entry.id);let end=try d.addBreakpoint(.init(id:0,kind:.execute,start:symbols["RdchLoop"]!.uint32Value));let checksum=try d.addBreakpoint(.init(id:0,kind:.execute,start:0x100b4));d.resume()
  _=m.run(untilTick:m.ticks+240_000_000,maxInstructions:20_000_000)
  check(d.isStopped && m.cpu.pc==0x100b4 && text(m.cpu.r[0]).hasPrefix("ARM2 FILING CLIENT PASS"),"guest checksum and filing result");events.append(["event":"application-result","message":text(m.cpu.r[0]),"checksum":m.cpu.r[6],"psr":m.cpu.psr]);try dump("application-checksum");_=d.removeBreakpoint(checksum.id);d.resume()
  _=m.run(untilTick:m.ticks+240_000_000,maxInstructions:20_000_000)
  try dump("application-return");check(d.isStopped && m.cpu.pc==symbols["RdchLoop"]!.uint32Value,"app exit to Supervisor")
  let expectedData=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/EA-Docs_Fragment")));check(read(0x20000,expectedData.count)==expectedData,"guest-loaded data bytes")
  try Data(read(0x20000,expectedData.count)).write(to:URL(fileURLWithPath:out+"/application-data.bin"))
  events.append(["event":"application-return","pc":m.cpu.pc,"psr":m.cpu.psr,"tick":m.ticks]);_=d.removeBreakpoint(end.id)
 }
 func finish(runApplication:Bool=false)throws {
  try call("Free client",0x1e,[7,0,wp]);if runApplication {try application()};check([1,3,4,5].allSatisfy{m.cpu.exceptionCounts[$0]==0},"final CPU exceptions");check(media.allSatisfy{$0.writeProtected && !$0.isModified && $0.overlay.isEmpty},"final read-only media");try dump("final")
  for (tag,b) in m.stateSections(){try Data(b).write(to:URL(fileURLWithPath:out+"/final-\(tag).bin"))}
  try json(["status":events.contains{$0["event"] as? String == "known-defect"} ? "KNOWN_BASELINE_DEFECT":"PASS","rom_sha256":rom.sha256,"calls":calls,"events":events,"screen":m.screenText,"exceptions":m.cpu.exceptionCounts,"fdc_commands":m.fdc.commandCount,"media":media.map{["sha256":$0.sha256,"protected":$0.writeProtected,"overlay":$0.overlay.count]}],out+"/result.json")
 }
}
func valid(_ image:String)throws {
 let c=try Client(image);try c.mount(image+".adf")
 // Independent host-side decoder also checks that generated directories and fragment addresses resolve.
 let imported=try ADFSDiscReader.read(path:a[3]+"/"+image+".adf")
 check(imported.items.count==7 && imported.directories.count==2,"host reader fixture shape")
 try c.enumeration("ADFS::0.$","*",["CheckFile","Docs","Hello","RootText","Zero"])
 try c.enumeration("ADFS::0.$.Docs","*",["Deep","Fragment","Sibling"])
 try c.enumeration("ADFS::0.$.Docs","F*",["Fragment"])
 try c.enumeration("ADFS::0.$.Docs.Deep","*",["Leaf"])
 let spec=images.first{$0["name"] as! String==image}!;let files=spec["files"] as! [[String:Any]]
 for file in files {
  let path=file["path"] as! String;let data=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/"+image+"-"+path.replacingOccurrences(of:".",with:"_"))))
  c.string(c.name,"adfs::0.$."+path.lowercased());let info=try c.call("Info "+path,8,[5,c.name])
  check(info[0]==1 && info[2]==(file["load"] as! NSNumber).uint32Value && info[3]==(file["execute"] as! NSNumber).uint32Value && info[4]==data.count && info[5]==17,"case-folded file metadata")
  let handle=try c.call("Open "+path,0x0d,[0x40,c.name])[0];check(handle != 0,"file handle")
  let length=try c.call("Length "+path,9,[2,handle]);check(length[2]==data.count,"file extent")
  var got:[UInt8]=[];let requests:[Int]=data.isEmpty ? [0,17]:[1,1023,1024,17,4096,8000,32768]
  for request in requests {
   c.write(c.buffer-4,Array(repeating:0xa5,count:request+8));let r=try c.call("Read \(path) \(request)",0x0c,[4,handle,c.buffer,UInt32(request)])
   let take=min(request,data.count-got.count);check(r[3]==request-take,"GBPB residual");check((c.m.cpu.psr&0x20000000 != 0)==(take<request),"GBPB EOF carry")
   check(c.read(c.buffer-4,4)==[0xa5,0xa5,0xa5,0xa5] && c.read(c.buffer+UInt32(take),request-take+4)==Array(repeating:0xa5,count:request-take+4),"no write outside requested/transferred data")
   got+=c.read(c.buffer,take)
  }
  check(got==data,"sequential bytes "+path);try Data(got).write(to:URL(fileURLWithPath:c.out+"/read-"+path+".bin"))
  let eof=try c.call("BGet EOF "+path,0x0a,[0,handle]);_=eof;check(c.m.cpu.psr&0x20000000 != 0,"BGet carry at EOF")
  if path=="Docs.Fragment" {
   for offset in [8190,20478,38888] {
    let r=try c.call("Random fragment boundary \(offset)",0x0c,[3,handle,c.buffer,32,UInt32(offset)]);let n=min(32,data.count-offset)
    check(r[3]==32-n && c.read(c.buffer,n)==Array(data[offset..<offset+n]),"fragment boundary bytes")
   }
  }
  try c.call("Close "+path,0x0d,[0,handle]);try c.call("Closed handle "+path,9,[0,handle],error:true)
  try c.load("ADFS::0.$."+path,"Whole load "+path);check(c.read(c.buffer,data.count)==data,"whole load "+path)
  try Data(c.read(c.buffer,data.count)).write(to:URL(fileURLWithPath:c.out+"/load-"+path+".bin"))
 }
 try c.cli("Dir ADFS::0.$.Docs")
 try c.load("@.Deep.Leaf","relative child");let expectedLeaf=Array("A leaf in the second nested directory.\r\n".utf8);check(c.read(c.buffer,expectedLeaf.count)==expectedLeaf,"relative leaf")
 c.string(c.name,"^.RootText");let parent=try c.call("Parent directory file",8,[5,c.name]);check(parent[0]==1,"parent lookup")
 try c.load("ADFS::0.$.Absent","Missing file",error:true)
 try c.finish(runApplication:true)
}
let selected=a.count>5 ? a[5]:"all"
for name in ["DA","EA"] where selected=="all" || selected==name {try valid(name)}
let faults=["DA-bad-directory.adf","EA-bad-directory.adf","EA-bad-maps.adf","EA-first-map-bad.adf","DA-missing.jfd","DA-id-crc.jfd","DA-data-crc.jfd","EA-missing.jfd","EA-id-crc.jfd","EA-data-crc.jfd"]
for file in faults {
 let scenario=String(file.split(separator:".")[0]);if selected != "all" && selected != scenario {continue}
 let c=try Client(scenario);try c.mount(file);let recoverable=file=="EA-first-map-bad.adf"
 try c.load("ADFS::0.$.Docs.Fragment","Read fault fixture",error:!recoverable)
 if recoverable {let expected=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/EA-Docs_Fragment")));check(c.read(c.buffer,expected.count)==expected,"secondary map bytes")}
 try c.mount(String(file.prefix(2))+".adf");try c.cli("ADFS:Dismount :0")
 try c.load("ADFS::0.$.Docs.Fragment","Read after recovery")
 let expected=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/EA-Docs_Fragment")));check(c.read(c.buffer,expected.count)==expected,"recovery exact data")
 try Data(c.read(c.buffer,expected.count)).write(to:URL(fileURLWithPath:c.out+"/recovered.bin"));try c.finish()
}
if selected=="all" || selected=="media-change" || selected=="media-change-baseline" {
 let c=try Client(selected=="media-change-baseline" ? selected:"media-change");try c.mount("DA.adf");try c.load("ADFS::0.$.RootText","Read disc A")
 let first=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/DA-RootText")));check(c.read(c.buffer,first.count)==first,"disc A bytes")
 c.eject();c.idle(1.0);try c.mount("DB.adf");c.idle(1.0)
 try c.load("ADFS::0.$.RootText","Read disc B")
 let second=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/DB-RootText")));let observed=c.read(c.buffer,second.count);try Data(observed).write(to:URL(fileURLWithPath:c.out+"/disc-B-read.bin"))
 if selected=="media-change-baseline" {
  check(observed==first && observed != second,"reproduced baseline stale cache defect")
  c.events.append(["event":"known-defect","description":"Baseline returns disc A cached data after insertion of disc B"])
  try c.cli("ADFS:Dismount :0");try c.load("ADFS::0.$.RootText","Explicit dismount recovery")
  check(c.read(c.buffer,second.count)==second,"baseline workaround recovery")
 } else {check(observed==second,"changed media must not return stale data")}
 try c.finish()
}
if selected=="all" || selected=="empty-drive" {
 let c=try Client("empty-drive");try c.load("ADFS::0.$.RootText","Empty drive",error:true,cancelAfter:5)
 try c.call("Acknowledge escape",6,[126,0,0]);try c.mount("DA.adf");try c.load("ADFS::0.$.RootText","Read after insertion")
 let expected=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/DA-RootText")));check(c.read(c.buffer,expected.count)==expected,"empty drive recovery")
 try c.finish()
}
check(["all","DA","EA","media-change","media-change-baseline","empty-drive"].contains(selected) || faults.map{String($0.split(separator:".")[0])}.contains(selected),"known scenario");print("Completed selected filing scenarios")
