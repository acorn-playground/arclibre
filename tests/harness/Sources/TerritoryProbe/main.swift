// SPDX-License-Identifier: Apache-2.0
// Real SWI client programs in test-owned application RAM; no service stubs.
import Foundation
import ArchimedesCore
func check(_ b:Bool,_ s:String) { if !b { fputs("FAIL: \(s)\n",stderr);exit(1) } }
let a=CommandLine.arguments;check(a.count==5,"TerritoryProbe ROM SNAPSHOT RESOURCES OUTPUT")
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let resources=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[3]))) as! [[String:Any]]
let root=URL(fileURLWithPath:a[3]).deletingLastPathComponent().deletingLastPathComponent()
let out=a[4];try FileManager.default.createDirectory(atPath:out,withIntermediateDirectories:true)
let d=m.debugger;d.setTracing(4096)
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:4))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:0x800c))
var calls:[[String:Any]]=[],swis:[String]=[],resourceReads:[[String:Any]]=[]
m.cpu.swiObserver={ pc,n in swis.append("\(m.ticks) \(String(pc,radix:16)) \(String(n,radix:16))") }
func bytes(_ p:UInt32,_ n:Int)->[UInt8] { (0..<n).map { m.memc.debugRead(p+UInt32($0),space:.logical)! } }
func word(_ p:UInt32)->UInt32 { m.memc.debugReadWord(p,space:.logical)! }
func write(_ p:UInt32,_ b:[UInt8]) { for (i,v) in b.enumerated() { check(m.memc.debugWrite(p+UInt32(i),v,space:.logical),"fixture memory") } }
func words(_ p:UInt32,_ w:[UInt32]) { write(p,w.flatMap { v in (0..<4).map { UInt8(truncatingIfNeeded:v>>($0*8)) } }) }
func string(_ p:UInt32,_ s:String) { write(p,Array(s.utf8)+[0]) }
func readString(_ p:UInt32)->String { String(bytes:bytes(p,1024).prefix { $0 != 0 },encoding:.isoLatin1)! }
@discardableResult func call(_ name:String,_ swi:UInt32,_ args:[UInt32],error:Bool=false)->[UInt32] {
    check(args.count<=8,"argument count")
    words(0x8000,[0xe59f8008,0xe89800ff,0xef020000|swi,0xeafffffe,0x8020])
    words(0x8020,args+Array(repeating:0,count:8-args.count))
    m.cpu.pc=0x8000;d.resume();_=m.run(untilTick:m.ticks+24_000_000,maxInstructions:2_000_000)
    if !(d.isStopped && m.cpu.pc==0x800c) {
        let trace=(d.trace?.last(4096) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
        try! trace.write(toFile:out+"/failure-instructions.log",atomically:true,encoding:.utf8)
        print("fault PC",String(m.cpu.pc,radix:16),"PSR",String(m.cpu.psr,radix:16))
    }
    check(d.isStopped && m.cpu.pc==0x800c,"SWI timeout/fault: \(name)")
    let r=(0..<8).map { m.cpu.r[$0] };let v=m.cpu.psr&0x10000000 != 0
    calls.append(["name":name,"swi":swi,"input":args,"output":r,"psr":m.cpu.psr,"tick":m.ticks,"error_text":v ? readString(r[0]+4) : ""])
    check(v==error,"unexpected V: \(name) \(v ? readString(r[0]+4) : "clear")")
    return r
}
let tablesURL=root.appendingPathComponent("artifacts/territory-tables.json")
let expected=try JSONSerialization.jsonObject(with:Data(contentsOf:tablesURL)) as! [String:Any]
let client=call("Claim client workspace",0x1e,[6,0,0,4096])[2]
let descriptor=client, filename=client+64, output=client+512, input=client+1024
check(call("Territory_Number",0x43040,[])[0]==1,"current UK")
check(call("Territory_Alphabet",0x43052,[UInt32.max])[0]==101,"Latin1 alphabet")
check(readString(call("Territory_AlphabetIdentifier",0x43053,[1])[0])=="Latin1","alphabet identifier")
check(call("Territory_WriteDirection",0x43055,[1])[0]==0,"UK write direction")
var tableReads:[[String:Any]]=[]
for t in expected["tables"] as! [[String:Any]] {
    let name=t["name"] as! String, wanted=(t["bytes"] as! [Int]).map { UInt8($0) }
    let swi=UInt32(t["swi"] as! Int), property=UInt32(t["property"] as? Int ?? 0)
    let pointer=call(name,swi,[UInt32.max,property])[0]
    check(bytes(pointer,wanted.count)==wanted,"complete source table: "+name)
    let explicit=call(name+" explicit UK",swi,[1,property])[0]
    check(pointer==explicit,"current and explicit territory agree")
    try Data(bytes(pointer,wanted.count)).write(to:URL(fileURLWithPath:out+"/"+name+".bin"))
    tableReads.append(["name":name,"pointer":pointer,"bytes":wanted.count])
}
call("Unknown property",0x43056,[1,99],error:true)
call("Reserved entry 24",0x43062,[1],error:true)
call("Reserved last",0x43074,[1],error:true)
call("Missing territory",0x43057,[99],error:true)
// Exercise the original UK -> OS_CLI -> International -> IntKey chain.
call("SelectKeyboardHandler",0x43054,[1])
for resource in resources {
    let name=resource["name"] as! String
    let data=Array(try Data(contentsOf:root.appendingPathComponent(resource["source"] as! String)))
    var reference:UInt32=0
    let mixed=String(name.enumerated().map { $0.offset%2==0 ? Character(String($0.element).uppercased()) : Character(String($0.element).lowercased()) })
    for (i,variant) in [name,name.lowercased(),name.uppercased(),mixed].enumerated() {
        string(filename,"Resources:$."+variant)
        let r=call("Case FileInfo "+variant,0x41500,[0,filename])
        check(r[0]&1==1 && r[2]==data.count+4,"case folded resource size")
        write(descriptor,Array(repeating:0,count:16));call("Case Open "+variant,0x41501,[descriptor,filename,0])
        let pointer=word(descriptor+8)+4
        if i==0 {reference=pointer};check(pointer==reference && bytes(pointer,data.count)==data,"case folded resource identity")
        resourceReads.append(["name":name,"variant":variant,"pointer":pointer])
        call("Case Close "+variant,0x41504,[descriptor])
    }
}
string(input,"UK")
check(call("NameToNumber UK",0x43060,[1,input])[0]==1,"UK name registration entry")
let interSymbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("artifacts/modules/Inter/symbols.json"))) as! [String:[String:NSNumber]]
let international=interSymbols["Service_International"]!["value"]!.uint32Value
for reason:UInt32 in [7,8,255] {
    let r=call("Unimplemented International reason \(reason)",0x30,[0,international,reason,0x11,0x22,0x33])
    check(r[1]==international && r[2]==reason && r[3]==0x11 && r[4]==0x22 && r[5]==0x33,"unknown service must remain unclaimed")
}
let sorting=(expected["sort"] as! [Int]).map { UInt8($0) }
let sample:[UInt8]=[65,99,111,114,110,32,233,201,92,0]
write(input,sample)
let transformed=call("TransformString",0x43061,[1,output,input,256])
check(transformed[0]==sample.count-1 && bytes(output,sample.count)==sample.map { sorting[Int($0)] },"original collation transformation")
string(input,"Acorn");string(output,"acorn")
check(call("Collate ignore case",0x4305d,[1,input,output,1])[0]==0,"case insensitive collation")
string(input,"Apple");string(output,"Banana")
check(Int32(bitPattern:call("Collate ordering",0x4305d,[1,input,output,0])[0])<0,"collation order")
call("Free client workspace",0x1e,[7,0,client])
check([1,3,4,5,7].allSatisfy { m.cpu.exceptionCounts[$0]==0 },"CPU fault")
for (tag,b) in m.stateSections() { try Data(b).write(to:URL(fileURLWithPath:out+"/final-\(tag).bin")) }
try JSONSerialization.data(withJSONObject:["status":"PASS","calls":calls,"table_reads":tableReads,"resource_reads":resourceReads,"exceptions":m.cpu.exceptionCounts,"rom_sha256":rom.sha256],options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/result.json"))
try swis.joined(separator:"\n").write(toFile:out+"/swis.log",atomically:true,encoding:.utf8)
let trace=(d.trace?.last(4096) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
try trace.write(toFile:out+"/instructions.log",atomically:true,encoding:.utf8)
print("PASS: territory tables, case-folded resources, collation, real errors and keyboard selection")
