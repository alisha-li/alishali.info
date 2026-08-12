#!/bin/zsh
# Install the Anki sync job as a launchd agent and retire the old cron entry.
#
# launchd is used instead of cron because it runs missed calendar jobs after the
# Mac wakes, it captures stdout/stderr to files, and `launchctl list` shows the
# last exit status -- none of which cron gave us, which is why the old job could
# stop working for eleven months without leaving a trace.

set -e

REPO="${0:A:h:h}"
LABEL="com.alishali.anki-sync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
# Resolve to the real interpreter. `command -v python3` can return a pyenv shim,
# which is a shell script that needs a login environment launchd does not give it
# ("pyenv: cannot change working directory to ''").
PYTHON="$(python3 -c 'import sys; print(sys.executable)')"
[ -x "$PYTHON" ] || PYTHON=/usr/bin/python3

mkdir -p "$REPO/logs" "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$REPO/scripts/update_anki.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
    <key>StartCalendarInterval</key>
    <array>
        <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>13</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
        <dict><key>Hour</key><integer>21</integer><key>Minute</key><integer>0</integer></dict>
    </array>
    <key>StandardOutPath</key>
    <string>$REPO/logs/launchd.out</string>
    <key>StandardErrorPath</key>
    <string>$REPO/logs/launchd.err</string>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$PLIST"

echo "installed $LABEL -> $REPO/scripts/update_anki.py"
echo "runs at 09:00, 13:00, 17:00, 21:00 (four tries a day, so Anki only has to be open for one)"

# Retire the old cron entry, keeping a backup.
if crontab -l 2>/dev/null | grep -q "alishali.info"; then
    crontab -l > "$REPO/logs/crontab.backup.$(date +%Y%m%d)"
    crontab -l | grep -v "alishali.info" | crontab -
    echo "removed old cron entry (backup in logs/)"
fi

echo
echo "check it:      launchctl list | grep $LABEL"
echo "run it now:    launchctl kickstart -k gui/$UID/$LABEL"
echo "read the log:  tail -f $REPO/logs/update.log"
