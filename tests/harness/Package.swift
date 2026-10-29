// swift-tools-version: 6.2
import PackageDescription
import Foundation
let core=ProcessInfo.processInfo.environment["MACARCH_CORE"]!
let package=Package(name:"ArcLibreTests",platforms:[.macOS(.v26)],dependencies:[.package(path:core)],targets:["PaletteProbe","GraphicsProbe","EditProbe","HardDiscProbe","BootProbe","CamProbe","KeyboardProbe","MessageProbe","TerritoryProbe","KeyboardSelectProbe","FloppyProbe","TextProbe","FilingProbe","WriteProbe","FPEProbe","RenderProbe","FontProbe","WimpProbe","MultiTaskProbe","DesktopProbe","DesktopROMProbe","DesktopLaunchProbe","PointerProbe","ClockProbe","DOSFSProbe","BasicRunProbe","FormatProbe","ARM3Probe","NetProbe","HardwareProbe","PrintProbe","NewIOProbe","NetFSProbe"].map{.executableTarget(name:$0,dependencies:["ProbeSupport",.product(name:"ArchimedesCore",package:"ArchimedesCore")])}+[.target(name:"ProbeSupport",dependencies:[.product(name:"ArchimedesCore",package:"ArchimedesCore")])],swiftLanguageModes:[.v5])
