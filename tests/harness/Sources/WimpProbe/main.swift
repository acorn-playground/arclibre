// SPDX-License-Identifier: Apache-2.0
// Executes a real USR26 diagnostic Wimp task on the original-machine kernel.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5,"WimpProbe ROM SNAPSHOT WIMP_DIRECTORY OUTPUT")
let root=URL(fileURLWithPath:a[3]),out=URL(fileURLWithPath:a[4])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let d=m.debugger;d.setTracing(20000)
var taskMode=false
var calls:[[String:Any]]=[],tests:[[String:Any]]=[]
var observedSWIs:[String:Int]=[:]
var colourCalls:[[String:Any]]=[]
m.cpu.swiObserver={_,n in
 let key=String(n,radix:16);observedSWIs[key,default:0]+=1
 if n==0x60743 || n==0x20061 {
  var row:[String:Any]=["swi":n,"r":(0..<5).map{m.cpu.r[$0]}]
  if n==0x20061 && m.cpu.r[0]&32 != 0 {row["pattern"]=(0..<8).map{word(m.cpu.r[1]+UInt32($0*4))}}
  colourCalls.append(row)
 }
}
func json(_ x:Any,_ name:String) { try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json")) }
func trace(_ name:String) { let t=(d.trace?.last(20000) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined();try! t.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8) }
func check(_ b:Bool,_ s:String) { if !b { trace("failure");json(["failure":s,"exceptions":m.cpu.exceptionCounts,"pc":m.cpu.pc,"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]},"calls":calls,"tests":tests],"failure");fputs("FAIL: \(s) at \(String(m.cpu.pc,radix:16))\n",stderr);exit(1) } }
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
 let b=Array(try Data(contentsOf:root.appendingPathComponent("modules/"+component+"/module.bin")))
 write(0x20000,b);call("Load "+title,0x1e,[11,0x20000,UInt32(b.count)])
 string(0x11000,title);let found=call("Look up "+title,0x1e,[18,0x11000]);check(bytes(found[3],b.count)==b,"exact installed module "+title)
 workspace[component]=found[4];loaded.append(["component":component,"base":found[3],"workspace":found[4],"bytes":b.count])
}


string(0x13000,"Open Archimedes test");words(0x13100,[0x4f415243,0])
call("Set desktop mode",0x400e3,[12])
let oldCAO=call("Set diagnostic application environment",0x40,[15,0x8000])
// Enter USR26 with real guest instructions, retaining IRQ/FIQ state. The
// fixture runs in its normal application space with a dedicated user stack.
words(0x8100,[0xe1a0900f,0xe3c99003,0xe13ff009,0xe1a00000,0xe59fd004,0xe59ff004,0xe1a00000,0x1f000,0x8128,0xe1a00000,0xeafffffe])
taskMode=true;run(0x8100,0x8128,"Enter USR26")
let initial=call("Initialise diagnostic task",0x400c0,[310,0x4b534154,0x13000,0x13100])
let definition: [UInt32]=[100,200,700,800,0,0,0xffffffff,3,0x01070207,0x000c0103,0,0xfffffc00,1280,0,0x3d,0x4000,1,0,0,0,0,0]
words(0x14000,definition);string(0x14048,"ARM2 test")
let window=call("Create diagnostic window",0x400c1,[0,0x14000])[0]
words(0x14500,[window,100,200,700,800,0,0,0xffffffff])
call("Open diagnostic window",0x400c5,[0,0x14500])
words(0x14600,[window]);call("Read window state",0x400cb,[0,0x14600])
json((0..<9).map{word(0x14600+UInt32($0*4))},"window-state")

let client=Array(try Data(contentsOf:root.appendingPathComponent("client.bin")))
let syms=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("client-symbols.json"))) as! [String:NSNumber]
func sym(_ n:String)->UInt32 {0x9000+syms[n]!.uint32Value}
write(0x9000,client)
func fp(_ name:String)->[UInt8] {
 words(0x8200,[0xe59fa000,0xe59ff000,0x16000,sym(name)])
 run(0x8200,sym("stop"),"FPA "+name);return bytes(0x16000,100)
}
let fpBefore=fp("seed")
var events:[[String:Any]]=[]
func poll(_ stage:String)->UInt32 {
 let before=m.cpu.exceptionCounts[1]
 let event=call("Poll "+stage,0x400c7,[0x01000000,0x14800]);let reason=event[0]
 events.append(["stage":stage,"reason":reason,"block":(0..<16).map{word(0x14800+UInt32($0*4))},"undefined_traps":m.cpu.exceptionCounts[1]-before])
 if reason==1 {
  var more=call("Begin redraw",0x400c8,[0,0x14800])[0];var rectangles=0
  while more != 0 {
   rectangles+=1;check(rectangles<100,"finite redraw rectangle list")
   // Convert work coordinates using the real redraw block; Wimp supplies
   // a screen-coordinate graphics clip, not an application origin.
   let ox=word(0x14804)&-word(0x14814),oy=word(0x14810)&-word(0x14818)
   let tx=ox&+32,ty=oy&-64
   write(0x15000,[5,25,4,UInt8(truncatingIfNeeded:tx),UInt8(truncatingIfNeeded:tx>>8),UInt8(truncatingIfNeeded:ty),UInt8(truncatingIfNeeded:ty>>8)])
   call("Position redraw text",0x46,[0x15000,7])
   string(0x15000,"Original ARM2 window");call("Redraw text",0x2,[0x15000])
   more=call("Next rectangle",0x400ca,[0,0x14800])[0]
  }
 }
 if reason==2 {call("Accept open request",0x400c5,[0,0x14800])}
 if reason==3 {call("Accept close request",0x400c6,[0,0x14800])}
 return reason
}
func drain(_ stage:String) {for _ in 0..<24 {if poll(stage)==0{return}};check(false,"poll queue drained "+stage)}
drain("initial")
check(fp("capture")==fpBefore,"Wimp preserves all eight FPA registers and FPSR")
let screen=word(0x10c0),length=word(0x1088)
var framePalettes:[String:[UInt32]]=[:]
func frame(_ name:String) {framePalettes[name]=m.vidc.palette;try! Data(bytes(screen,Int(length)*256)).write(to:out.appendingPathComponent(name+".bin"))}
frame("window");trace("initial-window")
let wsymbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]]
func ws(_ n:String)->UInt32 {wsymbols[n]!["value"]!.uint32Value}
let wwork=workspace["Wimp"]!,taskOffset=word(wwork+ws("taskhandle")),taskBlock=word(wwork+taskOffset),fpBlock=word(taskBlock+ws("task_fpblock"))
let messageList=word(taskBlock+ws("task_messages")),messageBytes=word(taskBlock+ws("task_messagessize"))
json(["task_block":taskBlock,"message_pointer":messageList,"message_bytes":messageBytes,"original_list":bytes(0x13100,8),"copied_list":messageList>0 && messageList<0x4000000 && messageBytes<1024 ? bytes(messageList,Int(messageBytes)):[]],"message-contract")
check(messageBytes==4 && word(messageList)==0x4f415243,"caller message-interest list preserved")
check(fpBlock>0 && bytes(fpBlock,100)==fpBefore,"real Wimp FP save block matches all registers and status")
check(bytes(wwork+ws("medusakernel"),1)==[0],"original MEMC kernel selected")

// Guest IRQs process real IOC keyboard/mouse traffic while the client is idle.
func idle(_ ticks:UInt64) {
 words(0x800c,[0xeafffffe]);m.cpu.pc=0x800c;d.resume()
 _=m.run(untilTick:m.ticks+ticks,maxInstructions:2_000_000)
 let bp=try! d.addBreakpoint(.init(id:0,kind:.execute,start:0x800c));d.resume()
 _=m.run(untilTick:m.ticks+240000,maxInstructions:100000);_=d.removeBreakpoint(bp.id)
 check(d.isStopped && m.cpu.pc==0x800c && m.cpu.mode == .user,"idle returns outside IRQ")
}
call("Keyboard focus",0x400d2,[window,0xffffffff,32,0xffffffc0,0x02000020,0])
drain("focus")
m.keyDown(0x3c);idle(2400000);m.keyUp(0x3c);idle(2400000);drain("keyboard")
check(events.contains{($0["reason"] as! UInt32)==8 && (($0["block"] as! [UInt32])[6])==97},"real keyboard a event");trace("keyboard")
let oldMouse=call("Read initial mouse",0x1c,[])
m.mouseMove(dx:-120,dy:-50);idle(4800000)
let newMouse=call("Read moved mouse",0x1c,[])
check(newMouse[0] != oldMouse[0] || newMouse[1] != oldMouse[1],"real mouse movement")
drain("mouse movement")
m.keyDown(0x70);idle(2400000);drain("mouse button");m.keyUp(0x70);idle(2400000);drain("mouse release")
check(events.contains{($0["reason"] as! UInt32)==6 && (($0["block"] as! [UInt32])[3])==window},"real work-area mouse click");trace("mouse")
// Exercise actual asynchronous task messaging without a second synthetic SWI handler.
words(0x15200,[24,0,0,0,0x4f415243,0x11223344])
call("Send diagnostic message",0x400e7,[17,0x15200,initial[1]])
drain("message")
check(events.contains{($0["reason"] as! UInt32)==17 && (($0["block"] as! [UInt32])[4])==0x4f415243 && (($0["block"] as! [UInt32])[5])==0x11223344},"real task message delivery")
// Exercise the public move/close APIs independently of pointer drag policy.
words(0x14500,[window,300,300,900,900,0,0,0xffffffff]);call("Move window",0x400c5,[0,0x14500]);drain("moved")
words(0x14600,[window]);call("Read moved state",0x400cb,[0,0x14600]);let moved=(0..<9).map{word(0x14600+UInt32($0*4))}
check(Array(moved[1...4])==[300,300,900,900],"window move coordinates")
frame("moved");trace("moved")
let closeMouse=call("Read mouse before close",0x1c,[])
m.mouseMove(dx:(360-Int(closeMouse[0]))/2,dy:(920-Int(closeMouse[1]))/2);idle(4800000);drain("close hover")
m.keyDown(0x70);idle(2400000);drain("close click");m.keyUp(0x70);idle(2400000);drain("closed")
check(events.contains{($0["reason"] as! UInt32)==3},"real close-button request")
words(0x14600,[window]);call("Read closed state",0x400cb,[0,0x14600]);let closed=(0..<9).map{word(0x14600+UInt32($0*4))}
check(closed[8]&0x10000==0,"closed state")
frame("closed");trace("closed")
words(0x14500,[window]);call("Delete window",0x400c3,[0,0x14500])
call("Close diagnostic task",0x400dd,[initial[1],0x4b534154])
call("Restore application environment",0x40,[15,oldCAO[1]])
taskMode=false;call("Return to Supervisor",0x16,[])
for title in ["WindowManager","ROMFonts","FontManager","Hourglass","SuperSample","Draw","ColourTrans","FPEmulator"] {string(0x11000,title);call("Unload "+title,0x1e,[4,0x11000])}
call("Deregister resources",0x41b41,[resourceBase]);call("Free resources",0x1e,[7,0,resourceBase])
check([3,4,5,7].allSatisfy{m.cpu.exceptionCounts[$0]==0},"no processor faults")
json(["status":"PASS","calls":calls,"loaded":loaded,"task":initial,"window":window,"moved":moved,"closed":closed,"events":events,"fpa_save_block":fpBlock,"task_block":taskBlock,"original_memc_path":true,"fpa_preserved":true,"fpa_before":fpBefore,"mouse_before":oldMouse,"mouse_after":newMouse,"colour_calls":colourCalls,"frame_palettes":framePalettes,"final_palette":m.vidc.palette,"observed_swis":observedSWIs,"rom_sha256":rom.sha256,"exceptions":m.cpu.exceptionCounts],"result")
trace("wimp")
print("PASS: real USR26 Wimp window, events, FPA state and finalisation")
