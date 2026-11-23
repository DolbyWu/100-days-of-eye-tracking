#!/bin/bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
target="$(dirname "$here")/TD-Neon.app"
build="$(mktemp -d)"
trap 'rm -rf "$build"' EXIT
bundle="$build/TD-Neon.app"
mkdir -p "$bundle/Contents/MacOS" "$build/cache"
xcrun swiftc -module-cache-path "$build/cache" -framework AppKit "$here/NeonBridge.swift" -o "$bundle/Contents/MacOS/NeonBridge"
cat > "$bundle/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>NeonBridge</string>
<key>CFBundleIdentifier</key><string>art.gazefluid.neonbridge.day12</string>
<key>CFBundleName</key><string>TD-Neon</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>1</string>
<key>CFBundleShortVersionString</key><string>1.0</string>
<key>NSLocalNetworkUsageDescription</key><string>Find Neon Companion and read eye-tracking data on your local network.</string>
<key>NSBonjourServices</key><array><string>_http._tcp</string></array>
</dict></plist>
PLIST
plutil -insert NeonBridgeDirectory -string "$(dirname "$here")" "$bundle/Contents/Info.plist"
plutil -lint "$bundle/Contents/Info.plist"
/usr/bin/codesign --force --sign - "$bundle"
ditto "$bundle" "$target"
