// SPDX-License-Identifier: Apache-2.0
// Executes real rendering-provider SWIs on the original-machine kernel.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5,"RenderProbe ROM SNAPSHOT RENDER_DIRECTORY OUTPUT")
let root=URL(fileURLWithPath:a[3]),out=URL(fileURLWithPath:a[4])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let d=m.debugger;d.setTracing(20000)
var calls:[[String:Any]]=[],tests:[[String:Any]]=[]
func json(_ x:Any,_ name:String) { try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json")) }
func trace(_ name:String) { let t=(d.trace?.last(20000) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined();try! t.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8) }
func check(_ b:Bool,_ s:String) { if !b { trace("failure");json(["failure":s,"pc":m.cpu.pc,"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]},"calls":calls,"tests":tests],"failure");fputs("FAIL: \(s) at \(String(m.cpu.pc,radix:16))\n",stderr);exit(1) } }
func word(_ p:UInt32)->UInt32 { m.memc.debugReadWord(p,space:.logical)! }
func bytes(_ p:UInt32,_ n:Int)->[UInt8] {(0..<n).map{m.memc.debugRead(p+UInt32($0),space:.logical)!}}
func write(_ p:UInt32,_ b:[UInt8]) { for (i,v) in b.enumerated(){check(m.memc.debugWrite(p+UInt32(i),v,space:.logical),"write fixture")} }
func words(_ p:UInt32,_ w:[UInt32]) { write(p,w.flatMap{v in (0..<4).map{UInt8(truncatingIfNeeded:v>>($0*8))}}) }
func string(_ p:UInt32,_ s:String) { write(p,Array(s.utf8)+[0]) }
func text(_ p:UInt32)->String { String(bytes:bytes(p,256).prefix{$0 != 0},encoding:.isoLatin1)! }
func run(_ start:UInt32,_ stop:UInt32,_ name:String) {
 let bp=try! d.addBreakpoint(.init(id:0,kind:.execute,start:stop));m.cpu.pc=start;d.resume()
 _=m.run(untilTick:m.ticks+24_000_000,maxInstructions:2_000_000)
 _=d.removeBreakpoint(bp.id)
 check(d.isStopped && m.cpu.pc==stop,"timeout/fault \(name)")
 check(m.cpu.mode == .supervisor,"SVC26 return \(name)")
 check([3,4,5,7].allSatisfy{m.cpu.exceptionCounts[$0]==0},"unexpected processor fault \(name)")
}
@discardableResult func call(_ name:String,_ swi:UInt32,_ args:[UInt32],error:Bool=false)->[UInt32] {
 words(0x8000,[0xe59f8008,0xe89800ff,0xef020000|swi,0xeafffffe,0x8020]);words(0x8020,args+Array(repeating:0,count:8-args.count));run(0x8000,0x800c,name)
 let r=(0..<8).map{m.cpu.r[$0]};let v=m.cpu.psr&0x10000000 != 0
 calls.append(["name":name,"swi":swi,"input":args,"output":r,"psr":m.cpu.psr,"error":v ? text(r[0]+4):""])
 check(v==error,"SWI \(name): \(v ? text(r[0]+4):"")");return r
}
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
let resources=Array(try Data(contentsOf:root.appendingPathComponent("resources.bin")))
let resourceBase=call("Claim resources",0x1e,[6,0,0,UInt32(resources.count)])[2];write(resourceBase,resources);call("Register provider messages",0x41b40,[resourceBase])
var loaded:[[String:Any]]=[]
var workspace:[String:UInt32]=[:]
for (component,title) in [("Colours","ColourTrans"),("DrawMod","Draw"),("Super","SuperSample"),("Hourglass","Hourglass")] {
 let b=Array(try Data(contentsOf:root.appendingPathComponent("modules/"+component+"/module.bin")))
 write(0x20000,b);call("Load "+title,0x1e,[11,0x20000,UInt32(b.count)])
 string(0x11000,title);let found=call("Look up "+title,0x1e,[18,0x11000]);check(bytes(found[3],b.count)==b,"exact installed module "+title)
 workspace[component]=found[4];loaded.append(["component":component,"base":found[3],"workspace":found[4],"bytes":b.count])
}
func vdu(_ b:[UInt8]) {write(0x12000,b);call("VDU",0x46,[0x12000,UInt32(b.count)])}
vdu([22,12,12]) // standard original-board 640x256, 16 colours; clear text.
var conversions:[[String:Any]]=[]
for rgb:[UInt32] in [[65536,0,0],[0,65536,0],[0,0,65536],[32768,16384,8192]] {
 let hsv=call("RGB to HSV",0x40758,rgb)
 let back=call("HSV to RGB",0x40759,Array(hsv.prefix(3)))
 check(zip(rgb,back).allSatisfy{abs(Int64($0)-Int64($1))<=4},"colour conversion roundtrip")
 conversions.append(["rgb":rgb,"hsv":Array(hsv.prefix(3)),"roundtrip":Array(back.prefix(3))])
}
var colours:[[String:Any]]=[]
for colour:UInt32 in [0,0xffffff00,0xff000000,0x0000ff00,0x00ff0000] {
 let first=call("Return colour",0x40744,[colour])[0]
 let cached=call("Cached colour",0x40744,[colour])[0]
 check(first==cached && first<16,"palette/cache result")
 call("Invalidate colour cache",0x40750,[])
 let fresh=call("Fresh colour",0x40744,[colour])[0];check(first==fresh,"cache invalidation preserves conversion")
 colours.append(["physical":colour,"logical":first])
}
// Exercise Draw's real fixed-point matrix processing, in-place output and errors.
let path:UInt32=0x14000,matrix:UInt32=0x14400
let original:[UInt32]=[2,1024,2048,8,3072,4096,0]
words(path,original);words(matrix,[65536,0,0,65536,256,512])
call("Transform path",0x4070a,[path,0,matrix,0])
let transformed=(0..<original.count).map{word(path+UInt32($0*4))}
check(transformed==[2,1280,2560,8,3328,4608,0],"Draw matrix result")
words(path,[99,0]);let err=call("Invalid path",0x40702,[path,0,0,0],error:true);check(text(err[0]+4)=="Bad path element","Draw translated error")
// Real filled rectangle, in Draw units (256 per OS unit). Keep its edges away
// from text/cursor and verify framebuffer changes, then independently inspect.
vdu([16]);let screen=word(0x10c0),lineLength=word(0x1088)
let before=bytes(screen,Int(lineLength)*256)
call("White foreground",0x40743,[0xffffff00,0,0,0,0])
words(path,[2,100*256,100*256,8,300*256,100*256,8,300*256,300*256,8,100*256,300*256,5,0])
call("Fill rectangle",0x40702,[path,0,0,0])
let after=bytes(screen,Int(lineLength)*256)
let changed=zip(before,after).filter{$0 != $1}.count
check(changed>100 && changed<Int(lineLength)*128,"bounded Draw framebuffer output")
try Data(before).write(to:out.appendingPathComponent("draw-before.bin"));try Data(after).write(to:out.appendingPathComponent("draw-after.bin"))
// Both original supersampling kernels: compare complete output words to an
// independently evaluated 2D convolution in the Python verifier.
var samples:[[String:Any]]=[]
for algorithm in 0...1 {
 for pattern in 0...3 {
  let input:[UInt32]=(0..<11).map { row in
   switch pattern {case 0:return 0;case 1:return 0x7fffffff;case 2:return row%2==0 ? 0x55555555:0x2aaaaaaa;default:return UInt32(truncatingIfNeeded:(row+1)*0x1050713)&0x7fffffff}
  }
  words(0x15000,input);words(0x16000,Array(repeating:0xcccccccc,count:8))
  call("Super sample \(algorithm)/\(pattern)",0x40d80+UInt32(algorithm),[0,0x15000,4,11,0x16000])
  let output=(0..<8).map{word(0x16000+UInt32($0*4))}
  check(output[2...].allSatisfy{$0==0xcccccccc},"Super output bounds")
  samples.append(["algorithm":algorithm,"pattern":pattern,"input":input,"output":Array(output.prefix(2))])
 }
}
// Let the actual IOC ticker invoke Hourglass, then verify its real workspace.
let hg=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("modules/Hourglass/symbols.json"))) as! [String:NSNumber]
let hp=workspace["Hourglass"]!
func h(_ n:String)->UInt32 {hp+hg[n]!.uint32Value}
func idleUntil(_ name:String,_ ready:()->Bool) {
 words(0x8000,[0xeafffffe]);m.cpu.pc=0x8000;d.resume();let deadline=m.ticks+24_000_000
 while !(ready() && m.cpu.pc==0x8000 && m.cpu.mode == .supervisor) && m.ticks<deadline && !d.isStopped {_=m.run(untilTick:min(deadline,m.ticks+24000),maxInstructions:1000)}
 json(["name":name,"pc":m.cpu.pc,"psr":m.cpu.psr,"depth":word(h("HourglassDepth")),"timer":word(h("HourglassTimer")),"bytes":bytes(h("OldPercentage"),20),"tick":m.ticks],"hourglass-"+name)
 check(!d.isStopped && ready() && m.cpu.pc==0x8000 && m.cpu.mode == .supervisor,"hourglass ticker "+name)
}
call("Start hourglass",0x406c3,[1])
idleUntil("initial shape",{bytes(h("PointerDirty"),1)==[0]})
// The real first setup clears its percentage state. Set it after display starts.
call("Hourglass percentage",0x406c4,[42])
idleUntil("percentage update",{bytes(h("OldPercentage"),1)==[42]})
check(word(h("HourglassDepth"))==1,"hourglass depth")
let hgData=bytes(h("HourglassData"),180);check(hgData.contains{$0 != 0},"hourglass shape generated")
try Data(hgData).write(to:out.appendingPathComponent("hourglass-shape.bin"))
call("Stop hourglass",0x406c1,[]);check(word(h("HourglassDepth"))==0,"hourglass released")
for title in ["Hourglass","SuperSample","Draw","ColourTrans"] {string(0x11000,title);call("Unload "+title,0x1e,[4,0x11000])}
call("Deregister provider messages",0x41b41,[resourceBase]);call("Free provider messages",0x1e,[7,0,resourceBase])
check([1,3,4,5,7].allSatisfy{m.cpu.exceptionCounts[$0]==0},"no processor faults")
trace("rendering")
json(["status":"PASS","calls":calls,"loaded":loaded,"conversions":conversions,"colours":colours,"transformed":transformed,"samples":samples,"screen":screen,"line_length":lineLength,"draw_changed_bytes":changed,"hourglass_shape":hgData,"rom_sha256":rom.sha256,"exceptions":m.cpu.exceptionCounts],"result")
print("PASS: real ColourTrans, Draw, SuperSample and Hourglass")
