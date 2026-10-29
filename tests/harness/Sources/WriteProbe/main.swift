// SPDX-License-Identifier: Apache-2.0
// Real guest filing writes to copy-on-write, original generated D/E media.
import Foundation
import ArchimedesCore
func check(_ b:Bool,_ message:String) {if !b {fputs("FAIL: \(message)\n",stderr);exit(1)}}
func json(_ v:Any,_ path:String)throws {try JSONSerialization.data(withJSONObject:v,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:path))}
let a=CommandLine.arguments;check(a.count>=5,"WriteProbe ROM SNAPSHOT DISCS OUTPUT [CASE]")
let rom=try ROMImage.load(paths:[a[1]]), snapshot=Array(try Data(contentsOf:URL(fileURLWithPath:a[2])))
func pattern(_ n:Int,_ seed:Int)->[UInt8] {(0..<n).map{UInt8(truncatingIfNeeded:$0*53+($0>>8)*17+seed)}}
final class Client {
 let m:Machine;let out:String;let disc:FloppyImage;let original:[UInt8];var wp:UInt32=0
 var calls:[[String:Any]]=[],fiqs:[[String:Any]]=[],checkpoints:[[String:Any]]=[]
 var name:UInt32 {wp};var other:UInt32 {wp+512};var buffer:UInt32 {wp+1024}
 init(_ caseName:String,_ image:String,protected:Bool=false)throws {
  out=a[4]+"/"+caseName;try FileManager.default.createDirectory(atPath:out,withIntermediateDirectories:true)
  original=Array(try Data(contentsOf:URL(fileURLWithPath:image)));disc=try FloppyImage.open(path:image,writeProtected:protected)
  m=try Machine.restore(snapshot:snapshot,rom:rom);m.insertFloppy(disc);m.debugger.setTracing(4096);m.fdc.trace=RingBuffer<WD1772.TraceEvent>(capacity:65536)
  for p:UInt32 in [4,12,16,20,0x800c] {_=try m.debugger.addBreakpoint(.init(id:0,kind:.execute,start:p))}
  wp=try call("Claim client",0x1e,[6,0,0,131072])[2]
 }
 func read(_ p:UInt32,_ n:Int)->[UInt8] {(0..<n).map{m.memc.debugRead(p+UInt32($0),space:.logical)!}}
 func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical)!}
 func write(_ p:UInt32,_ b:[UInt8]) {for(i,v) in b.enumerated(){check(m.memc.debugWrite(p+UInt32(i),v,space:.logical),"client RAM")}}
 func words(_ p:UInt32,_ w:[UInt32]) {write(p,w.flatMap{v in (0..<4).map{UInt8(truncatingIfNeeded:v>>($0*8))}})}
 func string(_ p:UInt32,_ s:String) {write(p,Array(s.utf8)+[0])}
 func text(_ p:UInt32)->String {String(bytes:read(p,512).prefix{$0 != 0},encoding:.isoLatin1) ?? "invalid"}
 func path(_ s:String) {string(name,"ADFS::0.$."+s)}
 func dump()throws {
  try json(["calls":calls,"fiqs":fiqs,"checkpoints":checkpoints,"exceptions":m.cpu.exceptionCounts],out+"/progress.json")
  try m.fdc.trace.elements.map{$0.description}.joined(separator:"\n").write(toFile:out+"/fdc.log",atomically:true,encoding:.utf8)
  try (m.debugger.trace?.last(4096) ?? []).map{"\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)"}.joined(separator:"\n").write(toFile:out+"/instructions.log",atomically:true,encoding:.utf8)
 }
 @discardableResult func call(_ label:String,_ swi:UInt32,_ args:[UInt32],error:Bool=false)throws->[UInt32] {
  let d=m.debugger;words(0x8000,[0xe59f8008,0xe89800ff,0xef020000|swi,0xeafffffe,0x8020]);words(0x8020,args+Array(repeating:0,count:8-args.count))
  // Sample the first actual write-sector FIQ in this client. Reads encountered
  // first are simply resumed; no driver registers or code are altered.
  var trap=fiqs.isEmpty ? try d.addBreakpoint(.init(id:0,kind:.execute,start:0x1c)).id:nil
  let start=m.ticks,deadline=start+60*24_000_000;m.cpu.pc=0x8000;d.resume()
  while m.ticks<deadline {
   _=m.run(untilTick:min(deadline,m.ticks+240000),maxInstructions:20000)
   if d.isStopped {
    if m.cpu.pc==0x1c,let id=trap {
     if m.fdc.command == .writeSector {
      check(m.cpu.psr&0x0c000003==0x0c000001,"FIQ26 masks")
      let capture=read(0x1c,512);try Data(capture).write(to:URL(fileURLWithPath:out+"/write-fiq.bin"))
      var event:[String:Any]=["call":label,"tick":m.ticks,"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]}]
      _=d.removeBreakpoint(id);trap=nil;d.resume();var trace:[[String:Any]]=[]
      while m.cpu.mode == .fiq && trace.count<4096 && !d.isStopped {
       trace.append(["pc":m.cpu.pc,"word":word(m.cpu.pc),"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]}]);_=m.run(untilTick:m.ticks+24000,maxInstructions:1)
      }
      check(m.cpu.mode != .fiq,"write FIQ returns");event["instructions"]=trace;event["return_pc"]=m.cpu.pc;event["return_psr"]=m.cpu.psr;fiqs.append(event)
     }else {d.resume()}
     continue
    }
    break
   }
  }
  if let id=trap {_=d.removeBreakpoint(id)}
  let r=(0..<8).map{m.cpu.r[$0]},v=m.cpu.psr&0x10000000 != 0
  calls.append(["name":label,"swi":swi,"input":args,"output":r,"pc":m.cpu.pc,"psr":m.cpu.psr,"start_tick":start,"end_tick":m.ticks,"error":v,"error_number":v ? word(r[0]):0,"message":v ? text(r[0]+4):""])
  try dump();print("\(label): \(v ? text(r[0]+4):"OK")");fflush(stdout)
  check(d.isStopped && m.cpu.pc==0x800c,"bounded SWI completion "+label);check(v==error,"unexpected V "+label)
  check([1,3,4,5].allSatisfy{m.cpu.exceptionCounts[$0]==0},"CPU exceptions")
  if disc.writeProtected {check(!disc.isModified && disc.mergedImage()==original,"protected image unchanged")}
  return r
 }
 func save(_ p:String,_ data:[UInt8],error:Bool=false)throws {
  path(p);write(buffer,data);try call("Save "+p,8,[0,name,0x12345678,0x23456780,buffer,buffer+UInt32(data.count)],error:error)
  check(read(buffer,data.count)==data,"save does not change source buffer")
 }
 func load(_ p:String,_ expected:[UInt8])throws {
  path(p);let meta=try call("Info "+p,8,[5,name]);check(meta[0]==1 && meta[4]==expected.count,"file extent "+p)
  write(buffer-4,Array(repeating:0xa5,count:expected.count+8));try call("Load "+p,8,[255,name,buffer,0])
  check(read(buffer,expected.count)==expected,"exact loaded bytes "+p)
  check(read(buffer-4,4)==[0xa5,0xa5,0xa5,0xa5] && read(buffer+UInt32(expected.count),4)==[0xa5,0xa5,0xa5,0xa5],"load bounds")
 }
 func checkpoint(_ name:String)throws {
  string(self.name,"ADFS:Dismount :0");try call("Dismount "+name,5,[self.name])
  let data=disc.mergedImage();try Data(data).write(to:URL(fileURLWithPath:out+"/"+name+".adf"))
  checkpoints.append(["name":name,"overlay_sectors":disc.overlay.keys.sorted(),"changed_bytes":zip(original,data).filter{$0 != $1}.count]);try dump()
 }
 func finish()throws {
  try call("Free client",0x1e,[7,0,wp]);try dump()
  try json(["status":"PASS","rom_sha256":rom.sha256,"base_sha256":disc.sha256,"write_protected":disc.writeProtected,"calls":calls,"fiqs":fiqs,"checkpoints":checkpoints,"exceptions":m.cpu.exceptionCounts,"fdc_commands":m.fdc.commandCount],out+"/result.json")
 }
}
let selected=a.count>5 ? a[5]:"all"
for fmt in ["DA","EA"] where selected=="all" || selected==fmt {
 let c=try Client(fmt,a[3]+"/"+fmt+".adf")
 let first=pattern(32791,0x31),replacement=pattern(7191,0x59),stream=pattern(16393,0x77),patch=pattern(37,0xa6)
 try c.save("Written",first);try c.load("Written",first);try c.checkpoint("01-save")
 try c.save("Written",replacement);try c.load("Written",replacement);try c.checkpoint("02-overwrite")
 c.path("Stream");let h=try c.call("Open output",0x0d,[0x80,c.name])[0];check(h != 0,"output handle")
 c.write(c.buffer,stream);let wr=try c.call("GBPB sequential write",0x0c,[2,h,c.buffer,UInt32(stream.count)])
 check(wr[3]==0 && wr[2]==c.buffer+UInt32(stream.count),"GBPB complete transfer")
 let pos=try c.call("Read pointer",9,[0,h]);check(pos[2]==stream.count,"write advances pointer")
 try c.call("BPut appended byte",0x0b,[0x5a,h]);try c.call("Flush output",9,[255,h]);try c.call("Close output",0x0d,[0,h])
 var updated=stream+[0x5a];try c.load("Stream",updated);try c.checkpoint("03-appended")
 c.path("Stream");let u=try c.call("Open update",0x0d,[0xc0,c.name])[0];check(u != 0,"update handle")
 c.write(c.buffer,patch);let random=try c.call("GBPB positioned write",0x0c,[1,u,c.buffer,UInt32(patch.count),1019]);check(random[3]==0,"positioned complete transfer")
 updated.replaceSubrange(1019..<1019+patch.count,with:patch)
 try c.call("Truncate stream",9,[3,u,10013]);updated=Array(updated.prefix(10013))
 let extent=try c.call("Read truncated extent",9,[2,u]);check(extent[2]==10013,"truncation extent")
 try c.call("Close update",0x0d,[0,u]);try c.load("Stream",updated);try c.checkpoint("03-stream")
 // Cross both real E-format fragment boundaries (D uses its contiguous layout).
 c.path("Docs.Fragment");let denied=try c.call("Open read-only fragment for update",0x0d,[0xc0,c.name])[0]
 c.write(c.buffer,patch);try c.call("Read-only file rejects update",0x0c,[1,denied,c.buffer,UInt32(patch.count),8190],error:true)
 try c.call("Close read-only fragment",0x0d,[0,denied])
 c.path("Docs.Fragment");try c.call("Grant fragment write access",8,[4,c.name,0,0,0,0x33])
 c.path("Docs.Fragment");let f=try c.call("Open fragment update",0x0d,[0xc0,c.name])[0]
 var fragmented=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/"+fmt+"-Docs_Fragment")))
 for offset in [8190,20478] {
  c.write(c.buffer,patch);let r=try c.call("Write fragment boundary \(offset)",0x0c,[1,f,c.buffer,UInt32(patch.count),UInt32(offset)]);check(r[3]==0,"fragment complete write");fragmented.replaceSubrange(offset..<offset+patch.count,with:patch)
 }
 try c.call("Flush fragment",9,[255,f]);try c.call("Close fragment",0x0d,[0,f]);try c.load("Docs.Fragment",fragmented);try c.checkpoint("04-fragment")
 c.path("Written");c.string(c.other,"ADFS::0.$.Renamed");try c.call("Rename file",0x29,[25,c.name,c.other])
 c.path("NewDir");try c.call("Create directory",8,[8,c.name,0,0,0,0]);try c.save("NewDir.Child",patch);try c.load("NewDir.Child",patch)
 try c.checkpoint("05-namespace")
 c.path("Stream");try c.call("Delete stream",8,[6,c.name]);c.path("NewDir.Child");try c.call("Delete child",8,[6,c.name]);c.path("NewDir");try c.call("Delete empty directory",8,[6,c.name])
 try c.checkpoint("06-deleted")
 c.path("TooBig");try c.call("Disc full allocation",8,[7,c.name,0x12345678,0x23456780,0,900000],error:true);try c.checkpoint("07-full")
 try c.save("Recovery",patch);try c.load("Recovery",patch);try c.checkpoint("08-final");try c.finish()
 // New machine from the independently cold-booted pre-filing state: no cache,
 // open file, snapshot disc overlay, or directory state from the writer survives.
 let r=try Client(fmt+"-reopen",c.out+"/08-final.adf",protected:true)
 try r.load("Renamed",replacement);try r.load("Docs.Fragment",fragmented);try r.load("Recovery",patch)
 for name in ["Written","Stream","NewDir","TooBig"] {r.path(name);let info=try r.call("Absent "+name,8,[5,r.name]);check(info[0]==0,"deleted/failed file absent")}
 try r.finish()
}
for fmt in ["DA","EA"] where selected=="all" || selected==fmt+"-protected" {
 let c=try Client(fmt+"-protected",a[3]+"/"+fmt+".adf",protected:true)
 try c.save("Denied",pattern(1027,0x91),error:true)
 let original=Array(try Data(contentsOf:URL(fileURLWithPath:a[3]+"/"+fmt+"-RootText")));try c.load("RootText",original)
 try c.checkpoint("protected");try c.finish()
}
check(["all","DA","EA","DA-protected","EA-protected"].contains(selected),"known write scenario")
print("PASS: selected controlled filing writes")
