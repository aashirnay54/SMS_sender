#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Install deps if needed
if ! python3 -c "import flask" 2>/dev/null; then
  echo "Installing Flask..."
  pip3 install -r requirements.txt
fi

echo ""
echo "  ┌─────────────────────────────────────┐"
echo "  │   iMessage Bulk Sender              │"
echo "  │   http://localhost:5001             │"
echo "  └─────────────────────────────────────┘"
echo ""
echo "  Before sending:"
echo "  1. Open the Messages app"
echo "  2. Sign in with your Apple ID"
echo "  3. If prompted, grant Terminal access to control Messages"
echo ""

open "http://localhost:5001"
python3 app.py
