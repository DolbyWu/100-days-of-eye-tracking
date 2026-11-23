import AppKit

let adjacent = Bundle.main.bundleURL.deletingLastPathComponent()
let configured = Bundle.main.object(forInfoDictionaryKey: "NeonBridgeDirectory") as? String
let folder = FileManager.default.isReadableFile(atPath: adjacent.appendingPathComponent("neon_bridge.py").path)
    ? adjacent : configured.map { URL(fileURLWithPath: $0, isDirectory: true) } ?? adjacent
let python = folder.appendingPathComponent(".venv/bin/python")
let bridge = folder.appendingPathComponent("neon_bridge.py")

final class Launcher: NSObject, NSApplicationDelegate {
    private let window = NSWindow(
        contentRect: NSRect(x: 0, y: 0, width: 540, height: 350),
        styleMask: [.titled, .closable, .miniaturizable, .resizable],
        backing: .buffered, defer: false)
    private let port = NSTextField(string: "9012")
    private let device = NSTextField()
    private let status = NSTextField(labelWithString: "已停止")
    private let log = NSTextView()
    private var process: Process?
    private var stopping = false
    private var startButton: NSButton!
    private var stopButton: NSButton!

    func applicationDidFinishLaunching(_ notification: Notification) {
        window.title = "TD-Neon"
        window.minSize = NSSize(width: 420, height: 250)
        port.stringValue = UserDefaults.standard.string(forKey: "port") ?? "9012"
        port.widthAnchor.constraint(equalToConstant: 76).isActive = true
        device.stringValue = UserDefaults.standard.string(forKey: "device") ?? ""
        device.placeholderString = "自动发现 / Auto-discover"
        device.widthAnchor.constraint(equalToConstant: 185).isActive = true
        startButton = NSButton(title: "启动", target: self, action: #selector(start))
        stopButton = NSButton(title: "停止", target: self, action: #selector(stop))
        stopButton.isEnabled = false
        let row = NSStackView(views: [NSTextField(labelWithString: "TouchDesigner 端口"), port, startButton, stopButton])
        row.spacing = 10
        let deviceRow = NSStackView(views: [NSTextField(labelWithString: "Companion IP"), device])
        deviceRow.spacing = 10

        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.borderType = .bezelBorder
        log.isEditable = false
        log.isVerticallyResizable = true
        log.autoresizingMask = [.width]
        log.font = .monospacedSystemFont(ofSize: 12, weight: .regular)
        scroll.documentView = log

        let layout = NSStackView(views: [row, deviceRow, status, scroll])
        layout.orientation = .vertical
        layout.alignment = .leading
        layout.spacing = 12
        layout.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(layout)
        let view = window.contentView!
        NSLayoutConstraint.activate([
            layout.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 20),
            layout.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -20),
            layout.topAnchor.constraint(equalTo: view.topAnchor, constant: 20),
            layout.bottomAnchor.constraint(equalTo: view.bottomAnchor, constant: -20),
            scroll.widthAnchor.constraint(equalTo: layout.widthAnchor)
        ])
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
        start()
    }

    @objc private func start() {
        guard process == nil else { return }
        guard let value = Int(port.stringValue), (1...65535).contains(value) else {
            status.stringValue = "端口必须是 1 到 65535 之间的整数。"
            return
        }
        guard FileManager.default.isExecutableFile(atPath: python.path),
              FileManager.default.isReadableFile(atPath: bridge.path) else {
            status.stringValue = "找不到 Day 12 桥接脚本或 .venv。请按 README 完成安装。"
            return
        }
        UserDefaults.standard.set(String(value), forKey: "port")
        let address = device.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        UserDefaults.standard.set(address, forKey: "device")
        log.string = ""
        let child = Process()
        let pipe = Pipe()
        child.executableURL = python
        var arguments = ["-u", bridge.path, "--port", String(value), "live", "--eye-features"]
        if !address.isEmpty { arguments += ["--device", address] }
        child.arguments = arguments
        child.currentDirectoryURL = folder
        child.standardOutput = pipe
        child.standardError = pipe
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if data.isEmpty {
                handle.readabilityHandler = nil
                return
            }
            let message = String(decoding: data, as: UTF8.self)
            DispatchQueue.main.async { self?.append(message) }
        }
        child.terminationHandler = { [weak self] finished in
            DispatchQueue.main.async {
                guard let self = self, self.process === finished else { return }
                self.status.stringValue = self.stopping ? "已停止" : "桥接已退出（\(finished.terminationStatus)）。请查看日志。"
                self.process = nil
                self.stopping = false
                self.startButton.isEnabled = true
                self.stopButton.isEnabled = false
                self.port.isEnabled = true
                self.device.isEnabled = true
            }
        }
        do {
            try child.run()
            process = child
            status.stringValue = "正在查找 Neon Companion…"
            port.isEnabled = false
            device.isEnabled = false
            startButton.isEnabled = false
            stopButton.isEnabled = true
        } catch {
            pipe.fileHandleForReading.readabilityHandler = nil
            status.stringValue = "启动失败。请查看日志。"
            append(error.localizedDescription)
        }
    }

    private func append(_ message: String) {
        log.string = String((log.string + message).suffix(24000))
        log.scrollToEndOfDocument(nil)
        if process != nil && !stopping {
            if message.contains("Neon disconnected:") {
                status.stringValue = "正在重新连接 Companion…"
            } else if message.contains("OSC ready:") {
                status.stringValue = "已连上 Companion · OSC 127.0.0.1:\(port.stringValue)"
            }
        }
    }

    @objc private func stop() {
        guard let child = process, child.isRunning else { return }
        stopping = true
        status.stringValue = "正在停止…"
        stopButton.isEnabled = false
        child.terminate()
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationWillTerminate(_ notification: Notification) { stop() }
}

if CommandLine.arguments.contains("--check") {
    let probe = Process()
    probe.executableURL = python
    probe.arguments = ["-c", "import cv2, pupil_labs.realtime_api; import pathlib, sys; p = pathlib.Path(sys.argv[1]); compile(p.read_bytes(), str(p), 'exec')", bridge.path]
    do {
        try probe.run()
        probe.waitUntilExit()
        exit(probe.terminationStatus)
    } catch {
        fputs("\(error)\n", stderr)
        exit(1)
    }
}

let app = NSApplication.shared
let launcher = Launcher()
app.setActivationPolicy(.regular)
app.delegate = launcher
app.run()
