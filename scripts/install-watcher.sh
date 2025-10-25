#!/bin/bash
# Installation script for Absolutely Right watcher service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_FILE="$HOME/Library/LaunchAgents/com.absolutelyright.watcher.plist"
LOG_DIR="$HOME/Library/Logs"

echo "Installing Absolutely Right Watcher Service"
echo "==========================================="
echo "Project directory: $PROJECT_DIR"
echo ""

# Check if secret is provided
SECRET="${1:-}"
if [ -z "$SECRET" ]; then
    echo "ERROR: Secret key required"
    echo "Usage: $0 <SECRET_KEY>"
    echo ""
    echo "Example:"
    echo "  $0 YOUR_SECRET_KEY_HERE"
    exit 1
fi

echo "Using secret: ${SECRET:0:10}***"
echo ""

# Unload existing service if running
if launchctl list | grep -q "com.absolutelyright.watcher"; then
    echo "Stopping existing service..."
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    sleep 1
fi

# Create LaunchAgent plist
echo "Creating launch agent configuration..."
cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.absolutelyright.watcher</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>-B</string>
        <string>$SCRIPT_DIR/watcher.py</string>
        <string>--secret</string>
        <string>$SECRET</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONDONTWRITEBYTECODE</key>
        <string>1</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>$LOG_DIR/absolutelyright-watcher.log</string>

    <key>StandardErrorPath</key>
    <string>$LOG_DIR/absolutelyright-watcher.error.log</string>
</dict>
</plist>
EOF

# Ensure log files exist
touch "$LOG_DIR/absolutelyright-watcher.log"
touch "$LOG_DIR/absolutelyright-watcher.error.log"

# Load the service
echo "Loading service..."
launchctl load "$PLIST_FILE"

# Wait for service to start
sleep 2

# Check if service is running
if launchctl list | grep -q "com.absolutelyright.watcher"; then
    PID=$(launchctl list | grep "com.absolutelyright.watcher" | awk '{print $1}')
    echo ""
    echo "✓ Service installed and running successfully!"
    echo "  PID: $PID"
    echo ""
    echo "Log files:"
    echo "  Output: $LOG_DIR/absolutelyright-watcher.log"
    echo "  Errors: $LOG_DIR/absolutelyright-watcher.error.log"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    tail -f $LOG_DIR/absolutelyright-watcher.log"
    echo "  Stop service: launchctl unload $PLIST_FILE"
    echo "  Start service: launchctl load $PLIST_FILE"
    echo "  Service status: launchctl list | grep absolutelyright"
else
    echo ""
    echo "✗ Service installation failed"
    echo "Check error log: $LOG_DIR/absolutelyright-watcher.error.log"
    exit 1
fi
