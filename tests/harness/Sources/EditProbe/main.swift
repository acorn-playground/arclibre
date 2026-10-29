// SPDX-License-Identifier: Apache-2.0
// Power-on desktop experiment: no guest code injection or module loading.
import Foundation
import ArchimedesCore
import ProbeSupport
let a=CommandLine.arguments
precondition((4...6).contains(a.count),"EditProbe ROM BUILD_DIRECTORY OUTPUT [reopen]")
let root=URL(fileURLWithPath:a[2]),trial=URL(fileURLWithPath:a[3])
let reopening=a.dropFirst(4).contains("reopen")
let advanced=a.dropFirst(4).contains("advanced")
let taskWindowTest=a.dropFirst(4).contains("taskwindow")
let out=trial.appendingPathComponent(reopening ? "reopen":"write")
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
let modules=layout["modules"] as! [[String:Any]]
let hasPalette=modules.contains{$0["component"] as? String=="ArcPalette"}
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[trial.appendingPathComponent("test.hdf").path];config.monitor="standard";config.powerOnKeys=[0x34]
// A fitted floppy drive, no hard disc, and no automatic disc boot. These are
// ordinary persistent machine settings, not writes into guest OS workspace.
// The 3.60 ADFS byte includes IDE counts in bits 6-7, even on MEMC machines.
config.cmosSettings=[]
if reopening {config.powerOnKeys=[];config.cmosPath=trial.appendingPathComponent("saved.cmos").path}
if !reopening {precondition(!FileManager.default.fileExists(atPath:config.hardDiscs[0]!),"fresh disposable fixture only");try ADFSHardDiscBuilder.create(path:config.hardDiscs[0]!,geometry:HardDiscGeometry(cylinders:615,heads:4,sectorsPerTrack:32,sectorSize:256),name:"ArcDisc",items:[.init(path:["ReadMe"],data:Array("ArcLibre original ST506 hard disc.\n".utf8),type:0xfff)])}
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
let symbolTokens=try String(contentsOf:root.appendingPathComponent("c-runtime/SharedCLib.symbols"),encoding:.utf8).split(whereSeparator:{$0.isWhitespace})
let textEntries=Set(["txt_size","txt_settitle","txt_charoptions"].map{UInt32(symbolTokens[symbolTokens.firstIndex(of:Substring($0))!-1],radix:16)!})
for pc in textEntries {_=try d.addBreakpoint(.init(id:0,kind:.execute,start:pc))}
var textBuffers:[[String:Any]]=[]
let wimpSyms=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]]
func ws(_ name:String)->UInt32 {wimpSyms[name]!["value"]!.uint32Value}
var windowHandles:[String:UInt32]=[:]
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
 if c=="BASIC" && swi==0x24 {trace("basic-export")}
 if swi==5 {cli.append(text(m.cpu.r[0]));json(cli,"cli")}
 if swi==0x41502 || swi==0x41506 {lookups.append(["pc":pc,"swi":swi,"r0":m.cpu.r[0],"token":text(m.cpu.r[swi==0x41502 ? 1:0])]);if lookups.count>100{lookups.removeFirst()};json(lookups,"lookups")}
 if c=="ShellCLI" && swi==5 {shellCommands.append(text(m.cpu.r[0]));trace("shell-command-\(shellCommands.count)")}
 if c=="ShellCLI" && swi==2 {shellMessages.append(text(m.cpu.r[0]))}
 if swi==0x400c0{initialisations.append(["component":c,"name":text(m.cpu.r[2]),"psr":m.cpu.psr,"version":m.cpu.r[0]])}
 if swi==0x400df{errors.append(["component":c,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}
 if swi==0x400c7 || swi==0x400e1{polls[c,default:0]+=1}
 if swi==0x400c5{
  opens[c,default:0]+=1
  if advanced {let h=word(m.cpu.r[1]),w=h-1,t=w+ws("w_title");let title=text(word(w+ws("w_titleflags"))&256 != 0 ? word(t):t);windowHandles[title]=h}
 }
 if swi==0x400c1 {let p=m.cpu.r[1];allWindows.append(["component":c,"title":text(word(p+72)),"definition":(0..<22).map{word(p+UInt32($0*4))}]);json(allWindows,"all-windows")}
 if swi==0x400c1 && c=="Filer" {let p=m.cpu.r[1];filingWindows.append(["title":text(word(p+72)),"definition":(0..<22).map{word(p+UInt32($0*4))}]);json(filingWindows,"filing-windows")}
 if swi==0x400e2 && c=="Filer" {let p=m.cpu.r[1];filingIcons.append(["text":text(word(p+20)),"definition":(0..<8).map{word(p+UInt32($0*4))}]);json(filingIcons,"filing-icons")}
 if swi==0x30{services[m.cpu.r[1],default:0]+=1;if m.cpu.r[1]==0x4a{trace("startup-complete")}}
}
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
func run(_ ticks:UInt64){let end=m.ticks+ticks;if d.isStopped {d.resume()};while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2400000),maxInstructions:300000)
 if d.isStopped {
  if m.cpu.pc==welcomeBoundary {
   capture("welcome");_=d.removeBreakpoint(welcomeBreakpoint.id)
  } else if textEntries.contains(m.cpu.pc) {
   // Read the actual original txt1_str while its owning task is mapped.
   let t=m.cpu.r[0],buf=word(t+4),top=Int(word(t+8)),gs=Int(word(t+20)),ge=Int(word(t+24)),start=Int(word(t+28))
   check(top>=1 && top<1048576 && [gs,ge,start].allSatisfy{$0>=0 && $0<=top},"original text buffer bounds")
   let count=top-(ge-gs+top+1)%(top+1)
   var pos=start,b:[UInt8]=[]
   for _ in 0..<count {if pos==gs{pos=ge};b.append(m.memc.debugRead(buf+UInt32(pos),space:.logical)!);pos=(pos+1)%(top+1)}
   let value=String(bytes:b,encoding:.isoLatin1) ?? "?"
   if textBuffers.last?["text"] as? String != value {textBuffers.append(["text":value,"structure":t,"buffer":buf,"top":top,"gap_start":gs,"gap_end":ge,"text_start":start]);json(textBuffers,"text-buffers");trace("edit-buffer")}
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
func capture(_ name:String){trace(name);let f=m.currentFrame;check(writePNG(f,to:out.appendingPathComponent(name+".png")),"PNG");let screen=word(0x10c0),line=word(0x1088);let b=(0..<Int(line)*256).map{m.memc.debugRead(screen+UInt32($0),space:.logical)!};try! Data(b).write(to:out.appendingPathComponent(name+"-screen.bin"));stages.append(["name":name,"ticks":m.ticks,"task_count":taskCount(),"polls":polls,"opens":opens,"palette":m.vidc.palette,"line_length":line,"pc":m.cpu.pc,"psr":m.cpu.psr]);json(stages,"stages")}
check(m.cpu.pc==0 && m.cpu.psr==0x0c000003,"real reset vector")
run(24_000_000*35)
capture("desktop")


func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
func field(_ title:String,_ icon:Int){
 guard let handle=windowHandles[title] else {check(false,"dialogue opened: "+title);return}
 let w=handle-1,i=word(w+ws("w_icons"))+UInt32(icon)*ws("i_size")
 func signed(_ p:UInt32)->Int {Int(Int32(bitPattern:word(p)))}
 let x=signed(w+ws("w_wax0"))+(signed(i+ws("i_bbx0"))+signed(i+ws("i_bbx1")))/2-signed(w+ws("w_scx"))
 let y=signed(w+ws("w_way1"))+(signed(i+ws("i_bby0"))+signed(i+ws("i_bby1")))/2-signed(w+ws("w_scy"))
 click(x,y)
}
func click(_ x:Int,_ y:Int,_ count:Int=1){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000);for _ in 0..<count{m.keyDown(0x70);run(1_920_000);m.keyUp(0x70);run(1_920_000)};run(24_000_000)}
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
 openFilingIcon("Document");run(24_000_000*5);capture("edit-reopened")
 check(initialisations.contains{$0["name"] as? String=="Edit"},"saved document launches original Edit")
} else {
// Discover the original Apps viewer using its icon-bar entry.
click(288,60);run(24_000_000*2);capture("apps")
json(["initialisations":initialisations,"windows":allWindows,"filing":filingWindows,"icons":filingIcons,"errors":errors,"screen":m.screenText],"progress")


openFilingIcon("!Edit");run(24_000_000*15);capture("edit-start")
json(["initialisations":initialisations,"windows":allWindows,"errors":errors,"screen":m.screenText],"edit-progress")
check(initialisations.contains{$0["name"] as? String=="Edit"},"original Edit initialises")

if taskWindowTest {
 let baseCount=taskCount()
 press(0x0c);type("WimpTask TaskWindow BASIC -name BasicGate -display -quit\n");press(0x47);run(24_000_000*5);capture("basic-task-window")
 check(initialisations.contains{$0["component"] as? String=="TaskWindow"},"real TaskWindow starts")
 check(taskCount()==baseCount+1,"Edit and BASIC child both active")
 type("PRINT 6*7\n");run(24_000_000*2);capture("basic-answer")
 check(textBuffers.contains{($0["text"] as? String)?.contains("42")==true},"BASIC answer reaches original Edit buffer")
 let oldPolls=polls
 type("REPEAT:UNTIL FALSE\n");run(24_000_000*4);capture("basic-busy")
 check(["SharedCLib","TaskWindow"].allSatisfy{polls[$0,default:0]>oldPolls[$0,default:0]},"Edit library and TaskWindow poll during CPU-bound BASIC")
 let oldOpens=opens["Filer",default:0];click(64,60);run(24_000_000);capture("basic-busy-filer")
 check(opens["Filer",default:0]>oldOpens,"Filer responds while BASIC is busy")
 press(0x00);run(24_000_000*3);capture("basic-escape")
 check(textBuffers.contains{($0["text"] as? String)?.contains("Escape")==true},"keyboard Escape interrupts busy BASIC")
 type("PRINT 7*7\n");run(24_000_000*2)
 check(textBuffers.contains{($0["text"] as? String)?.contains("49")==true},"BASIC recovers after escape")
 type("QUIT\n");run(24_000_000*5);capture("basic-quit")
 check(taskCount()==baseCount,"BASIC child exits leaving original Edit alive")
 json(["status":"PASS","rom_sha256":rom.sha256,"task_count":taskCount(),"initialisations":initialisations,"errors":errors,"exceptions":m.cpu.exceptionCounts,"sprite_vector_calls":spriteVectorCalls,"generated_sprite_code":generated.values.sorted{($0["pc"]!,$0["word"]!)<($1["pc"]!,$1["word"]!)},"undefined":undefined,"text_buffers":textBuffers,"polls":polls,"cli":cli],"result")
 print("PASS: original Edit TaskWindow, busy BASIC, Escape and recovery")
 exit(0)
}

click(hasPalette ? 1060:1150,60);run(24_000_000);capture("edit-new")
type("ArcLibre document saved by the original Edit.\nSecond line survives a cold restart.\n");capture("edit-typed")
if advanced {
 // Original Edit selection-copy semantics: select in one window, copy to another.
 func ctrl(_ key:UInt8){m.keyDown(0x3b);press(key);m.keyUp(0x3b);run(2_400_000)}
 ctrl(0x59);press(0x06);ctrl(0x63);press(0x06);capture("edit-selected")
 click(hasPalette ? 1060:1150,60);run(24_000_000);capture("edit-second-window")
 let second=textBuffers.last!["structure"] as! UInt32
 func currentText()->String {textBuffers.last{($0["structure"] as? UInt32)==second}?["text"] as? String ?? "?"}
 check(currentText()=="","new destination text is empty")
 ctrl(0x50);run(24_000_000);capture("edit-copied")
 check(currentText()=="ArcLibre document saved by the original Edit.\nSecond line survives a cold restart.\n","real selection copied between documents")
 press(0x08);run(24_000_000);capture("edit-undo-copy");check(currentText()=="","Undo removes copied selection")
 press(0x09);run(24_000_000);capture("edit-redo-copy");check(currentText().hasPrefix("ArcLibre document"),"Redo restores copied selection")
 ctrl(0x59);press(0x04);run(24_000_000);capture("edit-find-dialogue")
 type("Second");field("Find text",3);type("Revised");field("Find text",0);run(24_000_000);capture("edit-found")
 press(0x44);run(24_000_000);capture("edit-replaced")
 check(currentText().contains("Revised line survives"),"Find and last-replace change the actual document")
}
press(0x03);run(24_000_000);capture("edit-save-dialogue")
json(["initialisations":initialisations,"windows":allWindows,"errors":errors,"screen":m.screenText],"edit-progress")

m.keyDown(0x3b);press(0x2d);m.keyUp(0x3b);run(2_400_000)
type("ADFS::4.$.Document\n");run(24_000_000*3);capture("edit-saved")
}
m.hardDiscImages[0]!.synchronize()
if !reopening {try Data(m.cmos).write(to:trial.appendingPathComponent("saved.cmos"))}
let expected="ArcLibre document saved by the original Edit.\n"+(advanced ? "Revised":"Second")+" line survives a cold restart.\n"
check(textBuffers.contains{$0["text"] as? String==expected},"exact document bytes in real Edit buffer")
json(["advanced":advanced,"status":"PASS","rom_sha256":rom.sha256,"phase":reopening ? "reopen":"write","task_count":taskCount(),"cmos":m.cmos,"configuration":try JSONSerialization.jsonObject(with:JSONEncoder().encode(config)),"initialisations":initialisations,"errors":errors,"exceptions":m.cpu.exceptionCounts,"writes":m.hardDiscImages[0]!.writeCount,"sprite_vector_calls":spriteVectorCalls,"generated_sprite_code":generated.values.sorted{($0["pc"]!,$0["word"]!)<($1["pc"]!,$1["word"]!)},"undefined":undefined,"text_buffers":textBuffers],"result")
print("PASS: original Edit document saved")
