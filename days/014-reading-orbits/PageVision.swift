import AppKit
import Vision
import CoreText
import ImageIO

struct Word: Codable {
    let text: String
    let box: [Double]  // left, top, right, bottom in normalized scene coordinates
}

func recognize(_ data: Data) throws -> [Word] {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.recognitionLanguages = ["en-US", "zh-Hans", "zh-Hant"]
    try VNImageRequestHandler(data: data).perform([request])
    var words = [Word]()
    for observation in request.results ?? [] {
        guard let candidate = observation.topCandidates(1).first else { continue }
        let line = candidate.string
        var ranges = [Range<String.Index>]()
        for field in line.split(whereSeparator: { $0.isWhitespace }) {
            let bounds = field.startIndex..<field.endIndex
            if field.unicodeScalars.contains(where: { (0x3400...0x9fff).contains($0.value) }) {
                line.enumerateSubstrings(in: bounds, options: [.byWords]) { _, r, _, _ in ranges.append(r) }
            } else {
                ranges.append(bounds)
            }
        }
        for range in ranges {
            guard let rect = try candidate.boundingBox(for: range)?.boundingBox else { continue }
            words.append(Word(text: String(line[range]), box: [rect.minX, 1-rect.maxY, rect.maxX, 1-rect.minY]))
        }
    }
    return words
}

// Use Core Text font fallback for non-Latin alphabets. White glyphs on black.
func atlas(_ labels: [String]) throws -> Data {
    let w=256, h=48, cols=8, rows=max(1,(labels.count+cols-1)/cols)
    guard let ctx=CGContext(data:nil, width:w*cols,height:h*rows,bitsPerComponent:8,
                            bytesPerRow:w*cols, space:CGColorSpaceCreateDeviceGray(),
                            bitmapInfo:CGImageAlphaInfo.none.rawValue) else { throw CocoaError(.fileWriteUnknown) }
    ctx.setFillColor(gray:0,alpha:1)
    ctx.fill(CGRect(x:0,y:0,width:w*cols,height:h*rows))
    let attributes: [NSAttributedString.Key:Any] = [.font:NSFont.systemFont(ofSize:31,weight:.medium),
                                                       .foregroundColor:NSColor.white]
    for (i,label) in labels.enumerated() {
        let line=CTLineCreateWithAttributedString(NSAttributedString(string:label,attributes:attributes))
        let width=CTLineGetTypographicBounds(line,nil,nil,nil)
        ctx.saveGState()
        ctx.translateBy(x: CGFloat(i%cols*w+2), y:CGFloat((rows-1-i/cols)*h+11))
        ctx.scaleBy(x:min(1, CGFloat(w-4)/max(1,width)),y:1)
        ctx.textPosition = .zero
        CTLineDraw(line,ctx)
        ctx.restoreGState()
    }
    guard let image=ctx.makeImage(), let png=NSBitmapImageRep(cgImage:image).representation(using:.png,properties:[:])
    else { throw CocoaError(.fileWriteUnknown) }
    return png
}

do {
    let input = FileHandle.standardInput.readDataToEndOfFile()
    let result: Data
    if CommandLine.arguments.contains("--atlas") {
        result = try atlas(JSONDecoder().decode([String].self,from:input))
    } else {
        result = try JSONEncoder().encode(recognize(input))
    }
    try FileHandle.standardOutput.write(contentsOf:result)
} catch {
    FileHandle.standardError.write(Data(error.localizedDescription.utf8))
    exit(1)
}
