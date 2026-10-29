// SPDX-License-Identifier: Apache-2.0
// Isolated module-loading diagnostic used before joining the desktop ROM.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5,"DesktopProbe ROM SNAPSHOT STARTUP_DIRECTORY OUTPUT")
let root=URL(fileURLWithPath:a[3]),out=URL(fileURLWithPath:a[4])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let d=m.debugger;d.setTracing(200000)
var taskMode=false
var appSWIs:[[String:Any]]=[]
var calls:[[String:Any]]=[],tests:[[String:Any]]=[]
var observedSWIs:[String:Int]=[:]
var initialisations:[[String:Any]]=[],polls:[String:Int]=[:],services:[UInt32:Int]=[:]
m.cpu.swiObserver={pc,n in
 let swi=n & ~UInt32(0x20000)
 if swi==0x400c0 {initialisations.append(["pc":pc,"name":text(m.cpu.r[2]),"version":m.cpu.r[0],"psr":m.cpu.psr])}
 if swi==0x400df { appSWIs.append(["pc":pc,"error_number":word(m.cpu.r[0]),"error":text(m.cpu.r[0]+4)]) }
 if swi==0x30 {services[m.cpu.r[1],default:0]+=1}
 if swi==0x400c7 || swi==0x400e1 {
  let component=loaded.first{pc>=($0["base"] as! UInt32) && pc<($0["base"] as! UInt32)+UInt32($0["bytes"] as! Int)}?["component"] as? String ?? "unknown"
  polls[component,default:0]+=1
 }
}
func json(_ x:Any,_ name:String) { try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json")) }
func trace(_ name:String) { let t=(d.trace?.last(200000) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined();try! t.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8) }
func check(_ b:Bool,_ s:String) { if !b { trace("failure");json(["failure":s,"exceptions":m.cpu.exceptionCounts,"pc":m.cpu.pc,"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]},"calls":calls,"tests":tests,"app_swis":appSWIs],"failure");fputs("FAIL: \(s) at \(String(m.cpu.pc,radix:16))\n",stderr);exit(1) } }
func word(_ p:UInt32)->UInt32 { m.memc.debugReadWord(p,space:.logical)! }
func bytes(_ p:UInt32,_ n:Int)->[UInt8] {(0..<n).map{m.memc.debugRead(p+UInt32($0),space:.logical)!}}
func write(_ p:UInt32,_ b:[UInt8]) { for (i,v) in b.enumerated(){check(m.memc.debugWrite(p+UInt32(i),v,space:.logical),"write fixture")} }
func words(_ p:UInt32,_ w:[UInt32]) { write(p,w.flatMap{v in (0..<4).map{UInt8(truncatingIfNeeded:v>>($0*8))}}) }
func string(_ p:UInt32,_ s:String) { write(p,Array(s.utf8)+[0]) }
func text(_ p:UInt32)->String { String(bytes:bytes(p,256).prefix{$0 >= 32},encoding:.isoLatin1)! }
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
for (component,title) in [("FPEmulator","FPEmulator"),("Colours","ColourTrans"),("DrawMod","Draw"),("Super","SuperSample"),("Hourglass","Hourglass"),("FontManager","FontManager"),("ROMFonts","ROMFonts"),("SprExtend","SpriteExtend"),("Wimp","WindowManager"),("Desktop","Desktop"),("Filer","Filer"),("Switcher","TaskManager"),("Pinboard","Pinboard")] {
 let path=["Desktop","Filer","Switcher","Pinboard","SprExtend"].contains(component) ? root.appendingPathComponent("modules/"+component+"/module.bin"):root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/"+component+"/module.bin")
 let b=Array(try Data(contentsOf:path))
 write(0x20000,b);call("Load "+title,0x1e,[11,0x20000,UInt32(b.count)])
 string(0x11000,title);let found=call("Look up "+title,0x1e,[18,0x11000]);check(bytes(found[3],b.count)==b,"exact installed module "+title)
 workspace[component]=found[4];loaded.append(["component":component,"base":found[3],"workspace":found[4],"bytes":b.count])
}

// Exercise the original boot-error Cancel dialogue if present in this snapshot.
call("Set initial desktop mode",0x400e3,[12])
string(0x11000,"Desktop")
words(0x8000,[0xe59f0004,0xef020005,0xeafffffe,0x11000])
m.cpu.pc=0x8000;d.resume()
_=m.run(untilTick:m.ticks+240_000_000,maxInstructions:20_000_000)
if appSWIs.contains(where: { ($0["error"] as? String)?.contains("Machine startup has not completed") == true }) {
 trace("boot-warning")
 try Data(m.snapshot(createdBy:"ArcLibre original boot warning")).write(to:out.appendingPathComponent("boot-warning.macarch-state"))
 m.mouseMove(dx:(640-Int(word(1424+28)))/2,dy:(344-Int(word(1424+32)))/2)
 _=m.run(untilTick:m.ticks+4_800_000,maxInstructions:800_000)
 m.keyDown(0x70);_=m.run(untilTick:m.ticks+2_400_000,maxInstructions:400_000)
 m.keyUp(0x70)
}
_=m.run(untilTick:m.ticks+480_000_000,maxInstructions:40_000_000)
trace("desktop")
m.mouseMove(dx:(1230-Int(word(1424+28)))/2,dy:(60-Int(word(1424+32)))/2)
_=m.run(untilTick:m.ticks+4_800_000,maxInstructions:800_000)
m.keyDown(0x70);_=m.run(untilTick:m.ticks+2_400_000,maxInstructions:400_000);m.keyUp(0x70)
_=m.run(untilTick:m.ticks+240_000_000,maxInstructions:20_000_000)
trace("task-manager")
let syms=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]]
let taskCount=word(workspace["Wimp"]!+syms["taskcount"]!["value"]!.uint32Value)
let screen=word(0x10c0),line=word(0x1088)
try Data(bytes(screen,Int(line)*256)).write(to:out.appendingPathComponent("screen.bin"))
try Data(m.snapshot(createdBy:"ArcLibre desktop startup")).write(to:out.appendingPathComponent("desktop.macarch-state"))
json(["status":"CAPTURED","errors":appSWIs,"initialisations":initialisations,"polls":polls,"services":services.map{["service":$0.key,"count":$0.value]},"task_count":taskCount,"pc":m.cpu.pc,"psr":m.cpu.psr,"exceptions":m.cpu.exceptionCounts,"loaded":loaded,"palette":m.vidc.palette,"line_length":line,"screen":screen,"text":m.screenText],"result")
print("Desktop tasks \(taskCount), polls \(polls), PC \(String(m.cpu.pc,radix:16))")
