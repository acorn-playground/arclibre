// SPDX-License-Identifier: Apache-2.0
// Power-on desktop experiment: no guest code injection or module loading.
import Foundation
import ArchimedesCore
import ProbeSupport
let a=CommandLine.arguments
precondition((5...7).contains(a.count),"GraphicsProbe ROM BUILD_DIRECTORY OUTPUT APP [reopen]")
let app=a[4]
let root=URL(fileURLWithPath:a[2]),trial=URL(fileURLWithPath:a[3])
let reopening=a.dropFirst(5).contains("reopen")
let advanced=a.dropFirst(5).contains("advanced")
let out=trial.appendingPathComponent(reopening ? "reopen":"write")
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
let modules=layout["modules"] as! [[String:Any]]
let desktopTasks:UInt32 = 4+UInt32(["ResFiler","ArcPalette","Free"].filter{c in modules.contains{$0["component"] as? String==c}}.count)
let hasPalette=modules.contains{$0["component"] as? String=="ArcPalette"}
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[trial.appendingPathComponent("test.hdf").path];config.monitor="standard";config.powerOnKeys=[0x34]
// Let the restored reset defaults and real attached-drive configuration act.
// No guest workspace writes or host CMOS setting overrides.
config.cmosSettings=[]
if reopening {config.powerOnKeys=[];config.cmosPath=trial.appendingPathComponent("saved.cmos").path}
var fixtureItems:[ADFSHardDiscBuilder.Item]=[.init(path:["ReadMe"],data:Array("ArcLibre original ST506 hard disc.\n".utf8),type:0xfff)]
let paintFixture=root.deletingLastPathComponent().appendingPathComponent("app-workflows/fixtures/PaintSprite")
if advanced && app=="Draw" && FileManager.default.fileExists(atPath:paintFixture.path) {fixtureItems.append(.init(path:["PaintSrc"],data:Array(try Data(contentsOf:paintFixture)),type:0xff9))}
if !reopening {precondition(!FileManager.default.fileExists(atPath:config.hardDiscs[0]!),"fresh disposable fixture only");try ADFSHardDiscBuilder.create(path:config.hardDiscs[0]!,geometry:HardDiscGeometry(cylinders:615,heads:4,sectorsPerTrack:32,sectorSize:256),name:"ArcDisc",items:fixtureItems)}
let m=try Machine(configuration:config,rom:rom)
var hdcLog:[String]=[]
m.hdc!.log={hdcLog.append("\(m.ticks) "+$0)}
m.fdc.trace=RingBuffer<WD1772.TraceEvent>(capacity:10000)
let discPath=root.deletingLastPathComponent().appendingPathComponent("desktop-baseline/artifacts/discs/DA.adf").path
m.insertFloppy(try FloppyImage.open(path:discPath,writeProtected:true),drive:0)
m.powerOn();let d=m.debugger;d.setTracing(100000)
var generated:[String:[String:UInt32]]=[:],generatedStart:UInt32=0,spriteVectorCalls=0
let spriteSymbols = modules.contains(where:{$0["component"] as? String=="SprExtend"}) ? try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/SprExtend/symbols.json"))) as? [String:NSNumber] : nil
let spriteEntry:UInt32 = spriteSymbols == nil ? 0 : (modules.first{$0["component"] as? String=="SprExtend"}!["base"] as! NSNumber).uint32Value + spriteSymbols!["My_SpriteOp"]!.uint32Value
if spriteEntry>0 { _=try d.addBreakpoint(.init(id:0,kind:.execute,start:spriteEntry)) }
let desktopSymbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Desktop/symbols.json"))) as! [String:NSNumber]
let welcomeBoundary=(modules.first{$0["component"] as? String=="Desktop"}!["base"] as! NSNumber).uint32Value+desktopSymbols["NoWelcome"]!.uint32Value
let welcomeBreakpoint=try d.addBreakpoint(.init(id:0,kind:.execute,start:welcomeBoundary))
let appTokens=try String(contentsOf:root.appendingPathComponent("graphics-runtime/"+app+".symbols"),encoding:.utf8).split(whereSeparator:{$0.isWhitespace})
let observedNames=app=="Draw" ? ["draw_displ_redrawarea","draw_displ_redrawtitle","draw_displ_do_objects"] : ["psprite_plot_scaled","sprwindow_invalidate"]
var appEntries:[UInt32:String]=[:]
for n in observedNames {let pc=UInt32(appTokens[appTokens.firstIndex(of:Substring(n))!-1],radix:16)!;appEntries[pc]=n;_=try d.addBreakpoint(.init(id:0,kind:.execute,start:pc))}
var appBuffers:[[String:Any]]=[],bufferBytes:[Data]=[]
var latestDocument=Data()

let sclTokens=try String(contentsOf:root.appendingPathComponent("c-runtime/SharedCLib.symbols"),encoding:.utf8).split(whereSeparator:{$0.isWhitespace})
func scl(_ name:String)->UInt32 {UInt32(sclTokens[sclTokens.firstIndex(of:Substring(name))!-1],radix:16)!}
let stackFault=scl("_kernel_StackOverflowFault")
var stackEvents:[[String:Any]]=[]
let stackEntries=Dictionary(uniqueKeysWithValues:["_kernel_StkOvfGetNewChunk","_kernel_StackOverflowExit"].map{(scl($0),$0)})
if advanced {
 _=try d.addBreakpoint(.init(id:0,kind:.execute,start:stackFault))
 for pc in stackEntries.keys {_=try d.addBreakpoint(.init(id:0,kind:.execute,start:pc))}
}
var transforms:[[String:Any]]=[]
let transformPC=(modules.first{$0["component"] as? String=="SprExtend"}!["base"] as! NSNumber).uint32Value+spriteSymbols!["compile_transform_code"]!.uint32Value
if advanced {_=try d.addBreakpoint(.init(id:0,kind:.execute,start:transformPC))}
var undefined:[[String:Any]]=[]
var initialisations:[[String:Any]]=[],errors:[[String:Any]]=[],polls:[String:Int]=[:],services:[UInt32:Int]=[:],opens:[String:Int]=[:],stages:[[String:Any]]=[]
var cli:[String]=[],lookups:[[String:Any]]=[]
var allWindows:[[String:Any]]=[]
var filingWindows:[[String:Any]]=[],filingIcons:[[String:Any]]=[]
var shellCommands:[String]=[],shellMessages:[String]=[],shellScreens:[String:[String]]=[:]
func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical) ?? 0xffffffff}
func text(_ p:UInt32)->String {var b:[UInt8]=[];for i in 0..<256 {guard let v=m.memc.debugRead(p+UInt32(i),space:.logical),v>=32 else{break};b.append(v)};return String(bytes:b,encoding:.isoLatin1) ?? "?"}
func component(_ pc:UInt32)->String {modules.first {let b=($0["base"] as! NSNumber).uint32Value;return pc>=b && pc<b+($0["length"] as! NSNumber).uint32Value}?["component"] as? String ?? "Kernel"}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
func trace(_ name:String){try! hdcLog.joined(separator:"\n").write(to:out.appendingPathComponent("hdc.log"),atomically:true,encoding:.utf8);let s=(d.trace?.last(100000) ?? []).map{"\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n"}.joined();try! s.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8)}
func check(_ b:Bool,_ s:String){if !b{trace("failure");json(["failure":s,"pc":m.cpu.pc,"exceptions":m.cpu.exceptionCounts,"initialisations":initialisations,"errors":errors,"polls":polls,"text":m.screenText],"failure");fputs("FAIL: \(s)\n",stderr);exit(1)}}
m.cpu.swiObserver={pc,n in
 let swi=n & ~UInt32(0x20000),c=component(pc)
 if advanced && swi==0x2e && [55,56].contains(m.cpu.r[0]&255) {
  let r=m.cpu.r;let name="transform-\(transforms.count)";let area=r[1],free=word(area+12)
  transforms.append(["entry":"SWI","registers":(0..<13).map{r[$0]},"matrix":(0..<6).map{word(r[6]+UInt32($0*4))},"area_file":name+".bin"])
  if free>=16 && free<1048576 {try! Data((0..<free).map{m.memc.debugRead(area+$0,space:.logical)!}).write(to:out.appendingPathComponent(name+".bin"))}
  json(transforms,"transforms")
 }
 if c=="BASIC" && swi==0x24 {trace("basic-export")}
 if swi==5 {cli.append(text(m.cpu.r[0]));json(cli,"cli")}
 if swi==0x41502 || swi==0x41506 {lookups.append(["pc":pc,"swi":swi,"r0":m.cpu.r[0],"token":text(m.cpu.r[swi==0x41502 ? 1:0])]);if lookups.count>100{lookups.removeFirst()};json(lookups,"lookups")}
 if c=="ShellCLI" && swi==5 {shellCommands.append(text(m.cpu.r[0]));trace("shell-command-\(shellCommands.count)")}
 if c=="ShellCLI" && swi==2 {shellMessages.append(text(m.cpu.r[0]))}
 if swi==0x400c0{initialisations.append(["component":c,"name":text(m.cpu.r[2]),"psr":m.cpu.psr,"version":m.cpu.r[0]])}
 if swi==0x400df{errors.append(["component":c,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}
 if swi==0x400c7 || swi==0x400e1{polls[c,default:0]+=1}
 if swi==0x400c5{opens[c,default:0]+=1}
 if swi==0x400c1 {let p=m.cpu.r[1];allWindows.append(["component":c,"title":text(word(p+72)),"definition":(0..<22).map{word(p+UInt32($0*4))}]);json(allWindows,"all-windows")}
 if swi==0x400c1 && c=="Filer" {let p=m.cpu.r[1];filingWindows.append(["title":text(word(p+72)),"definition":(0..<22).map{word(p+UInt32($0*4))}]);json(filingWindows,"filing-windows")}
 if swi==0x400e2 && c=="Filer" {let p=m.cpu.r[1];filingIcons.append(["text":text(word(p+20)),"definition":(0..<8).map{word(p+UInt32($0*4))}]);json(filingIcons,"filing-icons")}
 if swi==0x30{services[m.cpu.r[1],default:0]+=1;if m.cpu.r[1]==0x4a{trace("startup-complete")}}
}
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
// Resume only a real stop: resume() skips a breakpoint at the current PC.
// A timed slice may end at an exception vector before its breakpoint is seen.
func run(_ ticks:UInt64){let end=m.ticks+ticks;if d.isStopped {d.resume()};while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2400000),maxInstructions:300000)
 if d.isStopped {
  if m.cpu.pc==welcomeBoundary {
   capture("welcome");_=d.removeBreakpoint(welcomeBreakpoint.id)
  } else if let name=stackEntries[m.cpu.pc] {
   let base=m.cpu.r[10]-560
   stackEvents.append(["entry":name,"sl":m.cpu.r[10],"sp":m.cpu.r[13],"fp":m.cpu.r[11],"chunk":(0..<9).map{word(base+UInt32($0*4))}]);json(stackEvents,"stack-events")
  } else if m.cpu.pc==stackFault {
   let r=m.cpu.r;var frames:[[String:UInt32]]=[];var fp=r[11]
   for _ in 0..<32 {if fp<0x8000 || fp>0x2000000 {break};frames.append(["fp":fp,"pc":word(fp),"lr":word(fp-4),"sp":word(fp-8)]);let next=word(fp-12);if next==fp {break};fp=next}
   json(["registers":(0..<16).map{r[$0]},"frames":frames,"stack_chunk":(0..<16).map{word(r[10]-560+UInt32($0*4))}],"stack-fault")
   check(false,"real C stack overflow")
  } else if m.cpu.pc==transformPC {
   var vars:[String:UInt32]=[:]
   for n in ["screenstart","ywindlimit","linelength","gwx0","gwx1","gwy0","gwy1","orgx","orgy","BPP","save_inbpp"] {vars[n]=word(m.cpu.r[12]+spriteSymbols![n]!.uint32Value)}
   transforms.append(["entry":"compiler","variables":vars,"stack":(0..<24).map{word(m.cpu.r[13]+UInt32($0*4))},"registers":(0..<16).map{m.cpu.r[$0]}]);json(transforms,"transforms")
  } else if let name=appEntries[m.cpu.pc] {
   var start:UInt32=0,count:UInt32=0
   if app=="Draw" {
    let diag=m.cpu.r[0],misc=word(diag+8),paper=word(diag+12),lo=word(misc),hi=word(misc+4)
    check(hi>=lo && hi-lo<1048576,"Draw object bounds");start=paper+lo;count=hi-lo
   } else {
    let sprite=m.cpu.r[name=="psprite_plot_scaled" ? 2:0],file=word(sprite+4),area=word(file+8)
    let free=word(area+12);check(free>=16 && free<1048576,"Paint sprite area bounds");start=area+4;count=free-4
   }
   let bytes=Data((0..<count).map{m.memc.debugRead(start+$0,space:.logical)!})
   latestDocument=bytes
   if !bufferBytes.contains(bytes) {let filename="document-buffer-\(bufferBytes.count).bin";try! bytes.write(to:out.appendingPathComponent(filename));bufferBytes.append(bytes);appBuffers.append(["entry":name,"file":filename,"address":start,"length":count]);json(appBuffers,"document-buffers");trace("document-buffer")}
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
 };check(errors.isEmpty,"desktop error: \(errors)")}
func moduleWorkspace(_ c:String)->UInt32 {var node=word(2000);let base=(modules.first{$0["component"] as! String==c}!["base"] as! NSNumber).uint32Value
 for _ in 0..<50 {if node==0{break};if word(node+4)==base{return word(word(node+12)+4)};node=word(node)};return 0xffffffff}
func taskCount()->UInt32 {let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]];return word(moduleWorkspace("Wimp")+syms["taskcount"]!["value"]!.uint32Value)}
func reportedTotal()->UInt32 {let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Switcher/symbols.json"))) as! [String:NSNumber]
 var node=word(moduleWorkspace("Switcher")+syms["wlink"]!.uint32Value)
 for _ in 0..<100 {if node==0 || node==0xffffffff{break};if m.memc.debugRead(node+syms["icb_icon1"]!.uint32Value,space:.logical)==UInt8(syms["ic_totalname"]!.uint32Value){return word(node+syms["icb_memsize"]!.uint32Value)};node=word(node+syms["icb_link"]!.uint32Value)};return 0xffffffff}
func capture(_ name:String){if advanced && !latestDocument.isEmpty {try! latestDocument.write(to:out.appendingPathComponent(name+"-document.bin"))};trace(name);let f=m.currentFrame;check(writePNG(f,to:out.appendingPathComponent(name+".png")),"PNG");let screen=word(0x10c0),line=word(0x1088);let b=(0..<Int(line)*256).map{m.memc.debugRead(screen+UInt32($0),space:.logical)!};try! Data(b).write(to:out.appendingPathComponent(name+"-screen.bin"));stages.append(["name":name,"ticks":m.ticks,"task_count":taskCount(),"polls":polls,"opens":opens,"palette":m.vidc.palette,"line_length":line,"pc":m.cpu.pc,"psr":m.cpu.psr]);json(stages,"stages")}
check(m.cpu.pc==0 && m.cpu.psr==0x0c000003,"real reset vector")
run(24_000_000*35)
capture("desktop")


func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
func move(_ x:Int,_ y:Int){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000)}
func replaceField(_ value:String){m.keyDown(0x3b);press(0x2d);m.keyUp(0x3b);run(2_400_000);type(value)}
func click(_ x:Int,_ y:Int,_ count:Int=1){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000);for _ in 0..<count{m.keyDown(0x70);run(1_920_000);m.keyUp(0x70);run(1_920_000)};run(24_000_000)}
let wimpSyms=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]]
func ws(_ name:String)->UInt32 {wimpSyms[name]!["value"]!.uint32Value}
func menuHandle(_ level:Int)->UInt32 {word(moduleWorkspace("Wimp")+ws("menuhandles")+UInt32(level*4))-1}
func menuPoint(_ level:Int,_ item:Int,_ arrow:Bool=false)->(Int,Int) {
 let h=menuHandle(level),icons=word(h+ws("w_icons")),i=icons+UInt32(item*3+1)*ws("i_size")
 let x=arrow ? Int(word(h+ws("w_wax1")))-12:Int(word(h+ws("w_wax0")))+64
 let y=Int(word(h+ws("w_way1")))+(Int(Int32(bitPattern:word(i+ws("i_bby0"))))+Int(Int32(bitPattern:word(i+ws("i_bby1")))))/2
 return (x,y)
}
func appMenu(){move(app=="Paint" ? 240:300,app=="Paint" ? 720:600);m.keyDown(0x71);run(1_920_000);m.keyUp(0x71);run(24_000_000)}
func subMenu(_ level:Int,_ item:Int){let (x,y)=menuPoint(level,item,true);move(x,y);run(24_000_000);check(Int32(bitPattern:word(moduleWorkspace("Wimp")+ws("menuSP")))>=Int32((level+1)*4),"real submenu opens")}
func choose(_ level:Int,_ item:Int){let (x,y)=menuPoint(level,item);click(x,y);run(24_000_000)}
// RISC_OSLib's dboxtcol opens the application's "dboxtcol" window as the
// next submenu. Click icons in it by their template positions (work-area
// origin at the top left of the open window; it is never scrolled).
func colourDialogue(_ level:Int,_ title:String,_ icons:[(Int,Int)]){
 let h=menuHandle(level);check(allWindows.last?["title"] as? String==title,"colour dialogue \(title) is created");capture("colour-dialogue")
 for (x,y) in icons {click(Int(word(h+ws("w_wax0")))+x,Int(word(h+ws("w_way1")))+y)}
}
// Open the real hard-disc root before launching the application.
click(64,60);run(24_000_000);capture("hard-disc-root")
check(filingWindows.last?["title"] as? String=="ADFS::ArcDisc.$","desktop hard-disc icon opens root")
func openFilingIcon(_ name:String) {
let w=filingWindows.last!["definition"] as! [UInt32],ic=filingIcons.last{$0["text"] as? String==name}!["definition"] as! [UInt32]
let x=Int(Int32(bitPattern:w[0]))+(Int(Int32(bitPattern:ic[0]))+Int(Int32(bitPattern:ic[2])))/2-Int(Int32(bitPattern:w[4]))
let y=Int(Int32(bitPattern:w[3]))+(Int(Int32(bitPattern:ic[1]))+Int(Int32(bitPattern:ic[3])))/2-Int(Int32(bitPattern:w[5]))
click(x,y,2)
}
if reopening {
 openFilingIcon(app+"Doc");run(24_000_000*5);capture("reopened")
} else {
 click(288,60);run(24_000_000*2);capture("apps")
 openFilingIcon("!"+app);run(24_000_000*8);capture("started")
 check(initialisations.contains{$0["name"] as? String==app},"original application initialises")
 click(hasPalette ? 1060:1150,60);run(24_000_000*2);capture("new")
 if app=="Draw" {
  if !advanced {
   // Style > Fill colour: the desktop's yellow (colour 9), then OK.
   appMenu();subMenu(0,2);subMenu(1,2);colourDialogue(2,"Fill colour",[(94,-230),(412,-296)]);capture("fill-chosen")
  }
  click(64,584);click(248,708);click(648,468);capture("drawn")
  if advanced {
   // Real original Draw commands: Tab enters text, Return commits it.
   press(0x26);click(300,640);type("ArcLibre Draw text");press(0x47);press(0x00)
   run(24_000_000);capture("text-object")
   check(bufferBytes.contains{$0.range(of:Data("ArcLibre Draw text".utf8)) != nil},"Draw stores the actual typed text object")
   press(0x08);run(24_000_000);capture("undo-text")
   check(latestDocument.range(of:Data("ArcLibre Draw text".utf8))==nil,"Undo removes text object")
   press(0x09);run(24_000_000);capture("redo-text")
   check(latestDocument.range(of:Data("ArcLibre Draw text".utf8)) != nil,"Redo restores text object")
   press(0x05);run(24_000_000);capture("select-all")
   appMenu();subMenu(0,2);subMenu(1,8);capture("font-menu")
   subMenu(2,1);capture("font-family")
   choose(3,0);capture("outline-text")
   press(0x04);run(24_000_000);capture("grouped")
   m.keyDown(0x4c);press(0x04);m.keyUp(0x4c);run(24_000_000);appMenu();press(0x00);run(24_000_000);capture("ungrouped")
   appMenu();subMenu(0,5);subMenu(1,1)
   let (sx,sy)=menuPoint(2,0);move(sx,sy);replaceField("2\n");run(24_000_000);capture("scaled-draw")
   if FileManager.default.fileExists(atPath:root.deletingLastPathComponent().appendingPathComponent("app-workflows/fixtures/PaintSprite").path) {
    m.keyDown(0x4c);press(0x02);m.keyUp(0x4c);run(24_000_000);capture("insert-dialogue")
    replaceField("ADFS::4.$.PaintSrc\n");run(24_000_000);capture("imported-paint")
   }
  }
  press(0x03);run(24_000_000);capture("save-dialogue")
  replaceField("ADFS::4.$.DrawDoc\n");run(24_000_000*3);capture("saved")
 } else {
  click(508,728);replaceField("32")
  click(508,668);replaceField("32")
  click(820,352);run(24_000_000*2);capture("sprite-created")
  click(674,664);move(208,744);m.keyDown(0x70);run(4_800_000)
  if advanced {move(210,744)}
  for i in 1...9 {move(208+i*4,744-i*4);if advanced {move(210+i*4,744-i*4)}}
  m.keyUp(0x70);run(24_000_000);capture("painted")
  if !advanced {
   // Paint > Edit palette for the painting colour: the desktop's red
   // (colour 11), then OK.
   appMenu();subMenu(0,2);subMenu(1,5);colourDialogue(2,"Edit colour",[(206,-230),(412,-296)]);capture("palette-edited")
  }
  if advanced {
   appMenu();subMenu(0,3);capture("paint-edit-menu");choose(1,0);capture("flipped")
   appMenu();subMenu(0,3);subMenu(1,2);capture("rotate-menu")
   let (x,y)=menuPoint(2,0);move(x,y);replaceField("90\n");run(24_000_000);capture("rotated")
   appMenu();subMenu(0,3);subMenu(1,3)
   let (sx,sy)=menuPoint(2,0);move(sx,sy);replaceField("2\n");run(24_000_000);capture("scaled-paint")
   appMenu();subMenu(0,3);choose(1,11);capture("mask-removed")
   appMenu();subMenu(0,3);choose(1,11);capture("mask-restored")
  }
  move(300,600);m.keyDown(0x71);run(1_920_000);m.keyUp(0x71);run(24_000_000);capture("file-menu")
  click(316,492);run(24_000_000);capture("save-dialogue")
  replaceField("ADFS::4.$.PaintDoc\n");run(24_000_000*3);capture("saved")
 }

}
json(["initialisations":initialisations,"windows":allWindows,"errors":errors,"screen":m.screenText],"progress")
check(taskCount()==desktopTasks+1 && !appBuffers.isEmpty,"application remains live with observed document data")
check(initialisations.contains{($0["name"] as? String==app) && (($0["psr"] as! UInt32)&3==0)},"original application initialises in USR26")
m.hardDiscImages[0]!.synchronize()
if !reopening {try Data(m.cmos).write(to:trial.appendingPathComponent("saved.cmos"))}
json(["stack_events":stackEvents,"advanced":advanced,"document_buffers":appBuffers,"status":"PASS","rom_sha256":rom.sha256,"app":app,"phase":reopening ? "reopen":"write","task_count":taskCount(),"cmos":m.cmos,"configuration":try JSONSerialization.jsonObject(with:JSONEncoder().encode(config)),"initialisations":initialisations,"errors":errors,"exceptions":m.cpu.exceptionCounts,"writes":m.hardDiscImages[0]!.writeCount,"sprite_vector_calls":spriteVectorCalls,"generated_sprite_code":generated.values.sorted{($0["pc"]!,$0["word"]!)<($1["pc"]!,$1["word"]!)},"undefined":undefined],"result")
print("PASS: original \(app) workflow executed; independent media verification follows")
