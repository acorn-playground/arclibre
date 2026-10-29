// SPDX-License-Identifier: Apache-2.0
// Two Archimedes on one emulated Econet line, run in lockstep: station 1
// ("A") and station 2 ("B"), each at the real F12 command line of a
// power-on desktop. A command "A:text" or "B:text" is typed on that machine;
// "WAIT:n" runs the network n more emulated seconds. After each command both
// screens are recorded. No guest code injection or module loading.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count>=4,"NetProbe ROM ROM_DIRECTORY OUTPUT COMMAND...")
let root=URL(fileURLWithPath:a[2]),out=URL(fileURLWithPath:a[3]),commands=Array(a[4...])
try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
let rom=try ROMImage.load(paths:[a[1]])
let layout=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("rom-layout.json"))) as! [String:Any]
precondition(rom.sha256==layout["rom_sha256"] as! String)
func machine(_ station:Int) throws -> Machine {
 var c=MachineConfiguration(model:.a440)
 c.cpu = .arm2;c.ramKB=4096;c.romPaths=[a[1]];c.hardDiscs=[];c.monitor="standard";c.powerOnKeys=[0x34];c.econetStation=station
 c.cmosSettings=[.init(byte:135,value:1),.drive(0),.init(byte:16,mask:0x10,value:0),.init(byte:185,value:10),.init(byte:196,value:12)]
 return try Machine(configuration:c,rom:rom)
}
let A=try machine(1),B=try machine(2)
let net=EconetNetwork();net.add(A);net.add(B)
func run(_ ticks:UInt64){net.run(ticks:ticks)}
let second:UInt64=24_000_000
func press(_ m:Machine,_ k:UInt8){m.keyDown(k);run(1_920_000);m.keyUp(k);run(2_400_000)}
func type(_ m:Machine,_ s:String){for ch in s{let (k,shift)=ArcKey.forCharacter(ch)!;if shift{m.keyDown(0x4c);run(720_000)};press(m,k);if shift{m.keyUp(0x4c);run(720_000)}};run(second)}
func json(_ x:Any,_ name:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(name+".json"))}
run(second*35)
for m in [A,B]{press(m,0x0c)};run(second*2)
var screens:[[String:[String]]]=[]
for c in commands {
 if c.hasPrefix("WAIT:"){run(second*UInt64(c.dropFirst(5))!)}
 else {let m=c.hasPrefix("A:") ? A:B;type(m,String(c.dropFirst(2))+"\n");run(second*3)}
 screens.append(["A":A.screenText,"B":B.screenText])
}
json(["status":"PASS","rom_sha256":rom.sha256,"commands":commands,"screens":screens,"stations":[1,2]],"result")
print("PASS")
