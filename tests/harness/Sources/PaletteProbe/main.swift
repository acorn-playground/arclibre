// SPDX-License-Identifier: Apache-2.0
// Power-on desktop experiment: no guest code injection or module loading.
import Foundation
import ArchimedesCore
import ProbeSupport
let a=CommandLine.arguments
precondition(a.count==4,"DesktopROMProbe ROM BUILD_DIRECTORY OUTPUT")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[3])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
let modules=layout["modules"] as! [[String:Any]]
let desktopTasks:UInt32 = 4+UInt32(["ResFiler","ArcPalette","Free"].filter{c in modules.contains{$0["component"] as? String==c}}.count)
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[];config.monitor="standard";config.powerOnKeys=[0x34]
// A fitted floppy drive, no hard disc, and no automatic disc boot. These are
// ordinary persistent machine settings, not writes into guest OS workspace.
// The 3.60 ADFS byte includes IDE counts in bits 6-7, even on MEMC machines.
config.cmosSettings=[]
let m=try Machine(configuration:config,rom:rom)
m.fdc.trace=RingBuffer<WD1772.TraceEvent>(capacity:10000)
let discPath=root.deletingLastPathComponent().appendingPathComponent("desktop-baseline/artifacts/discs/DA.adf").path
// A writable copy, so the real Save box can write a palette file to it.
let discCopy=out.appendingPathComponent("disc.adf")
try? FileManager.default.removeItem(at:discCopy);try FileManager.default.copyItem(at:URL(fileURLWithPath:discPath),to:discCopy)
let disc=try FloppyImage.open(path:discCopy.path,writeProtected:false)
m.insertFloppy(disc,drive:0)
m.powerOn();let d=m.debugger;d.setTracing(100000)
var generated:[String:[String:UInt32]]=[:],generatedStart:UInt32=0,spriteVectorCalls=0
let spriteSymbols = modules.contains(where:{$0["component"] as? String=="SprExtend"}) ? try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/SprExtend/symbols.json"))) as? [String:NSNumber] : nil
let spriteEntry:UInt32 = spriteSymbols == nil ? 0 : (modules.first{$0["component"] as? String=="SprExtend"}!["base"] as! NSNumber).uint32Value + spriteSymbols!["My_SpriteOp"]!.uint32Value
if spriteEntry>0 { _=try d.addBreakpoint(.init(id:0,kind:.execute,start:spriteEntry)) }
let desktopSymbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Desktop/symbols.json"))) as! [String:NSNumber]
let welcomeBoundary=(modules.first{$0["component"] as? String=="Desktop"}!["base"] as! NSNumber).uint32Value+desktopSymbols["NoWelcome"]!.uint32Value
let welcomeBreakpoint=try d.addBreakpoint(.init(id:0,kind:.execute,start:welcomeBoundary))
var undefined:[[String:Any]]=[]
var allowExpectedError=false
var expectedErrors:[[String:Any]]=[]
var paletteCloses=0, paletteRedraws=0
var menus:[[String:UInt32]]=[]
var modeCalls:[UInt32]=[]
var initialisations:[[String:Any]]=[],errors:[[String:Any]]=[],polls:[String:Int]=[:],services:[UInt32:Int]=[:],opens:[String:Int]=[:],stages:[[String:Any]]=[]
var filingWindows:[[String:Any]]=[],filingIcons:[[String:Any]]=[]
var shellCommands:[String]=[],shellMessages:[String]=[],shellScreens:[String:[String]]=[:]
func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical) ?? 0xffffffff}
func text(_ p:UInt32)->String {var b:[UInt8]=[];for i in 0..<256 {guard let v=m.memc.debugRead(p+UInt32(i),space:.logical),v>=32 else{break};b.append(v)};return String(bytes:b,encoding:.isoLatin1) ?? "?"}
func component(_ pc:UInt32)->String {modules.first {let b=($0["base"] as! NSNumber).uint32Value;return pc>=b && pc<b+($0["length"] as! NSNumber).uint32Value}?["component"] as? String ?? "Kernel"}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
func trace(_ name:String){let s=(d.trace?.last(100000) ?? []).map{"\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n"}.joined();try! s.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8)}
func check(_ b:Bool,_ s:String){if !b{trace("failure");json(["failure":s,"pc":m.cpu.pc,"exceptions":m.cpu.exceptionCounts,"initialisations":initialisations,"errors":errors,"polls":polls,"text":m.screenText],"failure");fputs("FAIL: \(s)\n",stderr);exit(1)}}
m.cpu.swiObserver={pc,n in
 let swi=n & ~UInt32(0x20000),c=component(pc)
 if c=="ShellCLI" && swi==5 {shellCommands.append(text(m.cpu.r[0]));trace("shell-command-\(shellCommands.count)")}
 if c=="ShellCLI" && swi==2 {shellMessages.append(text(m.cpu.r[0]))}
 if swi==0x400c0{initialisations.append(["component":c,"name":text(m.cpu.r[2]),"psr":m.cpu.psr,"version":m.cpu.r[0]])}
 if swi==0x400df{errors.append(["component":c,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}
 if swi==0x400c7 || swi==0x400e1{polls[c,default:0]+=1}
 if swi==0x400c5{opens[c,default:0]+=1}
 if c=="ArcPalette" && swi==0x400c6{paletteCloses+=1}
 if c=="ArcPalette" && swi==0x400c8{paletteRedraws+=1}
 if c=="ArcPalette" && swi==0x400d4{menus.append(["pointer":m.cpu.r[1],"x":m.cpu.r[2],"y":m.cpu.r[3]]);json(menus,"menus")}
 if c=="ArcPalette" && swi==0x400e3{modeCalls.append(m.cpu.r[0]);json(modeCalls,"mode-calls")}
 if swi==0x400c1 && c=="Filer" {let p=m.cpu.r[1];filingWindows.append(["title":text(word(p+72)),"definition":(0..<22).map{word(p+UInt32($0*4))}]);json(filingWindows,"filing-windows")}
 if swi==0x400e2 && c=="Filer" {let p=m.cpu.r[1];filingIcons.append(["text":text(word(p+20)),"definition":(0..<8).map{word(p+UInt32($0*4))}]);json(filingIcons,"filing-icons")}
 if swi==0x30{services[m.cpu.r[1],default:0]+=1;if m.cpu.r[1]==0x4a{trace("startup-complete")}}
}
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
func run(_ ticks:UInt64){let end=m.ticks+ticks;d.resume();while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2400000),maxInstructions:300000)
 if d.isStopped {
  if m.cpu.pc==welcomeBoundary {
   capture("welcome");_=d.removeBreakpoint(welcomeBreakpoint.id)
  } else if m.cpu.pc==spriteEntry {
   spriteVectorCalls+=1
   let start=m.cpu.r[12]+spriteSymbols!["codebuffer"]!.uint32Value
   if start != generatedStart {
    generatedStart=start
    _=try! d.addBreakpoint(.init(id:0,kind:.execute,start:start,end:start+511))
   }
  } else if generatedStart>0 && m.cpu.pc>=generatedStart && m.cpu.pc<generatedStart+512 {
   let pc=m.cpu.pc,w=word(pc);generated["\(pc)-\(w)"]=["pc":pc,"word":w]
  } else {
  check(m.cpu.pc==4,"processor fault")
  let pc=(m.cpu.r[14] & 0x03fffffc)-4
  undefined.append(["pc":pc,"word":word(pc),"component":component(pc),"psr":m.cpu.psr])
  }
  d.resume()
 }
 };check(errors.isEmpty || allowExpectedError,"desktop error: \(errors)")}
func moduleWorkspace(_ c:String)->UInt32 {var node=word(2000);let base=(modules.first{$0["component"] as! String==c}!["base"] as! NSNumber).uint32Value
 for _ in 0..<50 {if node==0{break};if word(node+4)==base{return word(word(node+12)+4)};node=word(node)};return 0xffffffff}
func taskCount()->UInt32 {let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]];return word(moduleWorkspace("Wimp")+syms["taskcount"]!["value"]!.uint32Value)}
func reportedTotal()->UInt32 {let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Switcher/symbols.json"))) as! [String:NSNumber]
 var node=word(moduleWorkspace("Switcher")+syms["wlink"]!.uint32Value)
 for _ in 0..<100 {if node==0 || node==0xffffffff{break};if m.memc.debugRead(node+syms["icb_icon1"]!.uint32Value,space:.logical)==UInt8(syms["ic_totalname"]!.uint32Value){return word(node+syms["icb_memsize"]!.uint32Value)};node=word(node+syms["icb_link"]!.uint32Value)};return 0xffffffff}
func capture(_ name:String){trace(name);let f=m.currentFrame;check(writePNG(f,to:out.appendingPathComponent(name+".png")),"PNG");let screen=word(0x10c0),line=word(0x1088);let b=(0..<Int(line)*256).map{m.memc.debugRead(screen+UInt32($0),space:.logical)!};try! Data(b).write(to:out.appendingPathComponent(name+"-screen.bin"));stages.append(["name":name,"ticks":m.ticks,"task_count":taskCount(),"polls":polls,"opens":opens,"palette":m.vidc.palette,"line_length":line,"pc":m.cpu.pc,"psr":m.cpu.psr]);json(stages,"stages")}

func click(_ x:Int,_ y:Int){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000);m.keyDown(0x70);run(2_400_000);m.keyUp(0x70);run(4_800_000)}
check(m.cpu.pc==0 && m.cpu.psr==0x0c000003,"real reset vector")
run(24_000_000*35);capture("desktop")
check(taskCount()==desktopTasks,"Palette plus five original desktop tasks")
check(m.cmos[0xcc]==0x83,"bitmap system font and disabled tiling from ROM defaults")
let wimpSyms=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]]
check(word(moduleWorkspace("Wimp")+wimpSyms["systemfont"]!["value"]!.uint32Value)==0,"Wimp actually selected system bitmap font")
func wimp(_ name:String)->UInt32 {word(moduleWorkspace("Wimp")+wimpSyms[name]!["value"]!.uint32Value)}
func editor(_ name:String)->UInt32 {word(word(moduleWorkspace("ArcPalette")+8)-1+wimpSyms[name]!["value"]!.uint32Value)}
func isOpen()->Bool {editor("w_flags") & 0x10000 != 0}
func move(_ x:Int,_ y:Int){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000)}
func clickWork(_ x:Int,_ y:Int){click(Int(editor("w_wax0"))+x-Int(Int32(bitPattern:editor("w_scx"))),Int(editor("w_way1"))+y-Int(Int32(bitPattern:editor("w_scy"))))}
func menu(){move(Int(wimp("scrx1"))-132,60);m.keyDown(0x71);run(2_400_000);m.keyUp(0x71);run(48_000_000)}
func menuItem(_ n:Int){let m=menus.last{$0["pointer"] != 0xffffffff}!;click(Int(m["x"]!)+72,Int(m["y"]!)-22-n*44);run(2_400_000)}
let original=m.vidc.palette, border=m.vidc.border, pointer=m.vidc.cursorPalette
// RISC OS 3.11 shows the desktop background grey (Wimp colour 4) in the border.
check(border & 0xfff == 0x777 && original.contains{$0 & 0xfff == border & 0xfff},"default border matches desktop background")
click(1148,60);run(24_000_000);capture("palette-open")
check(isOpen() && paletteRedraws>0,"real redraw request paints open editor")
move(800,900);move(600,500);move(100,400);run(4_800_000);capture("pointer-left")
check(isOpen() && paletteCloses==0 && taskCount()==desktopTasks,"leaving editor does not close window or task")
let beforeDrag=editor("w_wax0")
move(Int(beforeDrag)+180,Int(editor("w_way1"))+20);m.keyDown(0x70);run(4_800_000)
move(Int(beforeDrag)+260,Int(editor("w_way1"))+100);run(4_800_000);m.keyUp(0x70);run(24_000_000)
check(isOpen() && editor("w_wax0") != beforeDrag,"real title drag processes Open_Window_Request")
capture("dragged")
// The classic Tools file lacks textured title/scroll caps; real Wimp falls back to plain rectangles.
let tools=wimp("tool_list")
for name in ["tool_tbarlcap","tool_vwelltcap","tool_hwelllcap"] {check(word(tools+wimpSyms[name]!["value"]!.uint32Value)==0,"plain furniture: \(name)")}
let ws=moduleWorkspace("ArcPalette")
func label(_ n:Int)->String {text(ws+680+UInt32(n*4))}
func swatchFlags(_ n:Int)->UInt32 {word(editor("w_icons")+UInt32(n*32)+16)}
// 3.11 layout: the selected swatch shows its number inside an outline.
check(label(0)=="0" && swatchFlags(0)&4 != 0 && (1..<16).allSatisfy{label($0).isEmpty && swatchFlags($0)&4==0},"initial selection numbered and outlined")
// Select swatch one to avoid changing standard white/black, then drag all RGB channels.
clickWork(112,-142)
check(word(ws+16)==1 && label(1)=="1" && swatchFlags(1)&4 != 0 && label(0).isEmpty && swatchFlags(0)&4==0,"swatch selection shows its number")
for (i,y) in [-28,-60,-92].enumerated(){
 clickWork(24,y);run(2_400_000)
 check((m.vidc.palette[1] >> UInt32(i*4)) & 15 == 0,"slider low endpoint")
 let x=Int(editor("w_wax0")),top=Int(editor("w_way1"))
 move(x+24,top+y);m.keyDown(0x70);run(2_400_000);move(x+144,top+y);run(2_400_000)
 check((m.vidc.palette[1] >> UInt32(i*4)) & 15 == 8,"live slider changes before release")
 move(x+400,top+y);run(2_400_000)
 check((m.vidc.palette[1] >> UInt32(i*4)) & 15 == 15,"drag clamps beyond high endpoint")
 m.keyUp(0x70);run(4_800_000)
 check(isOpen(),"drag outside does not close editor")
}
capture("sliders")
check(m.vidc.border==border && m.vidc.cursorPalette==pointer,"desktop colour editing preserves border and pointer")
for i in 0..<4 {
 clickWork(46+i*66,-322)
 // The control being edited is inverted: black background, white text.
 check((word(editor("w_icons")+UInt32((16+i)*32)+16)>>24)==0x70,"selected Bor/Ms control is inverted")
 let previous=i==0 ? m.vidc.border:m.vidc.cursorPalette[i]
 let target:UInt32=previous&15==0 ? 15:0
 clickWork(target==15 ? 258:24,-28);run(2_400_000)
 let actual=i==0 ? m.vidc.border:m.vidc.cursorPalette[i]
 check(actual==(previous & ~UInt32(15))|target,"border/pointer RGB changes actual VIDC register")
}
capture("border-pointer")
// The original icon-bar menu: Invert, Mode, Save, Default (no Restore or Quit).
menu();capture("palette-menu")
check((0..<4).map{text(ws+384+28+UInt32($0*24)+12)}==["Invert","Mode","Save","Default"],"3.11 menu items")
menuItem(3);capture("defaulted")
check(m.vidc.palette==original && m.vidc.border & 0xfff==0x777 && m.vidc.cursorPalette==pointer,"Default restores standard colours, grey border and pointer")
// Colour 0 or 7: releasing re-spreads grey tones 1-6 between them.
clickWork(48,-142)
let x0=Int(editor("w_wax0")),top0=Int(editor("w_way1"))
move(x0+144,top0-28);m.keyDown(0x70);run(2_400_000);move(x0+16,top0-28);run(2_400_000);m.keyUp(0x70);run(9_600_000)
check(m.vidc.palette[0] & 15==0 && (1...6).allSatisfy{m.vidc.palette[$0] & 15==0} && (1...6).allSatisfy{(m.vidc.palette[$0]>>4)&15==(original[$0]>>4)&15},"greys 1-6 follow colour 0 on release")
capture("greys-spread")
menu();menuItem(3)
menu();menuItem(0);capture("inverted")
check(Array(m.vidc.palette.prefix(8))==Array(original.prefix(8).reversed()),"Invert reverses desktop greys")
let inverted=m.vidc.palette
func menuWindow(_ level:Int,_ name:String)->UInt32 {let h=word(moduleWorkspace("Wimp")+wimpSyms["menuhandles"]!["value"]!.uint32Value+UInt32(level*4));return word(h-1+wimpSyms[name]!["value"]!.uint32Value)}
func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func submenu(_ item:Int){
 menu()
 move(Int(menuWindow(0,"w_wax1"))-20,Int(menuWindow(0,"w_way1"))-22-item*44);run(24_000_000)
 check(Int32(bitPattern:wimp("menuSP"))>=4,"real submenu opens")
}
// Save: the real save box, typed full pathname, then Return.
submenu(2);capture("save-box")
m.keyDown(0x3b);press(ArcKey.forCharacter("u")!.0);m.keyUp(0x3b);run(720_000)
for ch in "ADFS::0.$.Pal" {let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}}
press(0x47);run(48_000_000);capture("saved")
check(Int32(bitPattern:wimp("menuSP"))<0,"saving closes the menu")
try Data(disc.mergedImage()).write(to:out.appendingPathComponent("saved.adf"))
menu();menuItem(3);check(m.vidc.palette==original,"Default before reload")
// Load: drag the saved file from a real Filer window onto the Palette window.
click(64,60);run(24_000_000*10);capture("floppy-root")
guard let fw=filingWindows.last?["definition"] as? [UInt32],let fi=filingIcons.last(where:{$0["text"] as? String=="Pal"})?["definition"] as? [UInt32] else {check(false,"Filer shows the saved palette file");exit(1)}
let fx=Int(Int32(bitPattern:fw[0]))+(Int(Int32(bitPattern:fi[0]))+Int(Int32(bitPattern:fi[2])))/2-Int(Int32(bitPattern:fw[4]))
let fy=Int(Int32(bitPattern:fw[3]))+(Int(Int32(bitPattern:fi[1]))+Int(Int32(bitPattern:fi[3])))/2-Int(Int32(bitPattern:fw[5]))
move(fx,fy);m.keyDown(0x70);run(4_800_000);m.mouseMove(dx:8,dy:-8);run(4_800_000)
move(Int(editor("w_wax0"))+144,Int(editor("w_way1"))-230);run(4_800_000);m.keyUp(0x70);run(48_000_000);capture("loaded")
check(m.vidc.palette==inverted,"a palette file dropped on the window is loaded")
menu();menuItem(3)
// Close the Filer window, which opened over the Palette window's title bar.
click(Int(Int32(bitPattern:fw[0]))+64,Int(Int32(bitPattern:fw[3]))+20);run(24_000_000)
// The close gadget must really close, and moving the pointer afterwards must not reopen it.
click(Int(editor("w_wax0"))+64,Int(editor("w_way1"))+20);run(2_400_000)
check(!isOpen() && paletteCloses==1,"close request closes editor exactly once")
move(100,400);check(!isOpen(),"closed window stays closed")
click(1148,60);run(2_400_000);capture("reopened")
check(isOpen(),"icon bar reopens editor")
func modeMenu(){submenu(1);capture("mode-menu")}
func modeChoice(_ index:Int){let x=Int(menuWindow(1,"w_wax0"))+64,y=Int(menuWindow(1,"w_way1"))-22-index*44;click(x,y);run(24_000_000)}
for (index,number,bpp) in [(1,15,3),(2,35,2),(3,36,3),(0,12,2)] {
 modeMenu();modeChoice(index);capture("mode-"+String(number))
 check(modeCalls.last==UInt32(number) && wimp("currentmode")==UInt32(number),"menu calls real Wimp_SetMode")
 check(m.vidc.bppCode==bpp && isOpen() && taskCount()==desktopTasks,"hardware depth changed; editor and desktop survive")
 move(100,400);check(isOpen(),"editor remains open after mode change and pointer leave")
}
func enterMode(_ value:String){
 modeMenu()
 // Moving into a writable menu item gives it the caret; clicking selects it.
 move(Int(menuWindow(1,"w_wax0"))+64,Int(menuWindow(1,"w_way1"))-198)
 run(4_800_000)
 m.keyDown(0x3b);press(ArcKey.forCharacter("u")!.0);m.keyUp(0x3b);run(720_000)
 for ch in value {press(ArcKey.forCharacter(ch)!.0)}
 check(text(ws+660)==value,"typed mode reaches the actual writable menu buffer")
 capture("typed-mode")
 press(0x47);run(96_000_000)
}
enterMode("15");check(wimp("currentmode")==15,"numeric mode field applies typed mode")
modeMenu();modeChoice(0);check(wimp("currentmode")==12,"return to mode 12")
allowExpectedError=true
enterMode("3");capture("rejected-text-mode")
check(errors.count==1 && errors[0]["component"] as? String=="ArcPalette" && wimp("currentmode")==12,"invalid desktop mode reports real error and preserves current mode")
press(0x47);run(4_800_000)
expectedErrors=errors;errors=[];allowExpectedError=false
check(taskCount()==desktopTasks && isOpen(),"mode error leaves Palette alive")
check([3,4,5].allSatisfy{m.cpu.exceptionCounts[$0]==0},"no abort/address exceptions")
json(["status":"PASS","rom_sha256":rom.sha256,"task_count":taskCount(),"palette_closes":paletteCloses,"palette_redraws":paletteRedraws,"mode_calls":modeCalls,"expected_errors":expectedErrors,"initialisations":initialisations,"errors":errors,"exceptions":m.cpu.exceptionCounts,"sprite_vector_calls":spriteVectorCalls,"generated_sprite_code":generated.values.sorted{($0["pc"]!,$0["word"]!)<($1["pc"]!,$1["word"]!)},"undefined":undefined,"cmos":m.cmos],"result")
print("PASS: Palette changes and restores actual VIDC colours")
