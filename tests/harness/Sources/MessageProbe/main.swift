// SPDX-License-Identifier: Apache-2.0
// Real SWI client programs in test-owned application RAM; no service stubs.
import Foundation
import ArchimedesCore
func check(_ b:Bool,_ s:String) { if !b { fputs("FAIL: \(s)\n",stderr);exit(1) } }
let a=CommandLine.arguments;check(a.count==5,"MessageProbe ROM SNAPSHOT RESOURCES OUTPUT")
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
    check(d.isStopped && m.cpu.pc==0x800c,"SWI timeout/fault: \(name)")
    let r=(0..<8).map { m.cpu.r[$0] };let v=m.cpu.psr&0x10000000 != 0
    calls.append(["name":name,"swi":swi,"input":args,"output":r,"psr":m.cpu.psr,"tick":m.ticks,"error_text":v ? readString(r[0]+4) : ""])
    check(v==error,"unexpected V: \(name) \(v ? readString(r[0]+4) : "clear")")
    return r
}
let client=call("Claim client workspace",0x1e,[6,0,0,4096])[2]
let descriptor=client, filename=client+64, token=client+256, parameter=client+512, errorBlock=client+768, output=client+1024
for resource in resources {
    let name=resource["name"] as! String;string(filename,"Resources:$."+name)
    let r=call("FileInfo "+name,0x41500,[0,filename])
    let data=Array(try Data(contentsOf:root.appendingPathComponent(resource["source"] as! String)))
    check(r[0]&1==1 && r[2]==data.count+4,"ROM resource flags/size")
    write(descriptor,Array(repeating:0,count:16));call("Open resource "+name,0x41501,[descriptor,filename,0])
    let pointer=word(descriptor+8)
    check(word(pointer)==data.count+4 && bytes(pointer+4,data.count)==data,"resource exact public bytes: "+name)
    try Data(bytes(pointer+4,data.count)).write(to:URL(fileURLWithPath:out+"/"+name+".bin"))
    resourceReads.append(["name":name,"pointer":pointer+4,"length":data.count,"flags":r[0],"size":r[2]])
    call("Close resource "+name,0x41504,[descriptor])
}
string(filename,"Resources:$.Resources.Kernel.Messages");write(descriptor,Array(repeating:0,count:16))
call("OpenFile",0x41501,[descriptor,filename,0])
string(token,"Escape");call("Lookup Escape",0x41502,[descriptor,token,output,1024]);check(readString(output)=="Escape","plain lookup")
string(token,"HelpFound");string(parameter,"Keyboard")
call("Lookup substitution",0x41502,[descriptor,token,output,1024,parameter]);check(readString(output)=="==> Help on keyword Keyboard","parameter substitution")
string(token,"HUTMHLP");call("Lookup dictionary expansion",0x41502,[descriptor,token,output,1024])
let help=readString(output);check(help.hasPrefix("*Help <subjects>") && help.contains("Explain the syntax message format") && help.contains("\r"),"dictionary expansion")
try help.write(toFile:out+"/expanded-help.txt",atomically:true,encoding:.utf8)
let dictionary=call("Dictionary",0x41509,[])
let dict=Array(try Data(contentsOf:root.appendingPathComponent("sources/Messages/Data/Dictionary")))
check(bytes(dictionary[0],dict.count)==dict,"dictionary exact source bytes")
words(errorBlock,[0x12345678]);string(errorBlock+4,"NoSuchSWI1");string(parameter,"DEADBEEF")
let error=call("ErrorLookup",0x41506,[errorBlock,descriptor,0,0,parameter],error:true)
check(word(error[0])==0x12345678 && readString(error[0]+4)=="SWI &DEADBEEF not known","error number and substitution")
string(token,"NeverDefinedToken");let missing=call("Missing token",0x41502,[descriptor,token,output,1024],error:true)
check(readString(missing[0]+4)=="Message token NeverDefinedToken not found","MessageTrans own error resource")
call("CloseFile",0x41504,[descriptor])
for i in 1...3 { call("Reopen \(i)",0x41501,[descriptor,filename,0]);call("Reclose \(i)",0x41504,[descriptor]) }
call("Free client workspace",0x1e,[7,0,client])
check([1,3,4,5,7].allSatisfy { m.cpu.exceptionCounts[$0]==0 },"CPU fault")
for (tag,b) in m.stateSections() { try Data(b).write(to:URL(fileURLWithPath:out+"/final-\(tag).bin")) }
try JSONSerialization.data(withJSONObject:["status":"PASS","calls":calls,"resource_reads":resourceReads,"exceptions":m.cpu.exceptionCounts,"rom_sha256":rom.sha256],options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:out+"/result.json"))
try swis.joined(separator:"\n").write(toFile:out+"/swis.log",atomically:true,encoding:.utf8)
let trace=(d.trace?.last(4096) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined()
try trace.write(toFile:out+"/instructions.log",atomically:true,encoding:.utf8)
print("PASS: \(calls.count) real MessageTrans calls, seven byte-exact resources, dictionary, errors and reopen")
