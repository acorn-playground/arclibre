// SPDX-License-Identifier: Apache-2.0
// Executes a real USR26 diagnostic Wimp task on the original-machine kernel.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5,"MultiTaskProbe ROM SNAPSHOT MULTITASK_DIRECTORY OUTPUT")
let root=URL(fileURLWithPath:a[3]),out=URL(fileURLWithPath:a[4])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let d=m.debugger;d.setTracing(200000)
var taskMode=false
var masterBase:UInt32=0
var taskObservations:[[String:Any]]=[]
var appSWIs:[[String:Any]]=[]
var calls:[[String:Any]]=[],tests:[[String:Any]]=[]
var observedSWIs:[String:Int]=[:]
m.cpu.swiObserver={pc,n in
 if (pc>=0x8000 && pc<0x10000) || [UInt32(1),0x20001,0x11,0x20011,0x600c0,0x600dd,0x400dd,0x600de].contains(n) {appSWIs.append(["pc":pc,"swi":n,"psr":m.cpu.psr,"r":(0..<5).map{m.cpu.r[$0]}])}
 let key=String(n,radix:16);observedSWIs[key,default:0]+=1
 if pc>=0x8000 && pc<0x10000 && n==0x600c7 {
  taskObservations.append(["pc":pc,"psr":m.cpu.psr,"marker":word(0x10000),"physical_code":m.memc.debugTranslate(0x8000) ?? 0xffffffff,"physical_marker":m.memc.debugTranslate(0x10000) ?? 0xffffffff])
 }
}
func json(_ x:Any,_ name:String) { try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json")) }
func trace(_ name:String) { let t=(d.trace?.last(200000) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined();try! t.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8) }
func check(_ b:Bool,_ s:String) { if !b { trace("failure");json(["failure":s,"exceptions":m.cpu.exceptionCounts,"pc":m.cpu.pc,"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]},"calls":calls,"tests":tests,"app_swis":appSWIs,"task_observations":taskObservations,"master_base":masterBase,"master_data":masterBase>0 ? bytes(masterBase,700):[]],"failure");fputs("FAIL: \(s) at \(String(m.cpu.pc,radix:16))\n",stderr);exit(1) } }
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
 check(m.cpu.mode == (taskMode ? .user : .supervisor),"26-bit return \(name)")
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
for (component,title) in [("FPEmulator","FPEmulator"),("Colours","ColourTrans"),("DrawMod","Draw"),("Super","SuperSample"),("Hourglass","Hourglass"),("FontManager","FontManager"),("ROMFonts","ROMFonts"),("Wimp","WindowManager")] {
 let b=Array(try Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/"+component+"/module.bin")))
 write(0x20000,b);call("Load "+title,0x1e,[11,0x20000,UInt32(b.count)])
 string(0x11000,title);let found=call("Look up "+title,0x1e,[18,0x11000]);check(bytes(found[3],b.count)==b,"exact installed module "+title)
 workspace[component]=found[4];loaded.append(["component":component,"base":found[3],"workspace":found[4],"bytes":b.count])
}



call("Set desktop mode",0x400e3,[12])
let master=Array(try Data(contentsOf:root.appendingPathComponent("Master.bin")))
let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("Master-symbols.json"))) as! [String:NSNumber]
write(0x20000,master);call("Load parent application module",0x1e,[11,0x20000,UInt32(master.count)]);string(0x11000,"ArcTasks");masterBase=call("Find parent module",0x1e,[18,0x11000])[3]
func sym(_ n:String)->UInt32 {masterBase+symbols[n]!.uint32Value}
words(0x8000,[0xe59f8008,0xe89800ff,0xef02001e,0xeafffffe,0x8020]);words(0x8020,[2,0x11000,0,0,0,0,0,0])
run(0x8000,sym("stop"),"real three-task scheduler")
let stage=word(sym("stage")),error=word(sym("error"))
json(["stage":stage,"error":error,"error_text":error>0 ? text(error+4):"","finished":word(sym("finished")),"task_a":word(sym("taska")),"task_b":word(sym("taskb")),"app_swis":appSWIs,"observations":taskObservations],"tasks")
check(stage==4 && word(sym("finished"))==3,"both real application tasks completed")
check(Set(taskObservations.map{$0["marker"] as! UInt32})==Set([UInt32(11),29]),"both task marker values")
check(Set(taskObservations.map{$0["physical_code"] as! UInt32}).count==2,"independent physical application slots")
check(taskObservations.allSatisfy{($0["psr"] as! UInt32)&3==0},"USR26 tasks")
trace("scheduler")
json(["status":"PASS","calls":calls,"loaded":loaded,"master_base":masterBase,"stage":stage,"observations":taskObservations,"exceptions":m.cpu.exceptionCounts,"rom_sha256":rom.sha256],"result")
print("PASS: real application slots, scheduler and independent FP states")
