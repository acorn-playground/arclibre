// SPDX-License-Identifier: Apache-2.0
// Executes real FPA instructions through the public software emulator on ARM2.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5,"FPEProbe ROM SNAPSHOT FPE_DIRECTORY OUTPUT")
let root=URL(fileURLWithPath:a[3]),out=URL(fileURLWithPath:a[4])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[2]))),rom:rom)
let d=m.debugger;d.setTracing(20000)
var calls:[[String:Any]]=[],tests:[[String:Any]]=[]
func json(_ x:Any,_ name:String) { try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json")) }
func trace(_ name:String) { let t=(d.trace?.last(20000) ?? []).map { "\($0.ticks) \(String(format:"%08X %08X",$0.pc,$0.instruction)) \($0.registerText)\n" }.joined();try! t.write(to:out.appendingPathComponent(name+"-trace.log"),atomically:true,encoding:.utf8) }
func check(_ b:Bool,_ s:String) { if !b { trace("failure");json(["failure":s,"pc":m.cpu.pc,"psr":m.cpu.psr,"r":(0..<15).map{m.cpu.r[$0]},"calls":calls,"tests":tests],"failure");fputs("FAIL: \(s) at \(String(m.cpu.pc,radix:16))\n",stderr);exit(1) } }
func word(_ p:UInt32)->UInt32 { m.memc.debugReadWord(p,space:.logical)! }
func bytes(_ p:UInt32,_ n:Int)->[UInt8] {(0..<n).map{m.memc.debugRead(p+UInt32($0),space:.logical)!}}
func write(_ p:UInt32,_ b:[UInt8]) { for (i,v) in b.enumerated(){check(m.memc.debugWrite(p+UInt32(i),v,space:.logical),"write fixture")} }
func words(_ p:UInt32,_ w:[UInt32]) { write(p,w.flatMap{v in (0..<4).map{UInt8(truncatingIfNeeded:v>>($0*8))}}) }
func string(_ p:UInt32,_ s:String) { write(p,Array(s.utf8)+[0]) }
func text(_ p:UInt32)->String { String(bytes:bytes(p,256).prefix{$0 != 0},encoding:.isoLatin1)! }
func run(_ start:UInt32,_ stop:UInt32,_ name:String) {
 let bp=try! d.addBreakpoint(.init(id:0,kind:.execute,start:stop));m.cpu.pc=start;d.resume()
 _=m.run(untilTick:m.ticks+24_000_000,maxInstructions:2_000_000)
 _=d.removeBreakpoint(bp.id)
 check(d.isStopped && m.cpu.pc==stop,"timeout/fault \(name)")
 check(m.cpu.mode == .supervisor,"SVC26 return \(name)")
 check([3,4,5,7].allSatisfy{m.cpu.exceptionCounts[$0]==0},"unexpected processor fault \(name)")
}
@discardableResult func call(_ name:String,_ swi:UInt32,_ args:[UInt32])->[UInt32] {
 words(0x8000,[0xe59f8008,0xe89800ff,0xef020000|swi,0xeafffffe,0x8020]);words(0x8020,args+Array(repeating:0,count:8-args.count));run(0x8000,0x800c,name)
 let r=(0..<8).map{m.cpu.r[$0]};let v=m.cpu.psr&0x10000000 != 0
 calls.append(["name":name,"swi":swi,"input":args,"output":r,"psr":m.cpu.psr,"error":v ? text(r[0]+4):""])
 check(!v,"SWI \(name): \(v ? text(r[0]+4):"")");return r
}
_ = try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
let module=Array(try Data(contentsOf:root.appendingPathComponent("module.bin")))
let resources=Array(try Data(contentsOf:root.appendingPathComponent("resources.bin")))
let client=Array(try Data(contentsOf:root.appendingPathComponent("client.bin")))
let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("client-symbols.json"))) as! [String:NSNumber]
func sym(_ n:String)->UInt32 {0x9000+symbols[n]!.uint32Value}
write(0x9000,client)
let resourceBase=call("Claim resources",0x1e,[6,0,0,UInt32(resources.count)])[2];write(resourceBase,resources)
call("Register real error messages",0x41b40,[resourceBase])
let oldVector=word(4),oldAnchor=word(0xff4)
write(0x20000,module);call("Copy and initialise FPEmulator",0x1e,[11,0x20000,UInt32(module.count)])
let newVector=word(4),newAnchor=word(0xff4)
string(0x11000,"FPEmulator");let lookup=call("Look up installed code",0x1e,[18,0x11000])
let moduleBase=lookup[3]
check(bytes(moduleBase,module.count)==module && lookup[4]==newAnchor,"exact module and private workspace")
check(newVector != oldVector && newAnchor != 0,"real undefined-vector installation")
let version=call("Version",0x40480,[])
check(version[0]==428,"public module version")
check(!m.cpu.hasSWP && m.cpu.cp15 == nil,"ARM2 configuration")
trace("initialisation")
func test(_ name:String,_ r0:UInt32=0,_ r1:UInt32=0) {
 write(0x10000,Array(repeating:0xcc,count:256))
 // Guest register setup preserves the kernel's SVC stack and processor state.
 words(0x8100,[0xe59f0010,0xe59f1010,0xe59fa010,0xe59ff010,0xe1a00000,0xe1a00000,r0,r1,0x10000,sym(name)])
 let before=m.cpu.exceptionCounts[1];let sp=m.cpu.r[13]
 run(0x8100,sym("stop"),name)
 check(m.cpu.r[13]==sp,"balanced SVC stack \(name)")
 let delta=m.cpu.exceptionCounts[1]-before
 check(delta>0,"real ARM2 undefined traps \(name)")
 tests.append(["name":name,"undefined_traps":delta,"psr":m.cpu.psr,"sp":sp,"result_words":(0..<64).map{word(0x10000+UInt32($0*4))}]);trace("\(tests.count)-"+name)
}
func double(_ offset:UInt32)->Double { // FPA double format stores the high word first.
 Double(bitPattern:(UInt64(word(0x10000+offset))<<32)|UInt64(word(0x10004+offset)))
}
test("status");check(word(0x10000)&0x00ffffff==0x70000,"Wimp default FPSR")
for name in ["arithmetic","user_arithmetic"] {
 test(name);check(double(0)==10 && double(8)==21 && abs(double(16)-7.0/3.0)<1e-15 && word(0x10018)==2,"arithmetic values \(name)");if name=="user_arithmetic" {check(word(0x100fc)&3==0,"real USR26 execution")}
}
test("save_restore")
check(bytes(0x10004,96)==bytes(0x10080,96),"all eight extended registers restored")
check(word(0x10000)==word(0x100e0),"FPSR restored")
for i in 0..<8 {check(word(0x10004+UInt32(i*12))&0x7fff>=0x3fff,"nonzero extended register \(i)")}
test("transcendentals")
check(abs(double(0)-sin(0.5))<1e-15 && double(8)==2 && double(16)==0 && double(24)==1,"recursive transcendental results")
test("masked_zero_divide");check(double(0).isInfinite && word(0x10008)&2 != 0,"masked IEEE divide-by-zero")
// Independent contexts must not share their FP registers or FPSR.
let length=call("ContextLength",0x40484,[])[0]
let c1=call("Claim context one",0x1e,[6,0,0,length])[2]
let c2=call("Claim context two",0x1e,[6,0,0,length])[2]
call("Init context one",0x40485,[c1]);call("Init context two",0x40485,[c2])
call("Activate one",0x40483,[c1]);test("context_write",11,0x70000);test("context_read");let one=bytes(0x10000,16)
call("Activate two",0x40483,[c2]);test("context_write",29,0x70010);test("context_read");let two=bytes(0x10000,16)
check(one != two,"distinct contexts")
call("Restore one",0x40483,[c1]);test("context_read");check(bytes(0x10000,16)==one,"first context preserved")
call("Restore two",0x40483,[c2]);test("context_read");check(bytes(0x10000,16)==two,"second context preserved")
call("Default context",0x40483,[0xffffffff])
call("Free context one",0x1e,[7,0,c1]);call("Free context two",0x1e,[7,0,c2])
// Non-FPA instructions must chain to the kernel; enabled FP exceptions must
// deliver a translated error through the real OS error mechanism.
var errors:[[String:Any]]=[]
let prior=call("Install client error handler",0x40,[6,sym("error_handler"),0x11200,0x11300])
func expectedError(_ name:String,_ number:UInt32,_ message:String) {
 write(0x11200,Array(repeating:0,count:512));let before=m.cpu.exceptionCounts[1]
 run(sym(name),sym("stop"),name)
 check(word(0x11200)==0x11200,"client error handler reached")
 let actual=word(0x11304),messageActual=text(0x11308)
 check(actual==number && messageActual==message,"real error \(name): \(String(actual,radix:16)) \(messageActual)")
 errors.append(["name":name,"number":actual,"message":messageActual,"return_pc":word(0x11300),"undefined_traps":m.cpu.exceptionCounts[1]-before]);trace(name)
}
expectedError("trapped_zero_divide",0x80000202,"Floating point exception: division by zero")
expectedError("unsupported_coprocessor",0x80000000,String(format:"Internal error: undefined instruction at &%08X",sym("unsupported_coprocessor")+4))
string(0x11000,"FPEmulator");call("Finalise FPEmulator",0x1e,[4,0x11000])
check(word(4)==oldVector,"undefined vector restored on finalisation")
expectedError("uninstalled_fpa",0x80000000,String(format:"Internal error: undefined instruction at &%08X",sym("uninstalled_fpa")+4))
call("Restore client error handler",0x40,[6,prior[1],prior[2],prior[3]])
call("Deregister resources",0x41b41,[resourceBase]);call("Free resources",0x1e,[7,0,resourceBase])
json(["status":"PASS","calls":calls,"tests":tests,"errors":errors,"rom_sha256":rom.sha256,"exceptions":m.cpu.exceptionCounts,"old_vector":oldVector,"new_vector":newVector,"old_anchor":oldAnchor,"new_anchor":newAnchor,"module_base":moduleBase,"context_length":length],"result")
print("PASS: real FPEmulator, \(tests.count) FPA cases, context isolation and vector restoration")
