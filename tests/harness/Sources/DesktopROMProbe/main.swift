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
let startupExtras = ["ResFiler","ArcPalette","Free"].filter{c in modules.contains{$0["component"] as? String==c}}
let desktopTasks:UInt32 = 4+UInt32(startupExtras.count)
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[];config.monitor="standard";config.powerOnKeys=[0x34]
// A fitted floppy drive, no hard disc, and no automatic disc boot. These are
// ordinary persistent machine settings, not writes into guest OS workspace.
// The 3.60 ADFS byte includes IDE counts in bits 6-7, even on MEMC machines.
config.cmosSettings=[.init(byte:135,value:1),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12)]
let m=try Machine(configuration:config,rom:rom)
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
var undefined:[[String:Any]]=[]
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
// NetFiler starts on Service_StartFiler and, with no NetFS running (no
// Econet here), closes down again: it initialises but is not a persistent task.
let transient = modules.contains{$0["component"] as? String=="NetFiler"} ? ["NetFiler"]:[]
check(Set(initialisations.compactMap{$0["component"] as? String})==Set(["Desktop","Filer","Switcher","Pinboard","ADFSFiler"]+startupExtras+transient),"all original startup tasks initialised")
check(taskCount()==desktopTasks,"four persistent desktop tasks")
check((services[0x4a] ?? 0)>0,"Service_StartedWimp")
let before=opens["Switcher",default:0]
m.mouseMove(dx:(1230-Int(word(1424+28)))/2,dy:(60-Int(word(1424+32)))/2);run(4_800_000)
m.keyDown(0x70);run(2_400_000);m.keyUp(0x70);run(24_000_000*10)
capture("task-manager")
check(opens["Switcher",default:0]>before,"real mouse click opens TaskManager")
check(reportedTotal()==4194304,"TaskManager MEMC accounting totals 4 MB")
func click(_ x:Int,_ y:Int){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000);m.keyDown(0x70);run(2_400_000);m.keyUp(0x70);run(4_800_000)}
// Close TaskManager so its full-screen window does not cover the icon bar.
click(64,1004);run(24_000_000)
// Real icon-bar Select click, with a controlled, read-only floppy inserted.
click(64,60);run(24_000_000*10)
capture("floppy-root")
check(filingWindows.last?["title"] as? String=="ADFS::DTESTA.$","drive icon opens real floppy root")
check(Set(filingIcons.compactMap{$0["text"] as? String})==Set(["CheckFile","Docs","Hello","RootText","Zero"]),"root directory names drawn")
func openDirectory(_ name:String,_ title:String,_ children:[String]) {
 let w=filingWindows.last!["definition"] as! [UInt32],icon=filingIcons.last{$0["text"] as? String==name}!["definition"] as! [UInt32]
 let x=Int(Int32(bitPattern:w[0]))+(Int(Int32(bitPattern:icon[0]))+Int(Int32(bitPattern:icon[2])))/2-Int(Int32(bitPattern:w[4]))
 let y=Int(Int32(bitPattern:w[3]))+(Int(Int32(bitPattern:icon[1]))+Int(Int32(bitPattern:icon[3])))/2-Int(Int32(bitPattern:w[5]))
 let first=filingIcons.count
 m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000)
 for _ in 0..<2{m.keyDown(0x70);run(1_920_000);m.keyUp(0x70);run(1_920_000)}
 run(24_000_000*3)
 capture(name.lowercased())
 check(filingWindows.last?["title"] as? String==title,"double-click opens \(title)")
 check(Set(filingIcons.dropFirst(first).compactMap{$0["text"] as? String}).isSuperset(of:children),"nested directory names drawn")
}
openDirectory("Docs","ADFS::DTESTA.$.Docs",["Deep","Fragment","Sibling"])
openDirectory("Deep","ADFS::DTESTA.$.Docs.Deep",["Leaf"])
func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
press(0x0c);run(24_000_000*2);capture("shell-start")
check(initialisations.contains{$0["component"] as? String=="ShellCLI"},"F12 starts original ShellCLI")
check(taskCount()==desktopTasks+1,"temporary ShellCLI task is registered")
type("cat :0.$\n");capture("shell-catalogue")
shellScreens["catalogue"]=m.screenText
check(m.screenText.contains{$0.contains("Dir. ADFS::DTESTA.$")} && m.screenText.contains{$0.contains("RootText") && $0.contains("Zero")},"ShellCLI catalogue output")
type("type :0.$.RootText\n");capture("shell-file")
shellScreens["file"]=m.screenText
check(m.screenText.contains{$0=="DISC A -- same pathname, different media."},"ShellCLI reads actual file contents")
type("ArcLibreMissingCommand\n");capture("shell-error")
shellScreens["error"]=m.screenText
check(shellMessages==["File 'ArcLibreMissingCommand' not found"],"real missing-command error is handled")
type("type :0.$.Docs.Deep.Leaf\n");capture("shell-recovery")
shellScreens["recovery"]=m.screenText
check(m.screenText.contains{$0=="A leaf in the second nested directory."},"file access recovers after CLI error")
type("run :0.$.Hello\n");capture("shell-program")
shellScreens["program"]=m.screenText
check(m.screenText.contains{$0=="NESTED ARM2 PROGRAM EXECUTED"},"real on-disc ARM2 program runs and exits")
let pollsBeforeReturn=polls
press(0x47);run(24_000_000*2);capture("shell-return")
check(taskCount()==desktopTasks,"empty Return closes temporary shell task")
// ADFSFiler masks null events, so wake it with a genuine drive-icon click.
let opensBeforeRecovery=opens["Filer",default:0]
click(64,60);run(24_000_000);capture("desktop-recovery")
check(opens["Filer",default:0]>opensBeforeRecovery,"floppy icon still responds after ShellCLI")
check(["Filer","ADFSFiler","Switcher","Pinboard"].allSatisfy{polls[$0,default:0]>pollsBeforeReturn[$0,default:0]},"desktop tasks resume polling after ShellCLI")
json(["commands":shellCommands,"messages":shellMessages,"screens":shellScreens],"shell")
check([3,4,5].allSatisfy{m.cpu.exceptionCounts[$0]==0},"no abort/address exceptions")
let fdc=m.fdc.trace.last(10000).map{$0.description};try fdc.joined(separator:"\n").write(to:out.appendingPathComponent("fdc.log"),atomically:true,encoding:.utf8)
check(m.cpu.exceptionCounts[7]>0 && fdc.contains{$0.contains("readSector")},"real floppy FIQ transfers")
check(!fdc.contains{$0.contains("writeSector") || $0.contains("writeTrack")},"read-only filing test")
try Data(m.snapshot(createdBy:"ArcLibre ROM desktop")).write(to:out.appendingPathComponent("desktop.macarch-state"))
try Data(m.cmos).write(to:out.appendingPathComponent("cmos.bin"))
json(["status":"PASS","reported_total":reportedTotal(),"rom_sha256":rom.sha256,"initialisations":initialisations,"sprite_vector_calls":spriteVectorCalls,"generated_sprite_start":generatedStart,"generated_sprite_code":generated.values.sorted{a,b in a["pc"]! == b["pc"]! ? a["word"]! < b["word"]!:a["pc"]!<b["pc"]!},"undefined":undefined,"errors":errors,"polls":polls,"opens":opens,"services":services.map{["service":$0.key,"count":$0.value]},"task_count":taskCount(),"exceptions":m.cpu.exceptionCounts,"configuration":try JSONSerialization.jsonObject(with:JSONEncoder().encode(config))],"result")
print("PASS: cold desktop, TaskManager, floppy navigation and F12 command/error/program/return")
