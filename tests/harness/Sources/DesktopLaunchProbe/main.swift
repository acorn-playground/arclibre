// SPDX-License-Identifier: Apache-2.0
// Power-on desktop experiment: no guest code injection or module loading.
import Foundation
import ArchimedesCore
import ProbeSupport
let a=CommandLine.arguments
precondition(a.count==6 || (a.count==7 && ["drag","copy","move","delete","protected","net"].contains(a[6])),"DesktopLaunchProbe ROM BUILD_DIRECTORY DISC OUTPUT APPLICATION")
// "net": the machine is Econet station 1 (a fitted Econet module, no other
// stations), so the ROM's NetFS and NetPrint start as on a networked 3.11.
let netTest=a.count==7 && a[6]=="net"
let dragTest=a.count==7 && a[6]=="drag"
let actionTest=a.count==7 && ["copy","move","delete","protected"].contains(a[6])
let protectedTest=a.count==7 && a[6]=="protected"
let moveTest=a.count==7 && a[6]=="move"
let deleteTest=a.count==7 && a[6]=="delete"
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[4])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
let modules=layout["modules"] as! [[String:Any]]
let startupExtras = ["ResFiler","ArcPalette","Free"].filter{c in modules.contains{$0["component"] as? String==c}}
// NetFiler is a desktop task only when NetFS is running, as on 3.11.
let desktopTasks:UInt32 = 4+UInt32(startupExtras.count)+(netTest && modules.contains{$0["component"] as? String=="NetFiler"} ? 1:0)
precondition(rom.sha256==layout["rom_sha256"] as! String)
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[];config.monitor="standard";config.powerOnKeys=[0x34]
// A fitted floppy drive, no hard disc, and no automatic disc boot. These are
// ordinary persistent machine settings, not writes into guest OS workspace.
// The 3.60 ADFS byte includes IDE counts in bits 6-7, even on MEMC machines.
config.cmosSettings=[.init(byte:135,value:1),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12)]
if netTest {config.econetStation=1}
let m=try Machine(configuration:config,rom:rom)
m.fdc.trace=RingBuffer<WD1772.TraceEvent>(capacity:10000)
var discPath=a[3];let target=a[5]
// Configure saves its file to a writable copy of the fixture.
if target=="!Configure" {let copy=out.appendingPathComponent("disc.adf");try? FileManager.default.removeItem(at:copy);try FileManager.default.copyItem(at:URL(fileURLWithPath:discPath),to:copy);discPath=copy.path}
let disc=try FloppyImage.open(path:discPath,writeProtected:(!actionTest && !["!SprTest","!Configure"].contains(target)) || protectedTest)
m.insertFloppy(disc,drive:0)
m.powerOn();let d=m.debugger;d.setTracing(20000)
let kernelSymbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-baseline/artifacts/symbols.json"))) as! [String:NSNumber]
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:kernelSymbols["MouseButtonChange"]!.uint32Value,logMessage:"BUTTON {R0}"))
let ws=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]]
var generated:[String:[String:UInt32]]=[:],generatedStart:UInt32=0,spriteVectorCalls=0
let spriteSymbols = modules.contains(where:{$0["component"] as? String=="SprExtend"}) ? try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/SprExtend/symbols.json"))) as? [String:NSNumber] : nil
let spriteEntry:UInt32 = spriteSymbols == nil ? 0 : (modules.first{$0["component"] as? String=="SprExtend"}!["base"] as! NSNumber).uint32Value + spriteSymbols!["My_SpriteOp"]!.uint32Value
if spriteEntry>0 { _=try d.addBreakpoint(.init(id:0,kind:.execute,start:spriteEntry)) }
let desktopSymbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Desktop/symbols.json"))) as! [String:NSNumber]
let welcomeBoundary=(modules.first{$0["component"] as? String=="Desktop"}!["base"] as! NSNumber).uint32Value+desktopSymbols["NoWelcome"]!.uint32Value
let welcomeBreakpoint=try d.addBreakpoint(.init(id:0,kind:.execute,start:welcomeBoundary))
let filerSymbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Filer/symbols.json"))) as! [String:NSNumber]
let filerClick=(modules.first{$0["component"] as? String=="Filer"}!["base"] as! NSNumber).uint32Value+filerSymbols["event_mouse_click"]!.uint32Value
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:filerClick))
var loaderInstructions:[[UInt32]]=[],gameEntries:[[UInt32]]=[],loaderErrors:[[String:Any]]=[]
var loaderBreakpointID:Int?=nil
if target=="!Zarch" {
 loaderBreakpointID=try d.addBreakpoint(.init(id:0,kind:.execute,start:0x8000,end:0x84e7)).id
 _=try d.addBreakpoint(.init(id:0,kind:.execute,start:0xdba8))
}
var actionReturn:UInt32=0
if actionTest {
 let module=modules.first{$0["component"] as? String=="Filer"}!
 let start=(module["base"] as! NSNumber).uint32Value+filerSymbols["StartActionWindow"]!.uint32Value
 for p in stride(from:start,to:start+256,by:4) where m.memc.debugReadWord(p,space:.logical)==0xef0600de {actionReturn=p+4;break}
 check(actionReturn>0,"action start return located")
 _=try d.addBreakpoint(.init(id:0,kind:.execute,start:actionReturn))
}
var pipeReturn:UInt32=0,pipeReturns:[[String:Any]]=[]
if target=="!StrTest", let module=modules.first(where:{$0["component"] as? String=="PipeFS"}) {
 let syms=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("stream-runtime/modules/PipeFS/symbols.json"))) as! [String:NSNumber]
 let start=(module["base"] as! NSNumber).uint32Value+syms["sleepnomore"]!.uint32Value
 for p in stride(from:start,to:start+64,by:4) where m.memc.debugReadWord(p,space:.logical)==0xef020033 {pipeReturn=p+4;break}
 precondition(pipeReturn>0)
 _=try d.addBreakpoint(.init(id:0,kind:.execute,start:pipeReturn))
}
var streamDriver:[String:Any]=[:]
var clientVeneerWords:[[String:UInt32]]=[]
let clientVeneerAddresses:[UInt32] = ["!CAbiTest","!TaskTest","!StrTest","!RamTest","!UtilTest","!SqTest"].contains(target) ? (try JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent(target=="!TaskTest" ? "task-service-app/runtime-veneers.json" : target=="!StrTest" ? "stream-app/runtime-veneers.json" : target=="!RamTest" ? "ram-app/runtime-veneers.json" : target=="!UtilTest" ? "utility-app/runtime-veneers.json" : target=="!SqTest" ? "squash-app/runtime-veneers.json" : "c-abi-app/runtime-veneers.json"))) as! [NSNumber]).map{$0.uint32Value} : []
var actionReturns:[[String:Any]]=[]
var menus:[[String:Any]]=[]
var actionWindowTexts:[UInt32:[String]] = [:]
var clicks:[[UInt32]]=[]
var undefined:[[String:Any]]=[]
var initialisations:[[String:Any]]=[],errors:[[String:Any]]=[],polls:[String:Int]=[:],services:[UInt32:Int]=[:],opens:[String:Int]=[:],stages:[[String:Any]]=[]
var filingWindows:[[String:Any]]=[],filingIcons:[[String:Any]]=[]
var pinboardIcons:[[String:Any]]=[]
var soundRates:[[String:Any]]=[]
var streamClosePending=false
var pipeTraceCount:[UInt32:Int]=[:]
var utilityStates:[[String:Any]]=[],utilityBreaks:[UInt32:Int]=[:],utilityEntries:[UInt32]=[]
var ramUIReady=false,ramUIHandled=false
var ramFreeStates:[[String:Any]]=[]
var tracedTaskServices:Set<String>=[]
var tracedComponents:Set<String>=[]
var basicWindows:[[UInt32]]=[],basicMessages:[[String:Any]]=[],basicKeys:[UInt32]=[],basicFonts:[String]=[]
var alarmIcons:[[UInt32]]=[],alarmCodeSWIs:[[String:Any]]=[],alarmCode:[UInt8]=[],alarmCodeBase:UInt32=0,alarmCodeVerified=false,alarmCodeChangedWords:[Int]=[]
if target=="!Alarm" {alarmCode=[UInt8](try Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("alarm-code/Code")))}
var launchEvents:[[String:Any]]=[],swiCounts:[String:Int]=[:]
var shellCommands:[String]=[],shellMessages:[String]=[],shellScreens:[String:[String]]=[:]
func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical) ?? 0xffffffff}
func text(_ p:UInt32)->String {var b:[UInt8]=[];for i in 0..<256 {guard let v=m.memc.debugRead(p+UInt32(i),space:.logical),v>=32 else{break};b.append(v)};return String(bytes:b,encoding:.isoLatin1) ?? "?"}
func component(_ pc:UInt32)->String {modules.first {let b=($0["base"] as! NSNumber).uint32Value;return pc>=b && pc<b+($0["length"] as! NSNumber).uint32Value}?["component"] as? String ?? "Kernel"}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
func trace(_ name:String){let s=(d.trace?.last(100000) ?? []).map{"\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n"}.joined();try! s.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8)}
func check(_ b:Bool,_ s:String){if !b{trace("failure");json(["debug":d.log.map{"\($0.ticks): \($0.text)"},"failure":s,"pc":m.cpu.pc,"exceptions":m.cpu.exceptionCounts,"initialisations":initialisations,"errors":errors,"polls":polls,"text":m.screenText],"failure");fputs("FAIL: \(s)\n",stderr);exit(1)}}
m.cpu.swiObserver={pc,n in
 let swi=n & ~UInt32(0x20000),c=component(pc)
 if ["!Alarm","!Calc","!Configure"].contains(target) && c=="Kernel" {
  if swi==0x400c2 {alarmIcons.append((0..<9).map{word(m.cpu.r[1]+UInt32($0*4))})}
  // !RunImage loads Code with OS_File 16; R2 is its address in Alarm's slot.
  if swi==8 && m.cpu.r[0]==16 && text(m.cpu.r[1])=="Alarm:Code" {alarmCodeBase=m.cpu.r[2]}
 }
 // SWIs issued from Alarm's generated Code. While Alarm is paged in, confirm
 // the bytes there are exactly the generated Code.
 if target=="!Alarm" && alarmCodeBase>0 && !alarmCode.isEmpty && pc>=alarmCodeBase && pc<alarmCodeBase+UInt32(alarmCode.count) {
  // AlarmSrc keeps its table, text buffers and working variables inside the
  // block; the redraw writes them. Each executed SWI must be the generated
  // instruction at its offset, in a word the program has not changed. The
  // changed (data) words are recorded so cold boots can be compared.
  func fileWord(_ o:Int)->UInt32 {(0..<4).reduce(UInt32(0)){$0|UInt32(alarmCode[o+$1])<<UInt32(8*$1)}}
  let offset=Int(pc-alarmCodeBase)
  let changed=stride(from:0,to:alarmCode.count & ~3,by:4).filter{word(alarmCodeBase+UInt32($0)) != fileWord($0)}
  alarmCodeChangedWords=Array(Set(alarmCodeChangedWords+changed)).sorted()
  alarmCodeVerified=(alarmCodeSWIs.isEmpty || alarmCodeVerified) && word(pc)==fileWord(offset) && !changed.contains(offset)
  if alarmCodeSWIs.count<200 {alarmCodeSWIs.append(["offset":offset,"swi":swi])}
 }
 if ["!Chars","!Help","!Alarm","!Calc","!Configure"].contains(target) {
  if swi==0x400c5 && c=="Kernel" {basicWindows.append((0..<9).map{word(m.cpu.r[1]+UInt32($0*4))});json(basicWindows,"basic-windows")}
  if swi==0x40081 && c=="Kernel" {basicFonts.append(text(m.cpu.r[1]));json(basicFonts,"basic-fonts")}
  if swi==0x400dc && c=="Kernel" {basicKeys.append(m.cpu.r[0]);json(basicKeys,"basic-keys")}
  if swi==0x400e7 && [UInt32(0x502),0x503].contains(word(m.cpu.r[1]+16)) {
   let p=m.cpu.r[1];basicMessages.append(["component":c,"action":word(p+16),"reference":word(p+12),"recipient":m.cpu.r[2],"text":text(p+20)]);json(basicMessages,"basic-help-messages")
  }
 }
 if target=="!StrTest" {
  if streamClosePending {trace("stream-close-"+String(m.ticks));streamClosePending=false}
  if swi==0xd && m.cpu.r[0]==0 {streamClosePending=true}
  if c=="PipeFS" && swi==0x33 && [UInt32(6),7].contains(m.cpu.r[0]) {
   let reason=m.cpu.r[0];pipeTraceCount[reason,default:0]+=1
   if pipeTraceCount[reason]!<=3 {trace("pipe-upcall-"+String(m.ticks))}
  }
 }
 if target=="!MenuTest" && swi==2 && text(m.cpu.r[0])=="ARCLIBRE MENU CONTRACT FAIL" {check(false,"classic menu client assertion failure")}
 if target=="!MenuTest" && [UInt32(0x400d4),0x400e8].contains(swi) {trace("menu-call-\(swi)-\(m.ticks)")}
 if target=="!SqTest" && swi==2 {
  let marker=text(m.cpu.r[0])
  if marker=="ARCLIBRE SQUASH FAIL" {check(false,"Squash client assertion failure")}
  if marker.hasPrefix("ARCLIBRE SQUASH VECTOR ") {
   let fields=marker.split(separator:" ");let address=UInt32(fields[5],radix:16)!,length=Int(fields[6])!
   check(length>0 && length<=32000,"bounded compressed vector")
   try! Data((0..<length).map{m.memc.debugRead(address+UInt32($0),space:.logical)!}).write(to:out.appendingPathComponent("squash-"+fields[3]+"-"+fields[4]+".Z"))
   trace("squash-vector-"+fields[3]+"-"+fields[4])
  }
 }
 if target=="!UtilTest" && swi==2 {
  let marker=text(m.cpu.r[0])
  if marker=="ARCLIBRE UTILITY FAIL" {check(false,"utility client assertion failure")}
  if marker.hasPrefix("ARCLIBRE UTILITY ") {
   var state:[String:Any]=["marker":marker,"ticks":m.ticks,"palette":m.vidc.palette,"sound_bytes":m.vidc.soundBytesOutput,"sound_non_silent":m.vidc.soundBytesNonSilent,"psr":m.cpu.psr,"lit_pixels":m.currentFrame.pixels.filter{($0 & 0xffffff) != 0}.count]
   if modules.contains(where:{$0["component"] as? String=="ScrBlank"}) {
    let symbols=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("utility-runtime/modules/ScrBlank/symbols.json"))) as! [String:NSNumber]
    state["blanked"]=word(moduleWorkspace("ScrBlank")+symbols["Blanked"]!.uint32Value)
   }
   utilityStates.append(state);json(utilityStates,"utility-states");capture("utility-"+String(utilityStates.count),settle:false)
  }
  // Hardware input only, after recording the blank frame; no guest-state edits.
  if marker=="ARCLIBRE UTILITY SCREEN MOUSEBLANK" {m.mouseMove(dx:20,dy:-20)}
  if marker=="ARCLIBRE UTILITY SCREEN KEYBLANK" {m.keyDown(0x4c)}
  if marker=="ARCLIBRE UTILITY SCREEN KEYRESTORED" {m.keyUp(0x4c)}
  if marker=="ARCLIBRE UTILITY VOICES READY" {
   let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("utility-runtime/modules/StringLib/symbols.json"))) as! [String:NSNumber]
   let rows=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("utility-runtime/modules/StringLib/instructions.json"))) as! [[String:Any]]
   let image=syms["WorkSpaceImage"]!.uint32Value,end=syms["AmountToCopy"]!.uint32Value,base=moduleWorkspace("StringLib")
   let code=rows.filter{let off=($0["offset"] as! NSNumber).uint32Value;return off>=image && off<end}.map{row -> [String:UInt32] in let off=(row["offset"] as! NSNumber).uint32Value;return ["offset":off,"pc":base+off-image,"word":word(base+off-image)]}
   json(["base":base,"source_offset":image,"instructions":code],"string-ram-code")
   for name in ["GateOn1","GateOn2","GateOn3","GateOn4","Fill1","Fill2","Fill3","Fill4"] {
    let pc=base+syms[name]!.uint32Value-image
    if utilityBreaks[pc]==nil {utilityBreaks[pc]=try! d.addBreakpoint(.init(id:0,kind:.execute,start:pc)).id}
   }
  }
 }
 if target=="!RamTest" && swi==2 {
  let message=text(m.cpu.r[0])
  if message=="ARCLIBRE RAM UI READY" {
   let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Switcher/symbols.json"))) as! [String:NSNumber]
   let base=moduleWorkspace("Switcher")
   json(["filertaskhandle":word(base+syms["filertaskhandle"]!.uint32Value),"memoryupdated":word(base+syms["pollword"]!.uint32Value),"ramfsflag":m.memc.debugRead(base+syms["ramfsflag"]!.uint32Value,space:.logical)!,"task_count":taskCount()],"ram-taskmanager")
   ramUIReady=true
  }
  if message.hasPrefix("ARCLIBRE RAM FREE ") {
   let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("ram-filing-runtime/modules/Free/symbols.json"))) as! [String:NSNumber]
   let head=word(moduleWorkspace("Free")+syms["windows_ptr"]!.uint32Value)
   check(head>0 && head<0x4000000,"Free has a real window record")
   var values:[String:Any]=["marker":message,"node":head]
   for name in ["window_size_lo","window_size_hi","window_free_lo","window_free_hi","window_used_lo","window_used_hi","window_fs"] {values[name]=word(head+syms[name]!.uint32Value)}
   ramFreeStates.append(values);json(ramFreeStates,"ram-free-states")
  }
  if message.hasPrefix("ARCLIBRE RAM ") {trace("ram-marker-"+String(launchEvents.count))}
  if message=="ARCLIBRE RAM CONTRACT FAIL" {check(false,"RAM client assertion failure")}
 }
 if target=="!StrTest" && swi==2 {
  let message=text(m.cpu.r[0])
  if message.hasPrefix("ARCLIBRE ") || message.hasPrefix("closed a pipe") {trace("stream-marker-\(launchEvents.count)")}
  if message=="ARCLIBRE STREAM CONTRACT FAIL" {check(false,"stream client assertion failure")}
 }
 if target=="!StrTest" && swi==0x42740 {
  let data=try! Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("stream-app/device.bin"))
  streamDriver=["base":m.cpu.r[2],"workspace":m.cpu.r[4],"words":stride(from:0,to:data.count,by:4).map{word(m.cpu.r[2]+UInt32($0))}]
  json(streamDriver,"stream-driver")
 }
 if target=="!TaskTest" && swi==2 && text(m.cpu.r[0])=="ARCLIBRE TASK SERVICES FAIL" {check(false,"task client assertion failure")}
 if target=="!SndTest" && swi==2 && text(m.cpu.r[0]).hasPrefix("ARCLIBRE SOUND RATE ") {
  soundRates.append(["marker":text(m.cpu.r[0]),"channels":m.cpu.r[6],"period_us":m.cpu.r[7],"reported_period_us":m.cpu.r[9],"ticks":m.ticks,"sfr":m.vidc.sfr,"bytes":m.vidc.soundBytesOutput])
  json(soundRates,"sound-rates")
 }
 if !tracedComponents.contains(c) {tracedComponents.insert(c);trace("component-"+c)}
 swiCounts[String(format:"%06X",swi),default:0]+=1
 if [UInt32(5),2,0x24,0x400de].contains(swi) && launchEvents.count<1000 {
  launchEvents.append(["pc":pc,"swi":swi,"r0":m.cpu.r[0],"r1":m.cpu.r[1],"text":text(m.cpu.r[0]),"psr":m.cpu.psr])
  json(launchEvents,"launch-events")
 }
 if (actionTest || ["!Chars","!Help","!Alarm","!Calc","!Configure"].contains(target)) && [UInt32(0x400d4),0x400e3].contains(swi) && m.cpu.r[1] != 0xffffffff {
  let p=m.cpu.r[1];var items:[[String:Any]]=[]
  for i in 0..<30 {let q=p+28+UInt32(i*24),flags=word(q),iflags=word(q+8);items.append(["flags":flags,"submenu":word(q+4),"text":text(iflags&0x100 != 0 ? word(q+12):q+12)]);if flags&0x80 != 0 {break}}
  menus.append(["x":m.cpu.r[2],"y":m.cpu.r[3],"width":word(p+16),"height":word(p+20),"gap":word(p+24),"items":items]);json(menus,"menus")
 }
 if c=="Filter" || c=="TaskWindow" || (target=="!StrTest" && ["DeviceFS","SystemDevs","PipeFS"].contains(c)) {let key="task-service-\(c)-\(swi)";if tracedTaskServices.insert(key).inserted {trace(key)}}
 if c=="SpriteUtil" {trace("sprite-command-\(launchEvents.count)-\(swi)")}
 if c=="Obey" && swi==5 {trace("obey-command-\(launchEvents.count)")}
 if c=="ShellCLI" && swi==5 {shellCommands.append(text(m.cpu.r[0]));trace("shell-command-\(shellCommands.count)")}
 if c=="ShellCLI" && swi==2 {shellMessages.append(text(m.cpu.r[0]))}
 if ["!CAbiTest","!TaskTest","!StrTest","!RamTest","!UtilTest","!SqTest"].contains(target) && swi==2 && ["ARCLIBRE C ABI PASS","ARCLIBRE TASK SERVICES PASS","ARCLIBRE STREAM CONTRACT PASS","ARCLIBRE RAM CONTRACT PASS","ARCLIBRE UTILITY PASS","ARCLIBRE SQUASH PASS"].contains(text(m.cpu.r[0])) {clientVeneerWords=clientVeneerAddresses.map{["pc":$0,"word":word($0)]};json(clientVeneerWords,"client-veneers")}
 if swi==0x400c0{initialisations.append(["component":c,"name":text(m.cpu.r[2]),"psr":m.cpu.psr,"version":m.cpu.r[0]])}
 if swi==0x400df{errors.append(["component":c,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}
 if swi==0x400c7 || swi==0x400e1{polls[c,default:0]+=1}
 if swi==0x400c5 {
  opens[c,default:0]+=1
  if protectedTest {
   let h=word(m.cpu.r[1]) & ~UInt32(3)
   if word(h)==0x646e6957 && word(h+ws["w_nicons"]!["value"]!.uint32Value)==16 {
    let icons=word(h+ws["w_icons"]!["value"]!.uint32Value)
    let fields=(0..<16).map{i -> String in let p=icons+UInt32(i*32);return text(word(p+16)&0x100 != 0 ? word(p+20):p+20)}
    // Indirected text belongs to this task's current slot. Capture it while
    // that task calls Wimp, before another application is paged into the slot.
    if fields[7]=="Abort" {actionWindowTexts[h]=fields}
   }
  }
 }
 if swi==0x400c1 && c=="Filer" {let p=m.cpu.r[1];filingWindows.append(["title":text(word(p+72)),"definition":(0..<22).map{word(p+UInt32($0*4))}]);json(filingWindows,"filing-windows")}
 if dragTest && swi==0x400c2 && c=="Pinboard" {let p=m.cpu.r[1];pinboardIcons.append(["text":text(word(p+24)),"definition":(0..<9).map{word(p+UInt32($0*4))}]);json(pinboardIcons,"pinboard-icons")}
 if swi==0x400e2 && c=="Filer" {let p=m.cpu.r[1];filingIcons.append(["text":text(word(p+20)),"definition":(0..<8).map{word(p+UInt32($0*4))}]);json(filingIcons,"filing-icons")}
 if swi==0x30{services[m.cpu.r[1],default:0]+=1;if m.cpu.r[1]==0x4a{trace("startup-complete")}}
}
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
func run(_ ticks:UInt64){let end=m.ticks+ticks;if d.isStopped {d.resume()};while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2400000),maxInstructions:300000)
 if d.isStopped {
  if let id=utilityBreaks[m.cpu.pc] {
   utilityEntries.append(m.cpu.pc);json(utilityEntries,"string-entries");trace("string-entry-"+String(utilityEntries.count));_=d.removeBreakpoint(id);utilityBreaks.removeValue(forKey:m.cpu.pc)
  } else if pipeReturn>0 && m.cpu.pc==pipeReturn {
   pipeReturns.append(["ticks":m.ticks,"psr":m.cpu.psr,"r0":m.cpu.r[0],"r1":m.cpu.r[1],"number":word(m.cpu.r[0]),"error":text(m.cpu.r[0]+4)])
   json(pipeReturns,"pipe-close-upcalls");trace("pipe-close-return-"+String(pipeReturns.count))
  } else if actionTest && m.cpu.pc==actionReturn {
   actionReturns.append(["psr":m.cpu.psr,"registers":(0..<15).map{m.cpu.r[$0]},"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])]);json(actionReturns,"action-returns");trace("action-return")
  } else if target=="!Zarch" && m.cpu.pc==0xdba8 {
   gameEntries.append([m.cpu.psr]+(0..<15).map{m.cpu.r[$0]});json(gameEntries,"game-entry")
  } else if target=="!Zarch" && m.cpu.pc>=0x8000 && m.cpu.pc<=0x84e7 {
   if let previous=loaderInstructions.last, previous[1]&0x0f000000==0x0f000000 && m.cpu.psr&0x10000000 != 0 {
    loaderErrors.append(["swi_pc":previous[0],"swi":previous[1]&0xffffff,"error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])]);json(loaderErrors,"loader-errors")
   }
   loaderInstructions.append([m.cpu.pc,word(m.cpu.pc),m.cpu.psr]+(0..<15).map{m.cpu.r[$0]})
   if loaderInstructions.count>=10000, let id=loaderBreakpointID{_=d.removeBreakpoint(id)}
  } else if m.cpu.pc==filerClick {
   clicks.append((0..<6).map{word(m.cpu.r[1]+UInt32($0*4))});json(clicks,"mouse-events")
  } else if m.cpu.pc==welcomeBoundary {
   capture("welcome",settle:false);_=d.removeBreakpoint(welcomeBreakpoint.id)
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
 if target=="!RamTest" && ramUIReady && !ramUIHandled {return}
 };check(errors.isEmpty,"desktop error: \(errors)")}
func moduleWorkspace(_ c:String)->UInt32 {var node=word(2000);let base=(modules.first{$0["component"] as! String==c}!["base"] as! NSNumber).uint32Value
 for _ in 0..<(modules.count+1) {if node==0{break};if word(node+4)==base{return word(word(node+12)+4)};node=word(node)};return 0xffffffff}
func taskCount()->UInt32 {let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("wimp-stack/modules/Wimp/symbols.json"))) as! [String:[String:NSNumber]];let base=moduleWorkspace("Wimp");return base==0xffffffff ? 0:word(base+syms["taskcount"]!["value"]!.uint32Value)}
func reportedTotal()->UInt32 {let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.deletingLastPathComponent().appendingPathComponent("desktop-startup/modules/Switcher/symbols.json"))) as! [String:NSNumber]
 var node=word(moduleWorkspace("Switcher")+syms["wlink"]!.uint32Value)
 for _ in 0..<100 {if node==0 || node==0xffffffff{break};if m.memc.debugRead(node+syms["icb_icon1"]!.uint32Value,space:.logical)==UInt8(syms["ic_totalname"]!.uint32Value){return word(node+syms["icb_memsize"]!.uint32Value)};node=word(node+syms["icb_link"]!.uint32Value)};return 0xffffffff}
// VDU output may be redirected into a sprite at the instant of capture; let the
// guest finish that plotting so the dump below reads the real display memory.
// Captures taken inside the SWI observer or run loop cannot advance the machine.
func capture(_ name:String,settle:Bool=true){
 var waited=0;while settle && word(0x10c0) != word(0x1190) && waited<200 {run(240_000);waited+=1}
 check(word(0x10c0)==word(0x1190),"VDU output is on the screen for capture \(name)");trace(name);let f=m.currentFrame;check(writePNG(f,to:out.appendingPathComponent(name+".png")),"PNG");let screen=word(0x10c0),line=word(0x1088);let b=(0..<Int(line)*256).map{m.memc.debugRead(screen+UInt32($0),space:.logical)!};try! Data(b).write(to:out.appendingPathComponent(name+"-screen.bin"));stages.append(["name":name,"ticks":m.ticks,"task_count":taskCount(),"polls":polls,"opens":opens,"palette":m.vidc.palette,"sound":m.vidc.soundSummary,"sound_dma_enabled":m.memc.soundDMAEnabled,"sound_mapping":[m.memc.debugTranslate(0x1f06000) ?? 0,m.memc.debugTranslate(0x1f07000) ?? 0],"line_length":line,"pc":m.cpu.pc,"psr":m.cpu.psr]);json(stages,"stages")}
check(m.cpu.pc==0 && m.cpu.psr==0x0c000003,"real reset vector")
run(24_000_000*35);capture("desktop")
check(taskCount()==desktopTasks,"four desktop tasks")
func move(_ x:Int,_ y:Int){m.mouseMove(dx:(x-Int(word(1452)))/2,dy:(y-Int(word(1456)))/2);run(4_800_000)}
func select(){m.keyDown(0x70);run(960_000);m.keyUp(0x70);run(960_000)}
move(64,60);select();run(24_000_000*5);capture("disc-open")
check(!filingWindows.isEmpty,"floppy opens in Filer")
guard let icon=filingIcons.last(where:{$0["text"] as? String==target})?["definition"] as? [UInt32] else{check(false,"application icon not drawn: \(target)");exit(1)}
let w=filingWindows.last!["definition"] as! [UInt32]
let x=Int(Int32(bitPattern:w[0]))+(Int(Int32(bitPattern:icon[0]))+Int(Int32(bitPattern:icon[2])))/2-Int(Int32(bitPattern:w[4]))
let y=Int(Int32(bitPattern:w[3]))+(Int(Int32(bitPattern:icon[1]))+Int(Int32(bitPattern:icon[3])))/2-Int(Int32(bitPattern:w[5]))
json(["double_click_centiseconds":word(moduleWorkspace("Wimp")+ws["doubleclick_timelimit"]!["value"]!.uint32Value),"move_limit":m.memc.debugRead(moduleWorkspace("Wimp")+ws["doubleclick_movelimit"]!["value"]!.uint32Value,space:.logical)!,"buttons":word(1428)],"input-settings")
let soundBeforeLaunch=m.vidc.soundBytesNonSilent
move(x,y)
func menuBounds()->[Int] {
 let handle=word(moduleWorkspace("Wimp")+ws["menuhandle"]!["value"]!.uint32Value) & ~UInt32(3)
 return (0..<4).map {Int(Int32(bitPattern:word(handle+ws["w_wax0"]!["value"]!.uint32Value+UInt32($0*4))))}
}
if deleteTest {
 select();m.keyDown(0x71);run(960_000);m.keyUp(0x71);run(24_000_000);capture("file-menu")
 check(!menus.isEmpty,"file menu opened")
 // Continue from the actual menu geometry rather than fixed screen pixels.
 let menu=menus.last!,mh=Int(menu["height"] as! UInt32),mg=Int(menu["gap"] as! UInt32)
 let bounds=menuBounds();json(bounds,"menu-bounds");move(bounds[2]-16,bounds[3]-(mh+mg)-mh/2);run(24_000_000);capture("file-submenu")
 json(menus,"menus")
 check(word(moduleWorkspace("Wimp")+ws["menuSP"]!["value"]!.uint32Value)>=4,"file submenu opened")
 let p=((menu["items"] as! [[String:Any]])[1]["submenu"] as! UInt32)
 let sh=Int(word(p+20)),sg=Int(word(p+24));var items:[[String:Any]]=[]
 for i in 0..<30 {let q=p+28+UInt32(i*24),flags=word(q);items.append(["text":text(word(q+8)&0x100 != 0 ? word(q+12):q+12)]);if flags&0x80 != 0 {break}}
 guard let index=items.firstIndex(where:{$0["text"] as? String=="Delete"}) else{check(false,"Delete menu item exists");exit(1)}
 let sb=menuBounds();move(sb[0]+60,sb[3]-index*(sh+sg)-sh/2);select();run(24_000_000*20);capture("delete-completed")
 try Data(disc.mergedImage()).write(to:out.appendingPathComponent("copied.adf"))
 check(disc.isModified,"desktop delete writes media")
 check(taskCount()==desktopTasks,"delete task exits back to desktop")
} else if actionTest {
 guard let dest=filingIcons.last(where:{$0["text"] as? String=="Dest"})?["definition"] as? [UInt32] else{check(false,"destination folder drawn");exit(1)}
 let dx=Int(Int32(bitPattern:w[0]))+(Int(Int32(bitPattern:dest[0]))+Int(Int32(bitPattern:dest[2])))/2-Int(Int32(bitPattern:w[4]))
 let dy=Int(Int32(bitPattern:w[3]))+(Int(Int32(bitPattern:dest[1]))+Int(Int32(bitPattern:dest[3])))/2-Int(Int32(bitPattern:w[5]))
 // This historical Filer copies between open viewers, not onto a folder
 // icon in the source viewer. Open Dest and move its window aside first.
 move(dx,dy);select();select();run(24_000_000*3)
 check(filingWindows.count>=2,"destination viewer opens")
 let dw=filingWindows.last!["definition"] as! [UInt32]
 let wx=Int(Int32(bitPattern:dw[0])),wy=Int(Int32(bitPattern:dw[3]))
 move(wx+100,wy+20);m.keyDown(0x70);run(2_400_000);m.mouseMove(dx:300,dy:-60);run(24_000_000);m.keyUp(0x70);run(24_000_000);capture("copy-viewers")
 if moveTest {m.keyDown(0x4c);run(960_000)}
 move(x,y);m.keyDown(0x70);run(2_400_000);m.mouseMove(dx:20,dy:-20);run(24_000_000);capture("copy-drag")
 move(wx+700,wy-180);m.keyUp(0x70);if moveTest {m.keyUp(0x4c)};run(24_000_000*25);capture("copy-completed")
 json(initialisations,"initialisations")
 try Data(disc.mergedImage()).write(to:out.appendingPathComponent("copied.adf"))
 check(initialisations.contains{($0["name"] as? String)=="Filer Action Window"},"FilerAct creates real Wimp task through library")
 if protectedTest {
  func iconPointer(_ handle:UInt32,_ index:Int)->UInt32 {word(handle+ws["w_icons"]!["value"]!.uint32Value) &+ UInt32(index*32)}
  guard let h=actionWindowTexts.keys.first(where:{actionWindowTexts[$0]![12].lowercased().contains("protected")}) else {json(actionWindowTexts.map{["handle":$0.key,"fields":$0.value]},"error-windows");check(false,"real write-protection error displayed");exit(1)}
  json(["text":actionWindowTexts[h]![12]],"protected-error");capture("write-protected")
  check(!disc.isModified,"protected medium stays untouched")
  let ip=iconPointer(h,7),ix=(Int(Int32(bitPattern:word(ip)))+Int(Int32(bitPattern:word(ip+8))))/2,iy=(Int(Int32(bitPattern:word(ip+4)))+Int(Int32(bitPattern:word(ip+12))))/2
  let wx=Int(Int32(bitPattern:word(h+ws["w_wax0"]!["value"]!.uint32Value))),wy=Int(Int32(bitPattern:word(h+ws["w_way1"]!["value"]!.uint32Value))),sx=Int(Int32(bitPattern:word(h+ws["w_scx"]!["value"]!.uint32Value))),sy=Int(Int32(bitPattern:word(h+ws["w_scy"]!["value"]!.uint32Value)))
  move(wx+ix-sx,wy+iy-sy);select();run(24_000_000*3);capture("protected-aborted")
 } else {check(disc.isModified,"desktop copy writes media")}
 check(taskCount()==desktopTasks,"copy task exits back to desktop")
} else if dragTest {
 m.keyDown(0x70);run(2_400_000);m.mouseMove(dx:40,dy:-40);run(24_000_000);capture("dragging")
 m.mouseMove(dx:160,dy:-60);run(24_000_000);capture("drag-moved")
 m.keyUp(0x70);run(24_000_000*3);capture("dropped")
 check(swiCounts["042400",default:0]>0 && swiCounts["042401",default:0]>0,"real DragASprite start and stop")
 check(taskCount()==desktopTasks,"desktop survives drag and pinboard drop")
 check(pinboardIcons.contains{($0["text"] as? String)==target},"Pinboard creates application shortcut")
 select();select();run(24_000_000*15);capture("shortcut-application")
 check(launchEvents.contains{($0["swi"] as? UInt32)==2 && ($0["text"] as? String)=="ARCLIBRE DOUBLE CLICK APPLICATION EXECUTED"},"dropped Pinboard shortcut launches actual application")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("returned")
 check(taskCount()==desktopTasks,"application returns to desktop after shortcut launch")
} else {select();select();run(24_000_000*15);capture("application")}

if ["!Chars","!Help"].contains(target) {
 check(initialisations.contains{($0["name"] as? String)==(target=="!Chars" ? "Characters":"Help")},"original BASIC application initialises Wimp")
 check(errors.isEmpty,"BASIC utility starts without errors")
 check(taskCount()==desktopTasks+1,"BASIC utility owns a real desktop task")
 check(!basicWindows.isEmpty,"BASIC utility opens its real window")
 capture("basic-utility-open")
 func signed(_ p:UInt32)->Int {Int(Int32(bitPattern:word(p)))}
 // OS_Byte 161/162 address n is clock-chip RAM n+&40 (n<&C0) or n-&B0.
 func cm(_ n:Int)->UInt8 {m.cmos[n<0xc0 ? n+0x40:n-0xb0]}
 if target=="!Chars" {
  let h=basicWindows.last![0] & ~UInt32(3),wx=signed(h+ws["w_wax0"]!["value"]!.uint32Value),wy=signed(h+ws["w_way1"]!["value"]!.uint32Value)
  // Original Chars has 32 columns, 24x44 OS-unit cells and 16-unit margins.
  move(wx+48,wy-120);select();run(24_000_000)
  check(basicKeys.contains(65),"Select emits character A through Wimp_ProcessKey")
  move(wx+72,wy-120);m.keyDown(0x4c);run(24_000_000);m.keyUp(0x4c);run(24_000_000)
  check(basicKeys.contains(66),"Shift emits character B through Wimp_ProcessKey")
  m.keyDown(0x71);run(960_000);m.keyUp(0x71);run(24_000_000);capture("chars-font-menu")
  check(!menus.isEmpty,"Chars opens original font menu")
  let menu=menus.last!,items=menu["items"] as! [[String:Any]]
  guard let index=items.firstIndex(where:{$0["text"] as? String=="WIMPSymbol"}) else {check(false,"installed outline font appears in Chars menu");exit(1)}
  let b=menuBounds(),height=Int(menu["height"] as! UInt32),gap=Int(menu["gap"] as! UInt32)
  let paintsBefore=swiCounts["040086",default:0]
  move(b[0]+40,b[3]-index*(height+gap)-height/2);select();run(24_000_000*3);capture("chars-outline-font")
  check(basicFonts.contains("\\FWIMPSymbol") && swiCounts["040086",default:0]>paintsBefore,"Chars finds and paints a real outline font")
  check(errors.isEmpty,"Chars font change has no error")
  move(wx+52,wy+20);select();run(24_000_000*2);capture("chars-closed")
  check(taskCount()==desktopTasks,"Chars close box terminates its task")
 } else {
  move(64,60);run(24_000_000*3);capture("help-floppy")
  check(basicMessages.contains{($0["action"] as? UInt32)==0x502},"Help sends real HelpRequest messages")
  check(basicMessages.contains{($0["action"] as? UInt32)==0x503 && ($0["component"] as? String)=="Filer"},"Filer sends real HelpReply text")
  func quitHelp(){
   let bar=word(moduleWorkspace("Wimp")+ws["iconbarhandle"]!["value"]!.uint32Value) & ~UInt32(3),n=word(bar+ws["w_nicons"]!["value"]!.uint32Value),icons=word(bar+ws["w_icons"]!["value"]!.uint32Value)
   var hp:UInt32=0
   for i in 0..<n {let p=icons+i*32;if text(word(p+16)&0x100 != 0 ? word(p+20):p+20).lowercased()=="!help" {hp=p;break}}
   check(hp != 0,"Help owns its icon-bar sprite")
   move(signed(bar+ws["w_wax0"]!["value"]!.uint32Value)+(signed(hp)+signed(hp+8))/2-signed(bar+ws["w_scx"]!["value"]!.uint32Value),signed(bar+ws["w_way1"]!["value"]!.uint32Value)+(signed(hp+4)+signed(hp+12))/2-signed(bar+ws["w_scy"]!["value"]!.uint32Value))
   m.keyDown(0x71);run(960_000);m.keyUp(0x71);run(24_000_000);capture("help-menu")
   guard let menu=menus.last,let items=menu["items"] as? [[String:Any]],let index=items.firstIndex(where:{$0["text"] as? String=="Quit"}) else {check(false,"Help Quit menu item");return}
   let b=menuBounds(),height=Int(menu["height"] as! UInt32),gap=Int(menu["gap"] as! UInt32)
   move(b[0]+40,b[3]-index*(height+gap)-height/2);select();run(24_000_000*2)
   check(taskCount()==desktopTasks,"Help Quit removes its task")
  }
  quitHelp();capture("help-quit")
  move(x,y);select();select();run(24_000_000*5)
  check(initialisations.filter{($0["name"] as? String)=="Help"}.count==2 && taskCount()==desktopTasks+1,"Help restarts after clearing Help$Dir")
  check(errors.isEmpty,"Help restart has no stale-running error")
  quitHelp();capture("help-restarted-and-quit")
 }
}
if target=="!Alarm" {
 func signed(_ p:UInt32)->Int {Int(Int32(bitPattern:word(p)))}
 func field(_ n:String)->UInt32 {ws[n]!["value"]!.uint32Value}
 func title(_ h:UInt32)->String {word(h+field("w_titleflags"))&0x100 != 0 ? text(word(h+field("w_title"))):text(h+field("w_title"))}
 func iconText(_ p:UInt32)->String {word(p+16)&0x100 != 0 ? text(word(p+20)):text(p+20)}
 func iconCentre(_ h:UInt32,_ p:UInt32)->(Int,Int) {(signed(h+field("w_wax0"))+(signed(p)+signed(p+8))/2-signed(h+field("w_scx")),signed(h+field("w_way1"))+(signed(p+4)+signed(p+12))/2-signed(h+field("w_scy")))}
 func icons(_ h:UInt32)->[UInt32] {let n=word(h+field("w_nicons")),base=word(h+field("w_icons"));return (0..<n).map{base+$0*32}}
 func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
 func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
 func window(_ name:String)->UInt32? {basicWindows.reversed().map{$0[0] & ~UInt32(3)}.first{title($0)==name}}
 // The clock chip's registers only refresh when the guest reads them; derive
 // its current time of day from its epoch and emulated time instead.
 func rtcMinutes()->Int {Int(((m.rtc.epochSeconds+Int64(m.ticks/24_000_000))%86400)/60)}
 check(initialisations.contains{($0["name"] as? String)=="Alarm"},"original Alarm initialises Wimp")
 check(errors.isEmpty,"Alarm starts without errors")
 check(taskCount()==desktopTasks+1,"Alarm owns a real desktop task")
 // Its icon-bar clock: the bar icon whose data words are those Alarm created.
 let bar=word(moduleWorkspace("Wimp")+field("iconbarhandle")) & ~UInt32(3)
 func clockIcon()->UInt32 {
  guard let created=alarmIcons.last(where:{Int32(bitPattern:$0[0])<0}),let icon=icons(bar).first(where:{p in (0..<3).allSatisfy{word(p+20+UInt32($0*4))==created[6+$0]}}) else {check(false,"Alarm creates its icon-bar clock");exit(1)}
  return icon
 }
 _=clockIcon()
 capture("alarm-iconbar")
 check(alarmCodeBase>0,"Alarm loads its generated Code with OS_File")
 // Lifecycle: Quit from the icon-bar menu (nothing to save), then restart.
 func choose(_ item:String) {
  let (x,y)=iconCentre(bar,clockIcon());move(x,y);m.keyDown(0x71);run(960_000);m.keyUp(0x71);run(24_000_000)
  guard let menu=menus.last,let items=menu["items"] as? [[String:Any]],let index=items.firstIndex(where:{$0["text"] as? String==item}) else {check(false,"Alarm menu has \(item)");exit(1)}
  let b=menuBounds(),height=Int(menu["height"] as! UInt32),gap=Int(menu["gap"] as! UInt32)
  move(b[0]+40,b[3]-index*(height+gap)-height/2);select();run(24_000_000*3)
 }
 choose("Quit");capture("alarm-quit")
 check(taskCount()==desktopTasks,"Alarm Quit removes its task")
 // From a floppy, Alarm reads !RunImage, Code, Messages and Templates
 // before it creates its clock: wait (bounded) for that real icon.
 let iconsBefore=alarmIcons.count
 move(x,y);select();select();run(24_000_000*8)
 for _ in 0..<30 where !alarmIcons.dropFirst(iconsBefore).contains(where:{Int32(bitPattern:$0[0])<0}) {run(24_000_000)}
 check(initialisations.filter{($0["name"] as? String)=="Alarm"}.count==2 && taskCount()==desktopTasks+1,"Alarm restarts after Quit")
 check(errors.isEmpty,"Alarm restart has no error")
 // Set an alarm two minutes ahead through the real Set alarm window.
 let (cx,cy)=iconCentre(bar,clockIcon());move(cx,cy);select();run(24_000_000*2)
 guard let set=window("Set alarm") else {check(false,"Select on the clock opens Set alarm");exit(1)}
 capture("alarm-set-window")
 let setIcons=icons(set)
 guard let timeIcon=setIcons.first(where:{iconText($0).hasSuffix(" am") || iconText($0).hasSuffix(" pm")}) else {check(false,"Set alarm shows a time");exit(1)}
 let before=iconText(timeIcon),row=(signed(timeIcon+4)+signed(timeIcon+12))/2
 // Right of the time are the minute arrows and Save; the right-most arrow adds a minute.
 guard let minuteUp=setIcons.filter({p in iconText(p) != "Save" && abs((signed(p+4)+signed(p+12))/2-row)<8 && signed(p)>signed(timeIcon+8)}).max(by:{signed($0)<signed($1)}) else {check(false,"minute arrow");exit(1)}
 for _ in 0..<2 {let (x,y)=iconCentre(set,minuteUp);move(x,y);select();run(24_000_000)}
 // The alarm's minute is what the window now shows, e.g. "12:02 am".
 func minutes(_ t:String)->Int {let f=t.split(whereSeparator:{$0==":" || $0==" "});let h=Int(f[0])!%12,mm=Int(f[1])!;return (f[2]=="pm" ? 12:0)*60+h*60+mm}
 let due=minutes(iconText(timeIcon))
 check(due==minutes(before)+2,"two minute-arrow clicks advance the alarm by two minutes")
 check(due>rtcMinutes(),"alarm is set in the future")
 guard let message=setIcons.first(where:{(word($0+16)>>12)&15==15}) else {check(false,"writable message field");exit(1)}
 let (mx,my)=iconCentre(set,message);move(mx,my);select();type("ArcLibre alarm test")
 guard let save=setIcons.first(where:{iconText($0)=="Save"}) else {check(false,"Save button");exit(1)}
 let soundBefore=m.vidc.soundBytesNonSilent,setTime=rtcMinutes()
 let (sx,sy)=iconCentre(set,save);move(sx,sy);select();run(24_000_000*2)
 check(window("Attention!")==nil,"future alarm is not delivered early")
 var deliveredAt = -1
 while deliveredAt<0 && rtcMinutes()<=due+1 {run(24_000_000*5);if window("Attention!") != nil {deliveredAt=rtcMinutes()}}
 capture("alarm-delivered")
 guard deliveredAt>=0,let attention=window("Attention!") else {check(false,"alarm delivered within a minute of its time");exit(1)}
 check(deliveredAt>=due,"alarm is not delivered before its minute")
 check(icons(attention).contains{iconText($0).contains("ArcLibre alarm test")},"Attention window shows the alarm message")
 // Alarm beeps (VDU 7) from its idle loop while the alarm is sounding.
 var waited=0;while m.vidc.soundBytesNonSilent<=soundBefore && waited<10 {run(24_000_000);waited+=1}
 check(m.vidc.soundBytesNonSilent>soundBefore,"alarm sounds through real DMA")
 // The browser's redraw runs the generated Code.
 let codeBefore=alarmCodeSWIs.count
 choose("Alarms...");capture("alarm-browser")
 json(["code_base":alarmCodeBase,"verified":alarmCodeVerified,"swis_before":codeBefore,"swis":alarmCodeSWIs.count,"code_bytes":alarmCode.count,"run_time_data_words":alarmCodeChangedWords],"alarm-code-state")
 check(alarmCodeSWIs.count>codeBefore && alarmCodeVerified,"browser redraw executes Alarm's exact generated Code")
 json(["set_time_minutes":setTime,"due_minutes":due,"delivered_minutes":deliveredAt,"code_base":alarmCodeBase,"code_swis":alarmCodeSWIs,"windows":basicWindows.map{title($0[0] & ~UInt32(3))}],"alarm-observations")
}
if target=="!Calc" {
 func signed(_ p:UInt32)->Int {Int(Int32(bitPattern:word(p)))}
 func field(_ n:String)->UInt32 {ws[n]!["value"]!.uint32Value}
 func title(_ h:UInt32)->String {word(h+field("w_titleflags"))&0x100 != 0 ? text(word(h+field("w_title"))):text(h+field("w_title"))}
 func iconText(_ p:UInt32)->String {word(p+16)&0x100 != 0 ? text(word(p+20)):text(p+20)}
 func iconCentre(_ h:UInt32,_ p:UInt32)->(Int,Int) {(signed(h+field("w_wax0"))+(signed(p)+signed(p+8))/2-signed(h+field("w_scx")),signed(h+field("w_way1"))+(signed(p+4)+signed(p+12))/2-signed(h+field("w_scy")))}
 func icons(_ h:UInt32)->[UInt32] {let n=word(h+field("w_nicons")),base=word(h+field("w_icons"));return (0..<n).map{base+$0*32}}
 func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
 func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(4_800_000)}
 check(initialisations.contains{($0["name"] as? String)=="Calculator"},"Calc initialises Wimp as Calculator")
 check(errors.isEmpty && taskCount()==desktopTasks+1,"Calc owns a real desktop task without errors")
 let bar=word(moduleWorkspace("Wimp")+field("iconbarhandle")) & ~UInt32(3)
 guard let created=alarmIcons.first(where:{Int32(bitPattern:$0[0]) == -1}),let icon=icons(bar).first(where:{p in iconText(p)=="!calc" && (0..<3).allSatisfy{word(p+20+UInt32($0*4))==created[6+$0]}}) else {check(false,"Calc puts its !calc icon on the right of the icon bar");exit(1)}
 let (bx,by)=iconCentre(bar,icon);move(bx,by);select();run(24_000_000*2)
 guard let win=basicWindows.reversed().map({$0[0] & ~UInt32(3)}).first(where:{title($0)=="Calculator"}) else {check(false,"Select on the icon opens the Calculator window");exit(1)}
 capture("calc-window")
 // 3.11 furniture: Back, Close and title only; no toggle, scroll bars or resize.
 check(word(win+field("w_flags")) & 0x7F000000 == 0x07000000,"Calculator has only Back, Close and title")
 let all=icons(win),display=all[0]
 func key(_ label:String)->UInt32 {all.first{iconText($0)==label}!}
 func colours(_ label:String)->(UInt32,UInt32) {let f=word(key(label)+16);return ((f>>24)&15,f>>28)}
 check(colours("C")==(12,11) && colours("7")==(7,3) && colours(".")==(7,2) && colours("=")==(7,12) && colours("+")==(7,12) && colours("\u{F7}")==(7,12),"key colours match 3.11")
 func tap(_ label:String){let (x,y)=iconCentre(win,key(label));move(x,y);select();run(2_400_000)}
 func shown()->String {iconText(display)}
 check(shown()=="0","display starts at 0")
 for k in ["1","2","+","3","="] {tap(k)};let sum=shown()
 type("7*6\n");let product=shown()
 for k in ["2","+","3","x","4","="] {tap(k)};let chained=shown()
 tap("9");tap("\u{F7}");tap("0");tap("=");let error=shown()
 tap("5");let stillError=shown()
 tap("C");let cleared=shown()
 type("8");press(0x34);run(2_400_000);let deleted=shown()
 capture("calc-used")
 check(sum=="15" && product=="42" && chained=="20","four-function arithmetic by click and keyboard")
 check(error=="Error" && stillError=="Error" && cleared=="0" && deleted=="0","division by zero shows Error until C; Delete clears")
 json(["sum":sum,"product":product,"chained":chained,"error":error,"cleared":cleared,"deleted":deleted,"icons":all.map{iconText($0)}],"calc-observations")
 move(bx,by);m.keyDown(0x71);run(960_000);m.keyUp(0x71);run(24_000_000)
 guard let menu=menus.last,let items=menu["items"] as? [[String:Any]],let quit=items.firstIndex(where:{$0["text"] as? String=="Quit"}) else {check(false,"Calc menu has Quit");exit(1)}
 let b=menuBounds(),height=Int(menu["height"] as! UInt32),gap=Int(menu["gap"] as! UInt32)
 move(b[0]+40,b[3]-quit*(height+gap)-height/2);select();run(24_000_000*3);capture("calc-quit")
 check(taskCount()==desktopTasks,"Quit removes the Calculator task")
}
if target=="!Configure" {
 // OS_Byte 161/162 address n is clock-chip RAM n+&40 (n<&C0) or n-&B0.
 func cm(_ n:Int)->UInt8 {m.cmos[n<0xc0 ? n+0x40:n-0xb0]}
 func signed(_ p:UInt32)->Int {Int(Int32(bitPattern:word(p)))}
 func field(_ n:String)->UInt32 {ws[n]!["value"]!.uint32Value}
 func title(_ h:UInt32)->String {word(h+field("w_titleflags"))&0x100 != 0 ? text(word(h+field("w_title"))):text(h+field("w_title"))}
 func iconText(_ p:UInt32)->String {word(p+16)&0x100 != 0 ? text(word(p+20)):text(p+20)}
 func validation(_ p:UInt32)->String {word(p+16)&0x101==0x101 && Int32(bitPattern:word(p+24)) > 0 ? text(word(p+24)):""}
 func iconCentre(_ h:UInt32,_ p:UInt32)->(Int,Int) {(signed(h+field("w_wax0"))+(signed(p)+signed(p+8))/2-signed(h+field("w_scx")),signed(h+field("w_way1"))+(signed(p+4)+signed(p+12))/2-signed(h+field("w_scy")))}
 func icons(_ h:UInt32)->[UInt32] {let n=word(h+field("w_nicons")),base=word(h+field("w_icons"));return (0..<n).map{base+$0*32}}
 func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
 func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(4_800_000)}
 func clearField(){m.keyDown(0x3b);press(ArcKey.forCharacter("u")!.0);m.keyUp(0x3b);run(720_000)}
 func window(_ name:String)->UInt32? {basicWindows.reversed().map{$0[0] & ~UInt32(3)}.first{title($0)==name}}
 // BASIC on an ARM2 takes up to a second to refresh a full window.
 func tap(_ h:UInt32,_ p:UInt32){let (x,y)=iconCentre(h,p);move(x,y);select();run(24_000_000)}
 func labelled(_ h:UInt32,_ s:String)->UInt32 {guard let p=icons(h).first(where:{iconText($0)==s}) else {check(false,"icon \(s) in \(title(h))");exit(1)};return p}
 // The control of a value row: the icon with this validation level with the label.
 func rowIcon(_ h:UInt32,_ label:String,_ v:String,_ nth:Int=0)->UInt32 {
  let l=labelled(h,label),row=(signed(l+4)+signed(l+12))/2
  let c=icons(h).filter{p in validation(p)==v && abs((signed(p+4)+signed(p+12))/2-row)<8 && signed(p)>=signed(l)}.sorted{signed($0)<signed($1)}
  check(c.count>nth,"\(v) control beside \(label)");return c[nth]
 }
 func rowField(_ h:UInt32,_ label:String)->String {let l=rowIcon(h,label,"Sleft"),row=(signed(l+4)+signed(l+12))/2
  return iconText(icons(h).first{p in word(p+16)&4 != 0 && validation(p)=="" && abs((signed(p+4)+signed(p+12))/2-row)<8 && signed(p)>signed(l)}!)}
 // The top-most icon with this validation (the first group's control).
 func topIcon(_ h:UInt32,_ v:String)->UInt32 {guard let p=icons(h).filter({validation($0)==v}).max(by:{signed($0+12)<signed($1+12)}) else {check(false,"\(v) in \(title(h))");exit(1)};return p}
 func closeWindow(_ h:UInt32){move(signed(h+field("w_wax0"))+58,signed(h+field("w_way1"))+20);json(["window":[signed(h+field("w_wax0")),signed(h+field("w_way1"))],"pointer":[word(1452),word(1456)]],"configure-close");select();run(9_600_000)}
 check(initialisations.contains{($0["name"] as? String)=="Configure"},"Configure initialises Wimp as Configure")
 check(errors.isEmpty && taskCount()==desktopTasks+1,"Configure owns a real desktop task without errors")
 // 3.11: double-clicking installs an icon on the icon bar and opens no window.
 check(basicWindows.isEmpty,"starting Configure opens no window")
 let bar=word(moduleWorkspace("Wimp")+field("iconbarhandle")) & ~UInt32(3)
 guard let created=alarmIcons.first(where:{Int32(bitPattern:$0[0]) == -1}),let icon=icons(bar).first(where:{p in iconText(p)=="!configure" && (0..<3).allSatisfy{word(p+20+UInt32($0*4))==created[6+$0]}}) else {check(false,"Configure puts its !configure icon on the right of the icon bar");exit(1)}
 let (bx,by)=iconCentre(bar,icon);move(bx,by);select();run(24_000_000*2)
 guard let main=window("Configuration") else {check(false,"Select on the icon opens the Configuration window");exit(1)}
 capture("configure-main")
 check(word(main+field("w_flags")) & 0x7F000000 == 0x07000000,"Configuration has only Back, Close and title")
 let sections=["Discs","Floppies","Net","Printer","Mouse","Keyboard","Memory","Sound","Screen","Fonts","Windows","Applications"]
 let mainIcons=icons(main)
 check(mainIcons.map(iconText)==sections,"the twelve 3.11 sections in order")
 check(mainIcons.enumerated().allSatisfy{(i,p) in (word(p+16)&0x400000 != 0)==(i==2 && !netTest) && word(p+16)&3==3},"sprite-and-text section icons; Net shaded without NetFS")
 // Positions now, while Configure is paged in: indirected text is in its slot.
 var sectionAt:[String:(Int,Int)]=[:];for (s,p) in zip(sections,mainIcons) {sectionAt[s]=iconCentre(main,p)}
 if netTest {
  // The Net window on station 1: servers through NetFS's and NetPrint's own
  // *Configure FS / PS, shown from CMOS RAM; options write their CMOS bits.
  let (nx,ny)=sectionAt["Net"]!;move(nx,ny);select();run(24_000_000*2)
  guard let net=window("Net") else {check(false,"Net opens the Net window");exit(1)}
  capture("configure-net")
  func texts()->[String] {icons(net).map(iconText)}
  check(["This station","File server","Print server","Use Arthurlib","Enable","Colour hourglass when used"].allSatisfy{texts().contains($0)} && texts().contains{$0.hasPrefix("Broadcast Loader")},"Net has the 3.11 controls")
  check(texts().contains("0.1"),"This station shows net 0, station 1")
  let fields=icons(net).filter{(word($0+16)>>12)&15==15}.sorted{signed($0+12)>signed($1+12)}
  check(fields.count==2,"a writable field for each server");let fs=fields[0],ps=fields[1]
  var seen:[String:Any]=["station":"0.1","initial":["fs":iconText(fs),"ps":iconText(ps),"cmos":[cm(1),cm(2),cm(3),cm(4)]]]
  func enter(_ f:UInt32,_ s:String){tap(net,f);clearField();type(s);press(0x47);run(24_000_000*2)}
  enter(fs,"0.254");check(cm(1)==254 && cm(2)==0 && iconText(fs)=="0.254","file server by number")
  enter(fs,"Fred");check(cm(1)==0 && cm(2)==0x46 && [cm(0x9e),cm(0x9f),cm(0xa0)]==[0x72,0x65,0x64] && iconText(fs)=="Fred","file server by name")
  seen["fs_name_cmos"]=(0x9e..<0xad).map{cm($0)}
  enter(ps,"0.235");check(cm(3)==235 && cm(4)==0 && iconText(ps)=="0.235","printer server by number")
  check(errors.isEmpty,"server changes report no error")
  let lib=cm(0x11);tap(net,labelled(net,"Use Arthurlib"));check(cm(0x11)==lib^2,"Use Arthurlib toggles CMOS &11 bit 1")
  let hourglass=labelled(net,"Colour hourglass when used"),loader=cm(0xc3)
  check((word(hourglass+16)&0x400000 != 0)==(loader&0x40 != 0),"Colour hourglass shaded only while broadcast loading is off")
  tap(net,labelled(net,"Enable"));check(cm(0xc3)==loader^0x40 && (word(hourglass+16)&0x400000 != 0)==(cm(0xc3)&0x40 != 0),"Enable toggles CMOS &C3 bit 6 (clear when enabled)")
  tap(net,labelled(net,"Enable"));check(cm(0xc3)==loader,"Enable toggles back")
  if cm(0xc3)&0x40 == 0 {tap(net,hourglass);check(cm(0xc3)==loader^0x80,"Colour hourglass toggles CMOS &C3 bit 7")}
  // No servers answer on this one-station network: neither button opens a
  // menu, and neither reports an error.
  let menusBefore=menus.count
  for f in [fs,ps] {let b=icons(net).filter{validation($0)=="Sgright,pgright" && abs((signed($0+4)+signed($0+12))/2-(signed(f+4)+signed(f+12))/2)<8};check(b.count==1,"a server menu button beside each field");tap(net,b[0]);run(24_000_000*6)}
  check(menus.count==menusBefore && errors.isEmpty,"no servers: no menu and no error")
  capture("configure-net-changed")
  seen["final"]=["fs":iconText(fs),"ps":iconText(ps),"cmos":[cm(1),cm(2),cm(3),cm(4)],"lib":cm(0x11),"loader":cm(0xc3)]
  json(seen,"configure-net-observations")
  closeWindow(net)
  move(bx,by);m.keyDown(0x71);run(960_000);m.keyUp(0x71);run(24_000_000)
  guard let qm=menus.last,let qi=qm["items"] as? [[String:Any]],let quit=qi.firstIndex(where:{$0["text"] as? String=="Quit"}) else {check(false,"Configure menu has Quit");exit(1)}
  let qb=menuBounds(),qh=Int(qm["height"] as! UInt32),qg=Int(qm["gap"] as! UInt32)
  move(qb[0]+40,qb[3]-quit*(qh+qg)-qh/2);select();run(24_000_000*3);capture("configure-quit")
  check(taskCount()==desktopTasks,"Quit removes the Configure task")
 } else {
 var cmosSeen:[String:[UInt8]]=[:]
 func cmosRow(_ name:String){cmosSeen[name]=(0..<240).map{cm($0)}}
 cmosRow("initial")
 // Save the initial configuration through the real Save box (icon-bar menu).
 func barMenu(){move(bx,by);m.keyDown(0x71);run(960_000);m.keyUp(0x71);run(24_000_000)}
 barMenu();capture("configure-menu")
 guard let menu=menus.last,let items=menu["items"] as? [[String:Any]] else {check(false,"Configure menu");exit(1)}
 check(items.map{$0["text"] as! String}==["Info","Save","Quit"],"icon-bar menu is Info, Save, Quit")
 let b=menuBounds(),mh=Int(menu["height"] as! UInt32),mg=Int(menu["gap"] as! UInt32)
 move(b[2]-20,b[3]-1*(mh+mg)-mh/2);run(24_000_000);capture("configure-save-box")
 check(Int32(bitPattern:word(moduleWorkspace("Wimp")+field("menuSP")))>=4,"Save opens the Save as box")
 clearField();type("ADFS::0.$.Cfg");press(0x47);run(24_000_000*4)
 check(errors.isEmpty,"Configure saves without error")
 try Data(disc.mergedImage()).write(to:out.appendingPathComponent("saved.adf"))
 var changes:[[String:Any]]=[],openTimes:[String:Int]=[:]
 func open(_ s:String,_ t:String)->UInt32 {let (x,y)=sectionAt[s]!;move(x,y);select();var waited=0;while window(t)==nil && waited<40 {run(2_400_000);waited+=1};openTimes[s]=waited;json(openTimes,"configure-open-times");run(24_000_000);guard let h=window(t) else {capture("configure-missing-"+s.lowercased());check(false,"\(s) opens \(t)");exit(1)};capture("configure-"+s.lowercased());return h}
 func expect(_ s:String,_ ok:Bool,_ bytes:[Int]){changes.append(["change":s,"cmos":bytes.map{["byte":$0,"value":cm($0)]}]);json(changes,"configure-changes");check(ok,s)}
 // Mouse: the drag-delay arrow and the fastest speed.
 var h=open("Mouse","Mouse")
 check(rowField(h,"Drag delay")=="5" && rowField(h,"Double click delay")=="10","Mouse shows the Wimp's configured values")
 tap(h,rowIcon(h,"Drag delay","Sright"));expect("Drag delay up writes WimpDragDelay 6",cm(0xdd)==6^5 && rowField(h,"Drag delay")=="6",[0xdd])
 let radios=icons(h).filter{validation($0)=="Sradiooff,radioon"}.sorted{signed($0)<signed($1)}
 check(radios.count==5,"five mouse speed radios");tap(h,radios[4]);expect("fast radio writes MouseStep 5",cm(0xc2)==5 && word(radios[4]+16)&0x200000 != 0,[0xc2])
 // The new speed applies at once (OS_Word 21): five OS units per count now.
 let (rx,ry)=iconCentre(h,radios[1]);m.mouseMove(dx:(rx-Int(word(1452)))/5,dy:(ry-Int(word(1456)))/5);run(4_800_000);select();run(4_800_000)
 expect("second radio restores MouseStep 2 and its multiplier",cm(0xc2)==2 && word(radios[1]+16)&0x200000 != 0,[0xc2])
 capture("configure-mouse-changed");closeWindow(h)
 h=open("Keyboard","Keyboard")
 tap(h,labelled(h,"Shift caps"));expect("Shift caps writes ShCaps",(cm(0x0b)>>3)&7==1,[0x0b])
 let delay=cm(0x0c);tap(h,rowIcon(h,"Delay for","Sright"));expect("Delay arrow writes Delay",cm(0x0c)==delay+1,[0x0c])
 closeWindow(h)
 h=open("Memory","Memory allocation")
 let page=cm(0x92);tap(h,rowIcon(h,"Module area","Sright"));expect("Module area arrow adds one page",cm(0x92)==page+1,[0x92])
 tap(h,icons(h).first{p in (word(p+16)>>12)&15==15 && abs(signed(p+4)-signed(rowIcon(h,"Module area","Sleft")+4))<4}!)
 clearField();type("96");press(0x47);run(4_800_000)
 expect("typed 96K and Return writes RMASize 96K",Int(cm(0x92))*32==96 && rowField(h,"Module area")=="96",[0x92])
 closeWindow(h)
 h=open("Screen","Screen")
 tap(h,rowIcon(h,"Blank delay","Sright"));expect("Blank delay arrow writes 30 seconds",(cm(0xbc)>>3)&7==1 && rowField(h,"Blank delay")=="30 Sec.",[0xbc])
 capture("configure-screen-changed");closeWindow(h)
 h=open("Sound","Sound")
 let volume=(cm(0x94)>>4)&7;tap(h,rowIcon(h,"Volume","Sleft"));expect("Volume arrow writes SoundDefault volume",(cm(0x94)>>4)&7==(volume==0 ? 0:volume-1),[0x94])
 check(icons(h).contains{iconText($0)=="WaveSynth-Beep"},"Sound names the configured voice")
 capture("configure-sound-changed");closeWindow(h)
 h=open("Printer","Printer")
 tap(h,labelled(h,"Serial"));expect("Serial writes Print 2",(cm(0x0f)>>5)&7==2,[0x0f])
 closeWindow(h)
 h=open("Windows","Window manager")
 let flags=cm(0xc5);tap(h,labelled(h,"Open submenus automatically"));expect("submenus option toggles WimpFlags bit 7",cm(0xc5)==flags^0x80,[0xc5])
 tap(h,labelled(h,"None"));expect("None clears the instant-drag flags",cm(0xc5)&15==0,[0xc5])
 capture("configure-windows-changed");closeWindow(h)
 h=open("Applications","Application auto-start")
 // !Alarm is on its own disc, not in Resources:, so it is shaded and All
 // leaves its bit (0) clear.
 tap(h,labelled(h,"All"));expect("All selects every ROM application",cm(0xd7)==0xfe,[0xd7])
 capture("configure-applications-all")
 tap(h,labelled(h,"None"));expect("None clears auto-start",cm(0xd7)==0,[0xd7])
 tap(h,labelled(h,"!Calc"));expect("!Calc toggles its auto-start bit",cm(0xd7)==2,[0xd7])
 tap(h,labelled(h,"!Alarm"));expect("shaded !Alarm ignores clicks",cm(0xd7)==2,[0xd7])
 closeWindow(h)
 h=open("Floppies","Floppy disc drives")
 func drives(_ h:UInt32,_ s:String)->Int {icons(h).filter{validation($0)==s && word($0+16)&0xC00000==0}.count}
 check(drives(h,"Sfloppydisc")==1,"one floppy drive shown");tap(h,topIcon(h,"Sup"))
 check(drives(h,"Sfloppydisc")==2 && cm(0x87)&7==1,"up arrow shows two drives; nothing written before OK")
 capture("configure-floppies-two");tap(h,labelled(h,"OK"));expect("OK writes Floppies 2",cm(0x87)&7==2,[0x87])
 check(window("Floppy disc drives").map{word($0+field("w_flags"))&0x10000==0} ?? false,"OK closes Floppy disc drives")
 h=open("Discs","Hard disc drives")
 check(drives(h,"Sharddisc")==0,"no ST506 or IDE drives shown");tap(h,topIcon(h,"Sup"))
 tap(h,labelled(h,"OK"));expect("OK writes HardDiscs 1",(cm(0x87)>>3)&7==1,[0x87])
 h=open("Fonts","Fonts")
 // FontMax2 is held EOR 12 (FontManager's default); OK applies the pending value.
 let fontMax2=cm(0xca)^12;check(rowField(h,"up to")==String(fontMax2),"Fonts shows the configured FontMax2")
 tap(h,rowIcon(h,"up to","Sright"));check(cm(0xca)^12==fontMax2,"nothing written before OK")
 tap(h,labelled(h,"OK"));expect("OK writes FontMax2 one point larger",cm(0xca)^12==fontMax2+1,[0xca])
 cmosRow("changed")
 // Load the saved file: double-click it in the Filer window, so Configure
 // receives Message_DataOpen and restores the recorded CMOS RAM bits.
 closeWindow(main)
 guard let fw=filingWindows.last?["definition"] as? [UInt32],let fi=filingIcons.last(where:{$0["text"] as? String=="Cfg"})?["definition"] as? [UInt32] else {check(false,"Filer shows the saved Cfg file");exit(1)}
 let fx=Int(Int32(bitPattern:fw[0]))+(Int(Int32(bitPattern:fi[0]))+Int(Int32(bitPattern:fi[2])))/2-Int(Int32(bitPattern:fw[4]))
 let fy=Int(Int32(bitPattern:fw[3]))+(Int(Int32(bitPattern:fi[1]))+Int(Int32(bitPattern:fi[3])))/2-Int(Int32(bitPattern:fw[5]))
 move(fx,fy);select();select();run(24_000_000*5);capture("configure-loaded")
 cmosRow("loaded")
 check(errors.isEmpty && taskCount()==desktopTasks+1,"the running Configure loads the file (one task)")
 for (a,mask) in [(0x0b,0x38),(0x0c,0xff),(0x0f,0xe2),(0x87,0xff),(0x92,0x7f),(0x94,0xff),(0xbc,0x38),(0xc2,0xff),(0xc5,0xff),(0xca,0xff),(0xd7,0xff),(0xdd,0xff)] {
  check(cm(a)&UInt8(mask)==cmosSeen["initial"]![a]&UInt8(mask),"loading restores CMOS byte \(a)")
 }
 // Texts as checked while Configure was paged in.
 json(["cmos":cmosSeen,"changes":changes,"main_icons":sections,"windows":openTimes.keys.sorted(),"open_polls":openTimes],"configure-observations")
 barMenu()
 let qb=menuBounds();move(qb[0]+40,qb[3]-2*(mh+mg)-mh/2);select();run(24_000_000*3);capture("configure-quit")
 check(taskCount()==desktopTasks,"Quit removes the Configure task")
 }
}
if target=="!Nevryon" {
 run(24_000_000*60)
 // An arbitrary elapsed-time boundary can land in a legitimate sound IRQ.
 // Observe its real return, with a strict 10 ms bound, before checking the
 // foreground game's mode. Do not write registers or bypass the handler.
 let start=m.ticks,initialPC=m.cpu.pc,initialPSR=m.cpu.psr
 while (m.cpu.psr&3 != 0 || m.cpu.pc>=0x3800000) && m.ticks-start<240_000 {run(1)}
 json(["initial_pc":initialPC,"initial_psr":initialPSR,"elapsed_ticks":m.ticks-start,"final_pc":m.cpu.pc,"final_psr":m.cpu.psr],"nevryon-mode-boundary")
 capture("nevryon-title")
 check(launchEvents.contains{($0["text"] as? String)=="SLOAD PIX.LOADINGSPR"},"original loading sprite command reached")
 check(launchEvents.contains{($0["text"] as? String)=="LOAD PIX.TITLEPIC 1B550"},"original title load reached")
 check(m.cpu.psr&3==0 && m.cpu.pc<0x3800000,"game runs in USR26")
}
if target=="!Swiv" {
 // SWIV chains IRQs by relocating the branch it finds at &18 (3.11 has one
 // there; 3.60's LDR pc through page zero sent the first IRQ into zeroed RAM).
 run(24_000_000*60)
 let irq=word(0x18),hook=UInt32(truncatingIfNeeded:Int64(0x20)+Int64(Int32(bitPattern:irq<<8)>>6)) & 0x3fffffc
 json(["irq_vector":irq,"irq_handler":hook,"pc":m.cpu.pc,"psr":m.cpu.psr],"swiv-vectors")
 check(irq>>24==0xEA && hook>=0x8000 && hook<0x1000000,"SWIV hooks IRQs with a branch to its own handler")
 capture("swiv-credits",settle:false)
 let credits=try Data(contentsOf:out.appendingPathComponent("swiv-credits-screen.bin"))
 check(credits.filter{$0 != 0}.count>4000,"SWIV draws its credits screen")
 m.keyDown(0x01);run(1_920_000);m.keyUp(0x01);run(24_000_000*4);capture("swiv-options",settle:false)
 let options=try Data(contentsOf:out.appendingPathComponent("swiv-options-screen.bin"))
 check(options != credits,"F1 shows the options screen")
}
if target=="!Zarch" {
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*3);capture("game-menu")
}
if target=="!MenuTest" {
 func menuWord(_ level:Int,_ field:String)->UInt32 {
  let h=word(moduleWorkspace("Wimp")+ws["menuhandles"]!["value"]!.uint32Value+UInt32(level*4))
  return word(h-1+ws[field]!["value"]!.uint32Value)
 }
 for item in [0,1] {
  let px=Int(menuWord(0,"w_wax1"))-20,py=Int(menuWord(0,"w_way1"))-22-item*44
  move(px,py);run(24_000_000);capture("submenu-\(item)")
  check(word(moduleWorkspace("Wimp")+ws["menuSP"]!["value"]!.uint32Value)==4,"classic submenu opens")
  let sx=Int(menuWord(1,"w_wax0"))+64,sy=Int(menuWord(1,"w_way1"))-22
  move(sx,sy);select();run(24_000_000)
 }
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE MENU CONTRACT PASS"},"classic menu warning/selection ABI")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("menu-returned")
 check(taskCount()==desktopTasks,"menu client exits and desktop survives")
}
if target=="!TaskTest" {
 let deadline=m.ticks+24_000_000*60
 while !launchEvents.contains(where:{$0["text"] as? String=="ARCLIBRE TASK SERVICES PASS"}) && m.ticks<deadline {run(24_000_000)}
 capture("task-services")
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE TASK SERVICES PASS"},"task and filter contracts pass")
 check(!launchEvents.contains{($0["text"] as? String)=="ARCLIBRE TASK SERVICES FAIL"},"no task service failure")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("task-services-returned")
 check(taskCount()==desktopTasks,"task services return to desktop")
}
if target=="!StrTest" {
 let deadline=m.ticks+24_000_000*60
 while !launchEvents.contains(where:{$0["text"] as? String=="ARCLIBRE STREAM CONTRACT PASS"}) && m.ticks<deadline {run(24_000_000)}
 capture("streams")
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE STREAM CONTRACT PASS"},"stream contracts pass")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("stream-returned")
 check(taskCount()==desktopTasks,"stream application exits back to desktop")
}
if target=="!RamTest" {
 let readyDeadline=m.ticks+24_000_000*30
 while !ramUIReady && m.ticks<readyDeadline {run(24_000_000)}
 check(ramUIReady,"RAM desktop fixture ready");ramUIHandled=true
 let syms=try! JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("ram-filing-runtime/modules/RAMFSFiler/symbols.json"))) as! [String:NSNumber]
 let workspace=moduleWorkspace("RAMFSFiler"),icon=word(workspace+syms["iconbaricon"]!.uint32Value)
 check(workspace>0 && workspace<0x4000000 && word(workspace+syms["mytaskhandle"]!.uint32Value)>0,"RAMFSFiler task active")
 let bar=word(moduleWorkspace("Wimp")+ws["iconbarhandle"]!["value"]!.uint32Value) & ~UInt32(3)
 check(icon<word(bar+ws["w_nicons"]!["value"]!.uint32Value),"RAM icon exists")
 let p=word(bar+ws["w_icons"]!["value"]!.uint32Value)+icon*32
 check(text(word(p+20))=="RAM","actual RAM icon text")
 let ix=(Int(Int32(bitPattern:word(p)))+Int(Int32(bitPattern:word(p+8))))/2
 let iy=(Int(Int32(bitPattern:word(p+4)))+Int(Int32(bitPattern:word(p+12))))/2
 let x=Int(Int32(bitPattern:word(bar+ws["w_wax0"]!["value"]!.uint32Value)))+ix-Int(Int32(bitPattern:word(bar+ws["w_scx"]!["value"]!.uint32Value)))
 let y=Int(Int32(bitPattern:word(bar+ws["w_way1"]!["value"]!.uint32Value)))+iy-Int(Int32(bitPattern:word(bar+ws["w_scy"]!["value"]!.uint32Value)))
 json(["icon":icon,"definition":(0..<8).map{word(p+UInt32($0*4))},"click":[x,y]],"ram-icon")
 move(x,y);select();run(24_000_000*2);capture("ram-disc-open")
 check(filingWindows.contains{($0["title"] as? String ?? "").hasPrefix("RAM::")},"RAM icon opens a real Filer directory")
 let deadline=m.ticks+24_000_000*60
 while !launchEvents.contains(where:{$0["text"] as? String=="ARCLIBRE RAM CONTRACT PASS"}) && m.ticks<deadline {run(24_000_000)}
 capture("ram-filing")
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE RAM CONTRACT PASS"},"RAM contracts pass")
 check(opens["Free",default:0]>0,"real Free window opened")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("ram-returned")
 check(taskCount()==desktopTasks,"RAM application exits back to desktop")
}
if target=="!UtilTest" {
 let deadline=m.ticks+24_000_000*40
 while !launchEvents.contains(where:{$0["text"] as? String=="ARCLIBRE UTILITY PASS"}) && m.ticks<deadline {run(24_000_000)}
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE UTILITY PASS"},"standard utilities contracts pass")
 json(Dictionary(uniqueKeysWithValues:services.map{(String($0.key),$0.value)}),"utility-services");capture("utilities")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("utilities-returned")
 check(taskCount()==desktopTasks,"utility application exits back to desktop")
}
if target=="!SqTest" {
 let deadline=m.ticks+24_000_000*90
 while !launchEvents.contains(where:{$0["text"] as? String=="ARCLIBRE SQUASH PASS"}) && m.ticks<deadline {run(24_000_000)}
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE SQUASH PASS"},"Squash contracts pass")
 json(["workspace":moduleWorkspace("Squash"),"words":(0..<25).map{word(moduleWorkspace("Squash")+UInt32($0*4))}],"squash-workspace")
 capture("squash")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("squash-returned")
 check(taskCount()==desktopTasks,"Squash application exits back to desktop")
}
if target=="!CAbiTest" {
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE C ABI PASS"},"C ABI application passes")
 check(!launchEvents.contains{($0["text"] as? String)=="ARCLIBRE C ABI FAIL"},"no C ABI failure")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("returned")
 check(taskCount()==desktopTasks,"C application exits back to desktop")
}
if target=="!SprTest" {
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE SPRITE COMMANDS PASS"},"sprite commands and API assertions pass")
 check(!launchEvents.contains{($0["text"] as? String)=="ARCLIBRE SPRITE COMMANDS FAIL"},"no sprite assertion failure")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("returned")
 check(taskCount()==desktopTasks,"sprite application exits back to desktop")
 check(disc.isModified,"SSave writes real floppy")
 try Data(disc.mergedImage()).write(to:out.appendingPathComponent("saved.adf"))
}
if target=="!SndTest" {
 check(launchEvents.contains{($0["text"] as? String)=="ARCLIBRE SOUND API PASS"},"sound API application passes")
 check(!launchEvents.contains{($0["text"] as? String)=="ARCLIBRE SOUND API FAIL"},"no sound API failure")
 check(m.vidc.soundBytesNonSilent>soundBeforeLaunch+1000 && m.memc.soundDMAEnabled,"real sound DMA emits non-silent samples")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("returned")
 check(taskCount()==desktopTasks,"sound application exits back to desktop")
}
if target=="!ArcTest" && !dragTest {
 check(launchEvents.contains{($0["swi"] as? UInt32)==0x24 && ($0["text"] as? String)?.hasPrefix("ArcLibre$AppSeen ")==true},"Filer executes !Boot")
 check(launchEvents.contains{($0["swi"] as? UInt32)==2 && ($0["text"] as? String)=="ARCLIBRE DOUBLE CLICK APPLICATION EXECUTED"},"nested Obey executes on-disc ARM2 application")
 m.keyDown(0x5f);run(1_920_000);m.keyUp(0x5f);run(24_000_000*2);capture("returned")
 check(taskCount()==desktopTasks,"application exits back to desktop tasks")
 let before=opens["Filer",default:0];move(64,60);select();run(24_000_000);check(opens["Filer",default:0]>before,"desktop remains responsive")
}
if actionTest {
 check(initialisations.contains{($0["name"] as? String)=="Filer Action Window"},"real action task started")
 for swi in ["040F80","040F81","040F82"] {check(swiCounts[swi,default:0]>0,"real action messages delivered") }
 check(!launchEvents.contains{($0["swi"] as? UInt32)==5 && (($0["text"] as? String)?.lowercased().contains("copy adfs:")==true)},"no command-line copy fallback")
}
json(loaderInstructions,"loader-instructions")
try Data(m.snapshot(createdBy:"ArcLibre desktop application launch")).write(to:out.appendingPathComponent("application.macarch-state"))
try m.fdc.trace.last(10000).map{$0.description}.joined(separator:"\n").write(to:out.appendingPathComponent("fdc.log"),atomically:true,encoding:.utf8)
json(["status":(actionTest || ["!ArcTest","!SndTest","!CAbiTest","!SprTest","!Nevryon","!TaskTest","!MenuTest","!StrTest","!RamTest","!UtilTest","!SqTest","!Chars","!Help","!Alarm","!Calc","!Configure"].contains(target)) ? "PASS":"OBSERVED","rom_sha256":rom.sha256,"application":target,"disc":discPath,"task_count":taskCount(),"events":launchEvents,"swi_counts":swiCounts,"sprite_vector_calls":spriteVectorCalls,"generated_sprite_code":generated.values.sorted{($0["pc"]!,$0["word"]!)<($1["pc"]!,$1["word"]!)},"undefined":undefined,"exceptions":m.cpu.exceptionCounts,"errors":errors,"screen":m.screenText],"result")
print("Desktop launch \(target): \(m.screenText.suffix(10))")
