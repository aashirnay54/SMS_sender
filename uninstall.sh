#!/bin/bash
PLIST="$HOME/Library/LaunchAgents/com.imessage-sender.plist"

launchctl unload "$PLIST" 2>/dev/null && echo "  ✓ Auto-start service removed." || echo "  Service was not running."
rm -f "$PLIST"
echo "  ✓ Done. The app folder can be deleted manually."
