// SPDX-License-Identifier: Apache-2.0
// Read-only cursor observations and isolated parity with the pinned C checker.
import Foundation
import ArchimedesCore
let a=CommandLine.arguments
precondition(a.count==5 || a.count==7,"PointerProbe inspect ROM SNAPSHOT OUTPUT | checks ROM SNAPSHOT MODULE_DIRECTORY CASES OUTPUT")
let inspect=a[1]=="inspect",rom=try ROMImage.load(paths:[a[2]])
let m=try Machine.restore(snapshot:Array(Data(contentsOf:URL(fileURLWithPath:a[3]))),rom:rom)
let out=URL(fileURLWithPath:a.last!);try FileManager.default.createDirectory(at:out,withIntermediateDirectories:true)
func json(_ x:Any,_ n:String){try! JSONSerialization.data(withJSONObject:x,options:[.prettyPrinted,.sortedKeys]).write(to:out.appendingPathComponent(n+".json"))}
func word(_ p:UInt32)->UInt32{m.memc.debugReadWord(p,space:.logical)!}
func write(_ p:UInt32,_ b:[UInt8]){for(i,v) in b.enumerated(){precondition(m.memc.debugWrite(p+UInt32(i),v,space:.logical))}}
if inspect {
 func capture(_ name:String)->[String:Any]{
  let timing=m.vidc.timingSummary,position=m.vidc.pointerPosition,frame=m.currentFrame
  var visible=0,matching=0
  for y in 0..<max(0,timing["cursorYEnd"]!-timing["cursorYStart"]!) {
   for x in 0..<32 {
    let w=m.memc.debugReadWord(m.memc.cinit+UInt32(y*8+(x/16)*4),space:.physical)!,v=Int(w>>UInt32((x%16)*2)&3)
    let fx=position.x+x,fy=position.y+y
    if v==0 || fx<0 || fy<0 || fx>=frame.width || fy>=frame.height{continue}
    let p=m.vidc.cursorPalette[v],rgb:UInt32=0xff000000|((p&15)*17<<16)|((p>>4&15)*17<<8)|((p>>8&15)*17)
    visible+=1;if frame.pixels[fy*frame.width+fx]==rgb{matching+=1}
   }
  }
  return ["name":name,"mouse":[word(1452),word(1456)],"shape":m.memc.debugRead(0x1578,space:.logical)!,"heights":(0..<4).map{m.memc.debugRead(0x156c+UInt32($0),space:.logical)!},"dma":m.memc.cinit,"cursor_mapping":m.memc.debugTranslate(0x1f03800)!,"timing":timing,"position":[position.x,position.y],"visible_pixels":visible,"matching_frame_pixels":matching,"palette":m.vidc.cursorPalette]
 }
 let before=capture("before");m.mouseMove(dx:-300,dy:150);m.debugger.resume();_=m.run(untilTick:m.ticks+24_000_000,maxInstructions:3_000_000);let after=capture("after")
 let visible=[before,after].allSatisfy{($0["visible_pixels"] as! Int)>0 && ($0["matching_frame_pixels"] as! Int)==($0["visible_pixels"] as! Int)}
 let moved=(before["position"] as! [Int]) != (after["position"] as! [Int])
 json(["status":visible && moved ? "PASS":"FAIL","rom_sha256":rom.sha256,"visible":visible,"moved":moved,"stages":[before,after]],"result")
 print(visible && moved ? "PASS: visible hardware cursor follows real input":"FAIL: invisible or stationary hardware cursor")
 exit(visible && moved ? 0:1)
}
let root=URL(fileURLWithPath:a[4]);let symbols=try JSONSerialization.jsonObject(with:Data(contentsOf:root.appendingPathComponent("symbols.json"))) as! [String:NSNumber]
let code=Array(try Data(contentsOf:root.appendingPathComponent("module.bin")));write(0x20000,code)
let cases=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:a[5]))) as! [[String:Any]]
let d=m.debugger;_=try d.addBreakpoint(.init(id:0,kind:.execute,start:0x8000));_=try d.addBreakpoint(.init(id:0,kind:.execute,start:4));_=try d.addBreakpoint(.init(id:0,kind:.execute,start:12,end:20))
var results:[[String:Any]]=[]
for row in cases {
 let w=(row["words"] as! [NSNumber]).map{$0.uint32Value};write(0x40000,w.flatMap{v in (0..<4).map{UInt8(truncatingIfNeeded:v>>($0*8))}})
 m.cpu.r[0]=0x40000;m.cpu.r[14]=0x8000
 let saved=(4..<13).map{m.cpu.r[$0]}
 m.cpu.pc=0x20000+symbols["check_sprite_area"]!.uint32Value;d.resume();_=m.run(untilTick:m.ticks+2400000,maxInstructions:100000)
 let expected=(row["expected"] as! NSNumber).uint32Value
 let pass=d.isStopped && m.cpu.pc==0x8000 && m.cpu.r[0]==expected && saved==(4..<13).map{m.cpu.r[$0]}
 results.append(["name":row["name"]!,"expected":expected,"actual":m.cpu.r[0],"pass":pass]);if !pass{json(results,"failure");fatalError("checker parity")}
}
json(["status":"PASS","cases":results,"source":"src/SprExtend/c/SpriteOp","scope":"Bounded fixtures, not exhaustive validation"],"result");print("PASS: \(results.count) original-C checker cases")
