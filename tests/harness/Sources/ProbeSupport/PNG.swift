// SPDX-License-Identifier: Apache-2.0
// Frame captures shared by the probes.
import ArchimedesCore
import Foundation
#if canImport(ImageIO)
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers
#endif

/// Saves a frame as a PNG: through ImageIO on macOS, as the probes always
/// have, and with the core's own encoder on hosts without ImageIO.
public func writePNG(_ f: VideoFrame, to url: URL) -> Bool {
    #if canImport(ImageIO)
    let rgba=f.pixels.flatMap{p in [UInt8(truncatingIfNeeded:p>>16),UInt8(truncatingIfNeeded:p>>8),UInt8(truncatingIfNeeded:p),UInt8(255)]}
    let provider=CGDataProvider(data:Data(rgba) as CFData)!
    let img=CGImage(width:f.width,height:f.height,bitsPerComponent:8,bitsPerPixel:32,bytesPerRow:f.width*4,space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGBitmapInfo(rawValue:CGImageAlphaInfo.last.rawValue),provider:provider,decode:nil,shouldInterpolate:false,intent:.defaultIntent)!
    let dest=CGImageDestinationCreateWithURL(url as CFURL,UTType.png.identifier as CFString,1,nil)!
    CGImageDestinationAddImage(dest,img,nil)
    return CGImageDestinationFinalize(dest)
    #else
    return (try? PNGEncoder.encode(f).write(to:url)) != nil
    #endif
}
