#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$(which python3)"
PLIST="$HOME/Library/LaunchAgents/com.imessage-sender.plist"

echo ""
echo "  iMessage Bulk Sender — Installer"
echo "  ─────────────────────────────────"
echo ""

# 1. Install Python dependencies
echo "  [1/3] Installing Python dependencies..."
"$PYTHON" -m pip install flask openpyxl --quiet

# 2. Write the launchd plist with the correct paths for this machine
echo "  [2/3] Installing auto-start service..."
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.imessage-sender</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$DIR/app.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/imessage-sender.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/imessage-sender.log</string>
</dict>
</plist>
EOF

# 3. Load it (starts the server right now and on every future login)
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "  [3/3] Starting server..."
sleep 2
open "http://localhost:5001"

echo ""
echo "  ✓ Done! The server now starts automatically when you log in."
echo "  ✓ Bookmark http://localhost:5001 — it will always be available."
echo ""
echo "  To uninstall, run:  ./uninstall.sh"
echo ""
