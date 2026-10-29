// SPDX-License-Identifier: Apache-2.0
// Executes real font-provider SWIs on the original-machine kernel.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5,"FontProbe ROM SNAPSHOT FONT_DIRECTORY OUTPUT")
let root=URL(fileURLWithPath:a[3]),out=URL(fileURLWithPath:a[4])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let d=m.debugger;d.setTracing(20000)
var calls:[[String:Any]]=[],tests:[[String:Any]]=[]
var observedSWIs:[String:Int]=[:]
m.cpu.swiObserver={_,n in let key=String(n,radix:16);observedSWIs[key,default:0]+=1}
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
 _=m.run(untilTick:m.ticks+240_000_000,maxInstructions:20_000_000)
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
for (component,title) in [("Colours","ColourTrans"),("DrawMod","Draw"),("Super","SuperSample"),("Hourglass","Hourglass"),("FontManager","FontManager"),("ROMFonts","ROMFonts")] {
 let b=Array(try Data(contentsOf:root.appendingPathComponent("modules/"+component+"/module.bin")))
 write(0x20000,b);call("Load "+title,0x1e,[11,0x20000,UInt32(b.count)])
 string(0x11000,title);let found=call("Look up "+title,0x1e,[18,0x11000]);check(bytes(found[3],b.count)==b,"exact installed module "+title)
 workspace[component]=found[4];loaded.append(["component":component,"base":found[3],"workspace":found[4],"bytes":b.count])
}
func vdu(_ b:[UInt8]) {write(0x12000,b);call("VDU",0x46,[0x12000,UInt32(b.count)])}
vdu([22,12,12,23,1,0,0,0,0,0,0,0,0]) // standard original-board 640x256, 16 colours; clear text.
var fonts:[[String:Any]]=[]
let families=["Corpus.Medium","Corpus.Bold","Corpus.Medium.Oblique","Corpus.Bold.Oblique","Homerton.Medium","Homerton.Bold","Homerton.Medium.Oblique","Homerton.Bold.Oblique","Trinity.Medium","Trinity.Bold","Trinity.Medium.Italic","Trinity.Bold.Italic"]
let screen=word(0x10c0),lineLength=word(0x1088)
for (index,name) in families.enumerated() {
 string(0x13000,name)
 let found=call("Find "+name,0x40081,[0,0x13000,192,192,0,0]);let handle=found[0]
 check(handle>0 && handle<256,"valid font handle")
 let info=call("Bounds "+name,0x40084,[handle])
 call("Select "+name,0x4008a,[handle])
 string(0x13200,"Open Archimedes 3.11")
 let measured=call("Measure "+name,0x40085,[0,0x13200,0x7fffffff,0x7fffffff,0xffffffff,255])
 check(measured[2]>0 && measured[3]==0 && measured[5]==20,"string metrics")
 call("Font colours "+name,0x40092,[handle,0,7,0])
 vdu([16]);let blank=bytes(screen,Int(lineLength)*256)
 call("Paint "+name,0x40086,[handle,0x13200,0x110,100,400])
 let painted=bytes(screen,Int(lineLength)*256);let changed=zip(blank,painted).filter{$0 != $1}.count
 check(changed>20 && changed<5000,"bounded font bitmap")
 try Data(painted).write(to:out.appendingPathComponent("font-\(index).bin"))
 vdu([16]);call("Repaint "+name,0x40086,[handle,0x13200,0x110,100,400]);check(bytes(screen,painted.count)==painted,"cached repaint identical")
 let area=call("Font cache area "+name,0x5c,[4])
 var mappings:[UInt32]=[]
 for offset in stride(from:UInt32(0),to:area[1],by:32768) {let physical=m.memc.debugTranslate(area[0]+offset);check(physical != nil && physical!<4194304,"font cache MEMC mapping");mappings.append(physical!)}
 if index==4 {
  for i in 0..<16 {let gray=UInt8(i*17);vdu([19,UInt8(i),16,gray,gray,gray])}
  call("Antialias font colours",0x4074f,[handle,0,0xffffff00,14])
  vdu([16]);call("Paint antialias",0x40086,[handle,0x13200,0x110,100,400])
  let aa=bytes(screen,Int(lineLength)*256);let levels=Set(aa.flatMap{[$0&15,$0>>4]})
  check(levels.count>2,"antialiased output uses intermediate shades")
  try Data(aa).write(to:out.appendingPathComponent("antialias.bin"))
  vdu([22,12,23,1,0,0,0,0,0,0,0,0]) // restore the real original mode palette for remaining faces
 }
 fonts.append(["name":name,"handle":handle,"bounds":Array(info[1...4]),"width":measured[2],"characters":measured[5],"changed_bytes":changed,"cache_base":area[0],"cache_bytes":area[1],"cache_physical_pages":mappings])
 call("Lose "+name,0x40082,[handle])
}
for title in ["ROMFonts","FontManager","Hourglass","SuperSample","Draw","ColourTrans"] {string(0x11000,title);call("Unload "+title,0x1e,[4,0x11000])}
call("Deregister messages",0x41b41,[resourceBase]);call("Free messages",0x1e,[7,0,resourceBase])
check([1,3,4,5,7].allSatisfy{m.cpu.exceptionCounts[$0]==0},"no processor faults")
trace("font-stack")
json(["status":"PASS","calls":calls,"loaded":loaded,"fonts":fonts,"observed_swis":observedSWIs,"screen":screen,"line_length":lineLength,"rom_sha256":rom.sha256,"exceptions":m.cpu.exceptionCounts],"result")
print("PASS: real FontManager/ROMFonts, 12 faces measured and painted")
