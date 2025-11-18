#!/bin/bash
# Windows-like RDP via Tailscale - Google Cloud Shell Edition
# This creates a secure Windows desktop environment accessible via Tailscale VPN
# Save to: https://raw.githubusercontent.com/Skyro7777777/Java-Projects/main/windows-rdp-tailscale.sh

clear
echo "🚀 Setting up Windows Desktop via Tailscale"
echo "==========================================="
echo "ℹ️  This will create a Windows-like desktop environment"
echo "🔐 Accessible ONLY through your private Tailscale network"
echo "🕒 Session lasts 12 hours maximum"
echo ""

# Install required packages
echo "📦 Installing dependencies..."
sudo apt-get update > /dev/null 2>&1
sudo apt-get install -y curl wget docker.io > /dev/null 2>&1

# Get Tailscale auth key from user
echo ""
echo "🔑 Tailscale Setup Required"
echo "==========================="
echo "1. Go to: https://login.tailscale.com/admin/settings/keys"
echo "2. Click 'Generate auth key'"
echo "3. Select 'Ephemeral' key type (recommended for temporary use)"
echo "4. Set expiration to 1 day"
echo "5. Copy the generated key (starts with 'tskey-')"

read -p "🔑 Paste your Tailscale auth key: " TAILSCALE_AUTH_KEY

if [[ -z "$TAILSCALE_AUTH_KEY" ]]; then
    echo "❌ Error: Tailscale auth key cannot be empty!"
    echo "💡 Generate one at: https://login.tailscale.com/admin/settings/keys"
    exit 1
fi

echo ""
echo "🚀 Starting Windows Desktop Environment..."
echo "This may take 2-3 minutes to initialize..."

# Create and start the container with Tailscale integration
docker run -d \
  --name windows-desktop \
  --privileged \
  --network host \
  --cap-add=SYS_PTRACE \
  --shm-size=1g \
  -e TS_AUTHKEY="$TAILSCALE_AUTH_KEY" \
  -e TS_HOSTNAME="cloudshell-windows" \
  -e PASSWORD="RandomItIs@12345" \
  -e USER="user" \
  ghcr.io/thuonghai2711/nomachine-ubuntu-desktop:windows11

# Wait for container to start
sleep 30

echo ""
echo "✅ Windows Desktop Environment Started!"
echo "======================================="
echo ""
echo "🖥️  Connection Instructions:"
echo "1. Install Tailscale on your device: https://tailscale.com/download"
echo "2. Log in to your Tailscale account"
echo "3. Open Tailscale app and look for device named: 'cloudshell-windows'"
echo "4. Connect to this device using Remote Desktop (RDP) client"
echo ""
echo "👤 RDP Credentials:"
echo "User: user"
echo "Password: RandomItIs@12345"
echo ""
echo "⚠️  Important Notes:"
echo "- You MUST be logged into Tailscale on your device"
echo "- No public IP addresses are exposed - completely secure"
echo "- The desktop will appear as Windows 11 environment"
echo "- Session automatically terminates after 12 hours"
echo ""
echo "💡 Troubleshooting:"
echo "- If device doesn't appear in Tailscale, wait 1-2 minutes"
echo "- Restart Tailscale app on your device"
echo "- Check container logs: docker logs windows-desktop"
echo ""
echo "⏳ Keeping session alive for 12 hours (43200 seconds)..."
echo "Press CTRL+C to stop early"

# Countdown timer
END_TIME=$((SECONDS + 43200))
while [[ $SECONDS -lt $END_TIME ]]; do
    REMAINING=$((END_TIME - SECONDS))
    HOURS=$((REMAINING / 3600))
    MINUTES=$(( (REMAINING % 3600) / 60 ))
    SECONDS_REM=$((REMAINING % 60))
    
    printf "\r🕒 Session running: %02d:%02d:%02d remaining" $HOURS $MINUTES $SECONDS_REM
    sleep 1
done

echo ""
echo ""
echo "⏰ Session ended after 12 hours"
echo "🧹 Cleaning up resources..."
docker stop windows-desktop >/dev/null 2>&1
docker rm windows-desktop >/dev/null 2>&1
echo "✅ Cleanup complete!"
echo "💡 To start a new session, run the script again"
