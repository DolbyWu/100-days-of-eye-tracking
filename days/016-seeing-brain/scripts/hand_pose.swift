import Foundation
import CoreGraphics
import Vision

// With no arguments, continue to serve older Day 13 projects.
let args = CommandLine.arguments
let width = args.count > 1 ? Int(args[1]) ?? 0 : 256
let height = args.count > 2 ? Int(args[2]) ?? 0 : 144
guard (1...2048).contains(width), (1...2048).contains(height) else { exit(2) }
let bytes = width * height * 4
let request = VNDetectHumanHandPoseRequest()
request.maximumHandCount = 2
let joints: [VNHumanHandPoseObservation.JointName] = [
    .wrist, .thumbCMC, .thumbMP, .thumbIP, .thumbTip,
    .indexMCP, .indexPIP, .indexDIP, .indexTip,
    .middleMCP, .middlePIP, .middleDIP, .middleTip,
    .ringMCP, .ringPIP, .ringDIP, .ringTip,
    .littleMCP, .littlePIP, .littleDIP, .littleTip
]
let input = FileHandle.standardInput
let output = FileHandle.standardOutput
while true {
    var data = Data()
    while data.count < bytes {
        guard let part = try input.read(upToCount: bytes - data.count), !part.isEmpty else { exit(0) }
        data.append(part)
    }
    let provider = CGDataProvider(data: data as CFData)!
    let image = CGImage(width: width, height: height, bitsPerComponent: 8, bitsPerPixel: 32,
                        bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipLast.rawValue),
                        provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent)!
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    var hands: [String:[[Double]]] = [:]
    do {
        try handler.perform([request])
        for hand in request.results ?? [] {
            let side: String
            switch hand.chirality {
            case .left: side = "left"
            case .right: side = "right"
            default: continue
            }
            hands[side] = joints.map { joint in
                guard let p = try? hand.recognizedPoint(joint) else { return [0,0,0] }
                return [p.location.x,p.location.y,Double(p.confidence)]
            }
        }
    }
    catch {
        var message = try JSONEncoder().encode(["error": error.localizedDescription])
        message.append(10)
        try output.write(contentsOf: message)
        continue
    }
    var result = try JSONEncoder().encode(hands)
    result.append(10)
    try output.write(contentsOf: result)
}
