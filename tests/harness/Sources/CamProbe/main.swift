// SPDX-License-Identifier: Apache-2.0
// Real guest SWI tests with host observation, using unchanged MacArch core.
import Foundation
import ArchimedesCore
func check(_ b: Bool,_ s: String) { if !b { fatalError(s) } }
let a=CommandLine.arguments
check(a.count==6,"CamProbe ROM SNAPSHOT SYMBOLS OUTPUT natural|fixtures|negative")
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]))) as! [String:NSNumber]
func sym(_ n:String)->UInt32 { symbols[n]!.uint32Value }
let out=a[4];try FileManager.default.createDirectory(atPath:out,withIntermediateDirectories:true)
let d=m.debugger;d.setTracing(10000)
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
let camFail=try d.addBreakpoint(.init(id:0,kind:.execute,start:sym("CamMapBroke")-8))
var events:[String]=[]
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:sym("testrestoreheapend"),logMessage:"RESTORE lr={R14} size={R10}"))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:sym("MoveCAMatR0toR3"),logMessage:"MOVE old={R0} new={R3}"))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:sym("NoHighSWIHandler"),logMessage:"MISSING swi={R11} lr={R14}"))
func word(_ x:UInt32)->UInt32 { m.memc.debugReadWord(x,space:.logical)! }
func save(_ stage:String) throws {
    for (tag,b) in m.stateSections() { try Data(b).write(to:URL(fileURLWithPath:out+"/\(stage)-\(tag).bin")) }
    let j:[String:Any] = ["pc":m.cpu.pc,"psr":m.cpu.psr,"r":(0..<15).map { m.cpu.r[$0] },"ticks":m.ticks,"instructions":m.cpu.instructionCount,"cam_failures":d.breakpoints.first{$0.id==camFail.id}!.hitCount,"heap_base":word(sym("SysHeapStart")+8),"heap_end":word(sym("SysHeapStart")+12),"app_end":word(sym("AplWorkSize")),"exceptions":m.cpu.exceptionCounts]
    try JSONSerialization.data(withJSONObject:j,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/\(stage).json"))
    try Data(m.snapshot(createdBy:"Open Archimedes CAM transition" )).write(to:URL(fileURLWithPath:out+"/\(stage).macarch-state"))
    let trace=(d.trace?.last(10000) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
    try trace.write(toFile:out+"/\(stage)-instructions.log",atomically:true,encoding:.utf8)
}
func reach(_ pc:UInt32, allowFail:Bool=false) throws -> Bool {
    let bp=try d.addBreakpoint(.init(id:0,kind:.execute,start:pc));d.resume()
    let deadline=m.ticks+24_000_000
    while !d.isStopped && m.ticks<deadline {
        _=m.run(untilTick:min(deadline,m.ticks+24000),maxInstructions:500)
        check(d.log.count<Debugger.logLimit,"log overflow")
        events += d.log.map{"\($0.ticks) \($0.text)"};d.clearLog()
    }
    _=d.removeBreakpoint(bp.id)
    if allowFail && m.cpu.pc==sym("CamMapBroke")-8 { return false }
    check(d.isStopped && m.cpu.pc==pc,"unexpected stop/timeout at \(String(m.cpu.pc,radix:16))")
    return true
}
func inject(_ words:[UInt32]) {
    for (i,w) in words.enumerated() { for b in 0..<4 { check(m.memc.debugWrite(0x8000+UInt32(i*4+b),UInt8(truncatingIfNeeded:w>>(b*8)),space:.logical),"test RAM") } }
    m.cpu.pc=0x8000
}
func change(_ area:UInt32,_ bytes:UInt32,_ stage:String) throws {
    // LDR r0,[pc,#8]; LDR r1,[pc,#8]; SWI XOS_ChangeDynamicArea; B .; area; bytes
    inject([0xe59f0008,0xe59f1008,0xef02002a,0xeafffffe,area,bytes])
    _=try reach(0x800c);try save(stage)
}
try save("pre-module")
if a[5]=="natural" || a[5]=="negative" {
    // Modules can now grow the RMA before the kernel's final heap shrink.
    // Identify this specific call site rather than the first CDA SWI in boot.
    check(word(sym("PostSysHeapShrink")-4)==0xef02002a,"kernel heap-shrink call site")
    _=try reach(sym("PostSysHeapShrink")-4)
    _=try reach(sym("ChangeDynamicSWI"));try save("shrink-entry")
    let success=try reach(sym("PostSysHeapShrink"),allowFail:a[5]=="negative")
    try save(success ? "shrink-return" : "reproduced-cam-failure")
    if a[5]=="negative" { check(!success,"negative control failed to expose old defect") }
    else {
        check(word(sym("SysHeapStart")+12)==0x6000,"heap size restored after no whole page removable")
        check(m.cpu.r[1]==0,"startup shrink must move zero bytes")
        // Stop at the real filing-system SWI; no service is installed or bypassed.
        _=try reach(sym("SelectFSSWI"));try save("filing-system-call")
        _=try reach(sym("SelectFSSWI")+4);try save("filing-system-return")
        _=try reach(sym("RdchLoop"));try save("supervisor-entry")
    }
} else {
    let app=word(sym("AplWorkSize"));check(app==0x3b0000,"baseline application end")
    try change(0,0xffff0000,"oversized-shrink") // 64K requested, no whole heap page removable.
    check(m.cpu.r[1]==0 && word(sym("SysHeapStart")+12)==0x6000,"bounded partial shrink")
    try change(0,32768,"heap-grow")
    check(m.cpu.psr&0x10000000==0 && m.cpu.r[1]==32768,"heap grow success")
    check(word(sym("SysHeapStart")+12)==0xe000 && word(sym("AplWorkSize"))==app-32768,"heap grow accounting")
    // Guest writes a marker into the moved page through its new logical address.
    inject([0xe59f000c,0xe59f100c,0xe5801000,0xe5902000,0xeafffffe,0x1c08000,0x51a7c0de])
    _=try reach(0x8010);check(m.cpu.r[2]==0x51a7c0de,"new page readable/writable");try save("heap-page-marker")
    try change(0,0xffff8000,"heap-shrink")
    check(m.cpu.psr&0x10000000==0 && m.cpu.r[1]==32768,"heap shrink returns magnitude moved")
    check(word(sym("SysHeapStart")+12)==0x6000 && word(sym("AplWorkSize"))==app,"heap shrink accounting")
    check(word(app-32768)==0x51a7c0de,"physical page contents preserved through remap")
    try change(0,65536,"heap-grow-two")
    check(m.cpu.psr&0x10000000==0 && word(sym("SysHeapStart")+12)==0x16000,"two-page heap grow")
    try change(0,0xffc00000,"partial-shrink-two")
    check(m.cpu.psr&0x10000000 != 0 && m.cpu.r[1]==65536,"partial shrink returns actual moved magnitude and V")
    check(word(m.cpu.r[0])==0x1c1,"genuine NotAllMoved error")
    check(word(sym("SysHeapStart")+12)==0x6000 && word(sym("AplWorkSize"))==app,"partial shrink retains minimum heap and application accounting")
    try change(1,32768,"rma-grow")
    check(m.cpu.psr&0x10000000==0 && word(0x180000c)==65536,"RMA grow")
    try change(1,0xffff8000,"rma-shrink")
    check(m.cpu.psr&0x10000000==0 && word(0x180000c)==32768,"RMA shrink")
    check(word(sym("AplWorkSize"))==app,"RMA accounting")
}
try events.joined(separator:"\n").write(toFile:out+"/events.log",atomically:true,encoding:.utf8)
let report:[String:Any]=["status":"PASS","mode":a[5],"rom_sha256":rom.sha256,"cam_failures":d.breakpoints.first{$0.id==camFail.id}!.hitCount,"exceptions":m.cpu.exceptionCounts]
try JSONSerialization.data(withJSONObject:report,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/result.json"))
print("PASS: \(a[5])")
