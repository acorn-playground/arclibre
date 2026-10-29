// SPDX-License-Identifier: Apache-2.0
// Power-on IIC/RTCAdjust experiment: no guest code injection or module loading.
// Guest actions are typed at the real F12 command line. The only hardware
// change is moving the emulated PCF8583's time, as a drifting crystal would.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5,"ClockProbe ROM BUILD_DIRECTORY OUTPUT smoke|drift|century|leap|absent")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[3]),scenario=a[4]
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
let modules=layout["modules"] as! [[String:Any]]
precondition(rom.sha256==layout["rom_sha256"] as! String)
let present=modules.contains{$0["component"] as? String=="RTCAdjust"}
precondition(present==(scenario != "absent"),"scenario does not match ROM profile")
// Unix times for the RTC, and the matching RISC OS CMOS year (bytes 128/129).
let epochs:[String:(Int64,UInt8,UInt8)]=["smoke":(770_428_800,94,19),"drift":(770_428_800,94,19),"absent":(770_428_800,94,19),
 "century":(946_684_800-1800,99,19),   // 1999-12-31 23:30:00
 "leap":(951_780_600,0,20)]            // 2000-02-28 23:30:00
var config=MachineConfiguration(model:.a440)
config.cpu = .arm2;config.ramKB=4096;config.romPaths=[a[1]];config.hardDiscs=[];config.monitor="standard";config.powerOnKeys=[0x34]
config.rtcEpoch=epochs[scenario]!.0
config.cmosSettings=[.init(byte:135,value:1),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12),
 .init(byte:128,value:epochs[scenario]!.1),.init(byte:129,value:epochs[scenario]!.2)]
let m=try Machine(configuration:config,rom:rom)
m.powerOn();let d=m.debugger;d.setTracing(100000)
var undefined=0,errors:[[String:Any]]=[],observations:[String:Any]=["scenario":scenario,"rom_sha256":rom.sha256,"rtc_epoch":config.rtcEpoch]
func word(_ p:UInt32)->UInt32 {m.memc.debugReadWord(p,space:.logical) ?? 0xffffffff}
func text(_ p:UInt32)->String {var b:[UInt8]=[];for i in 0..<256 {guard let v=m.memc.debugRead(p+UInt32(i),space:.logical),v>=32 else{break};b.append(v)};return String(bytes:b,encoding:.isoLatin1) ?? "?"}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
func trace(_ name:String){let s=(d.trace?.last(100000) ?? []).map{"\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n"}.joined();try! s.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8)}
func check(_ b:Bool,_ s:String){if !b{trace("failure");json(["failure":s,"pc":m.cpu.pc,"exceptions":m.cpu.exceptionCounts,"errors":errors,"observations":observations,"text":m.screenText],"failure");fputs("FAIL: \(s)\n",stderr);exit(1)}}
var callEvery:[[String:Any]]=[]
let rtcBase=(modules.first{$0["component"] as? String=="RTCAdjust"}?["base"] as? NSNumber)?.uint32Value ?? 0
m.cpu.swiObserver={pc,n in
 let swi=n & ~UInt32(0x20000)
 if swi==0x400df{errors.append(["error":text(m.cpu.r[0]+4),"number":word(m.cpu.r[0])])}
 // OS_CallEvery issued from RTCAdjust's own code: its hourly registrations.
 if swi==0x3c && rtcBase>0 && pc>=rtcBase && pc<rtcBase+4096{callEvery.append(["ticks":m.ticks,"period":m.cpu.r[0]])}
}
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
func run(_ ticks:UInt64){let end=m.ticks+ticks;d.resume();while m.ticks<end {
 _=m.run(untilTick:min(end,m.ticks+2_400_000),maxInstructions:300_000)
 if d.isStopped {
  // Undefined instructions are FPEmulator's normal trap; aborts are faults.
  check(m.cpu.pc==4,"processor fault");undefined+=1;d.resume()
 }
 };check(errors.isEmpty,"desktop error: \(errors)")}
let centisecond:UInt64=240_000
func press(_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(k);if shift{m.keyUp(0x4c);run(720_000)}};run(24_000_000)}
func moduleWorkspace(_ c:String)->UInt32 {var node=word(2000);let base=(modules.first{$0["component"] as! String==c}!["base"] as! NSNumber).uint32Value
 for _ in 0..<80 {if node==0{break};if word(node+4)==base{return word(word(node+12)+4)};node=word(node)};return 0xffffffff}
let symbols:[String:Int]=present ? try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("clock-runtime/modules/RTCAdjust/symbols.json"))) as! [String:Int] : [:]
func field(_ name:String)->Int32 {Int32(bitPattern:word(moduleWorkspace("RTCAdjust")+UInt32(symbols[name]!)))}
func state()->[String:Any] {
 var s:[String:Any]=["ticks":m.ticks,"ioc_timer0_latch":Int(m.ioc.timerLatches[0]),"rtc_registers":Array(m.rtc.ram[1...6]).map{Int($0)}]
 if present {for n in ["FailureMode","LastError","LastMonoTime","LastLatchValue","CallBackPending"]{s[n]=Int(field(n))}}
 return s}
// RTCAdjust's documented calibration, with its unsigned 64-bit truncating divides:
// new = L*(P+C)*P' / P / (P'-(C-W)), clamped to 18000..22000.
func expected(latch:Int64,c:Int64,w:Int64,elapsed:Int64)->Int64 {
 let p:Int64=360_000;let pc=max(0,p+c);var div=elapsed-(c-w);if div<=0{div=1}
 let product=UInt64(latch)*UInt64(pc)*UInt64(elapsed)
 return min(22000,max(18000,Int64(product/UInt64(p)/UInt64(div))))}
// Watch for a period and verify every recalibration against the formula.
func watch(_ name:String,_ cs:UInt64)->[[String:Any]] {
 // Per-instruction tracing is costly over an emulated hour; each event's state
 // is recorded instead, and tracing resumes for any later failure.
 d.setTracing(0);defer{d.setTracing(100000)}
 var events:[[String:Any]]=[];let end=m.ticks+cs*centisecond
 var latch=Int64(field("LastLatchValue")),w=Int64(field("LastError")),mono=field("LastMonoTime")
 while m.ticks<end {
  run(10*centisecond)
  if field("LastMonoTime") != mono {
   check(field("FailureMode")==0 && field("CallBackPending")==0,"\(name): recalibration completed without failure")
   let c=Int64(field("LastError")),elapsed=Int64(field("LastMonoTime"))-Int64(mono)
   let want=expected(latch:latch,c:c,w:w,elapsed:elapsed),got=Int64(field("LastLatchValue"))
   check(got==want,"\(name): latch \(got) equals formula \(want)")
   check(Int64(m.ioc.timerLatches[0])==want-1,"\(name): IOC timer 0 programmed with latch-1")
   events.append(["ticks":m.ticks,"C":c,"W":w,"elapsed_cs":elapsed,"latch_before":latch,"latch_after":got,"rtc_registers":Array(m.rtc.ram[1...6]).map{Int($0)}])
   latch=got;w=c;mono=field("LastMonoTime")
  }
 }
 return events}

run(24_000_000*35)
let boot=state();observations["boot"]=boot
check(Int(m.ioc.timerLatches[0])==19999,"kernel programs 20000-1 into IOC timer 0")
if present {check(field("FailureMode")==0 && field("LastLatchValue")==20000,"RTCAdjust initialised with default latch")}

// The public IIC API, typed in BASIC at the real F12 command line.
press(0x0c);run(24_000_000*2)
type("BASIC\n")
type("DIM b% 16:?b%=1:SYS \"XIIC_Control\",&A0,b%,1 TO e%;f%:IF f% AND 1 PRINT \"IICREAD \";$(e%+4) ELSE SYS \"IIC_Control\",&A1,b%,6:PRINT \"IICREAD\";:FOR i%=0 TO 5:PRINT \" \";~b%?i%;:NEXT:PRINT\n")
let rtcNow=Array(m.rtc.ram[1...6])
type("SYS \"XIIC_Control\",&D0,b%,1 TO e%;f%:PRINT \"NOACK \";f% AND 1;\" \";~!e%;\" \";:SYS \"XOS_Write0\",e%+4:PRINT\n")
// A write: register pointer 9 then four bytes into the PCF8583's alarm
// registers (the alarm is disabled), auto-incrementing; then read them back.
let alarmBefore=Array(m.rtc.ram[9...12])
type("DIM w% 8:w%?0=9:w%?1=&12:w%?2=&34:w%?3=&56:w%?4=&78:SYS \"XIIC_Control\",&A0,w%,5 TO e%;f%:?b%=9:SYS \"IIC_Control\",&A0,b%,1:SYS \"IIC_Control\",&A1,b%,4:PRINT \"IICWRITE \";f% AND 1;:FOR i%=0 TO 3:PRINT \" \";~b%?i%;:NEXT:PRINT\n")
let alarmAfter=Array(m.rtc.ram[9...12])
let screen=m.screenText;observations["basic_screen"]=screen
if present {
 let line=screen.first{$0.hasPrefix("IICREAD ")}
 check(line != nil,"IIC_Control read printed")
 let bytes=line!.split(separator:" ").dropFirst().compactMap{UInt8($0,radix:16)}
 check(bytes.count==6,"six RTC registers read through IIC_Control")
 // Hours, day/year and weekday/month must match the clock chip exactly.
 check(Array(bytes[3...5])==Array(rtcNow[3...5]),"IIC_Control returns the PCF8583's actual date registers")
 observations["iic_read"]=bytes.map{Int($0)}
 check(screen.contains{$0.hasPrefix("NOACK 1 20300 No acknowledge from IIC device")},"absent IIC device returns the real NoAck error and message")
 check(alarmBefore != [0x12,0x34,0x56,0x78] && alarmAfter==[0x12,0x34,0x56,0x78],"IIC_Control writes reach the PCF8583's registers")
 check(screen.contains{$0.hasPrefix("IICWRITE 0 12 34 56 78")},"IIC_Control reads the written registers back")
 observations["iic_write"]=alarmAfter.map{Int($0)}
} else {
 check(screen.contains{$0.contains("SWI name not known")},"absent IIC module: SWI name not known")
}
type("QUIT\n");press(0x47);run(24_000_000*2)

if scenario=="smoke" {
 // Quick tier: boot, IIC read and NoAck only; calibration needs an hour.
 check(callEvery.count==2,"RTCAdjust registers its hourly ticker at init and Service_Reset")
} else if present {
 // Init and the power-on Service_Reset each register the original hourly
 // ticker, so every hour brings two recalibrations about a second apart.
 check(callEvery.count==2 && callEvery.allSatisfy{($0["period"] as! UInt32)==359_999},"RTCAdjust registers its hourly ticker at init and Service_Reset")
 observations["call_every"]=callEvery
 // The RTC falls three seconds behind the IOC-driven software clock.
 if scenario=="drift" {m.rtc.epochSeconds -= 3}
 let events=watch("first hour",360_000+6_000);observations["events"]=events
 check(events.count==2,"two recalibrations in the first hour")
 if scenario=="drift" {
  check((events[0]["latch_after"] as! Int64)>20000,"IOC ticks are lengthened when the software clock runs ahead")
  press(0x0c);run(24_000_000*2);type("*RMKill RTCAdjust\n");press(0x47);run(24_000_000*2)
  observations["after_kill"]=["ioc_timer0_latch":Int(m.ioc.timerLatches[0])]
  check(Int(m.ioc.timerLatches[0])==19999,"RTCAdjust Die restores the default IOC latch")
  check(moduleWorkspace("RTCAdjust")==0xffffffff,"RTCAdjust removed from module chain")
 } else {
  let c=Int(field("LastError"));check(abs(c)<=2,"\(scenario): RTC and software clock agree across the date boundary (C=\(c))")
 }
} else {
 // As in watch(), per-instruction tracing is suspended over the emulated hour.
 m.rtc.epochSeconds -= 3;d.setTracing(0);run((360_000+6_000)*centisecond);d.setTracing(100000)
 observations["absent_after_hour"]=state()
 check(Int(m.ioc.timerLatches[0])==19999,"without RTCAdjust the IOC latch is never recalibrated")
}
observations["undefined_traps"]=undefined
json(observations,"observations")
json(["status":"PASS","scenario":scenario,"rom_sha256":rom.sha256],"result")
print("PASS: \(scenario)")
