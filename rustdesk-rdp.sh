#!/bin/bash

# Download ngrok
wget -q -O ngrok.tgz https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xzf ngrok.tgz
chmod +x ngrok

clear
echo "RustDesk Windows-like RDP Setup"
echo "================================="
echo "Go to: https://dashboard.ngrok.com/get-started/your-authtoken"
read -p "Paste Ngrok Authtoken: " CRP
./ngrok config add-authtoken $CRP

clear
echo "Choose ngrok region:"
echo "us, eu, ap, au, sa, jp, in"
read -p "Region: " REGION

# Start ngrok for RustDesk
./ngrok tcp --region $REGION 21116 &>/dev/null &
sleep 3

# Wait for ngrok to be ready
until curl -s http://127.0.0.1:4040/api/tunnels > /dev/null; do
    sleep 1
done

# Get RustDesk connection info
RUSTDESK_INFO=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o 'tcp://[^"]*')
RUSTDESK_ADDR=$(echo $RUSTDESK_INFO | sed 's/tcp:\/\///')

echo "Starting RustDesk server..."

# Run Docker container with desktop and RustDesk
docker run -d \
    --name windows-rdp \
    --privileged \
    --shm-size=1g \
    -p 21115:21115 \
    -p 21116:21116 \
    -p 21116:21116/udp \
    -p 21117:21117 \
    -p 21118:21118 \
    -p 21119:21119 \
    -e RUSTDESK_PASSWORD="RandomItIs@12345" \
    -e AUDIO_GID=$(getent group audio | cut -d: -f3) \
    -e VIDEO_GID=$(getent group video | cut -d: -f3) \
    --restart unless-stopped \
    rustdesk/rustdesk-server:latest

clear
echo "✅ Setup Complete!"
echo "=================="
echo "📡 RustDesk Server: $RUSTDESK_ADDR"
echo "🔑 Password: RandomItIs@12345"
echo ""
echo "📥 Download RustDesk: https://rustdesk.com/download"
echo ""
echo "🔧 Connection Instructions:"
echo "1. Install RustDesk on your local machine"
echo "2. In RustDesk settings, set ID Server to: $RUSTDESK_ADDR"
echo "3. The RustDesk ID will be generated automatically"
echo "4. Share that ID with others to connect"
echo ""
echo "⏳ The RustDesk ID will appear once fully started (1-2 minutes)"

# Display countdown
for i in {1..120}; do
    echo -ne "⏰ Waiting for RustDesk to start... $i/120 seconds\r"
    sleep 1
done

echo ""
echo "🚀 RustDesk should be ready now!"
echo "📋 Check the RustDesk ID in the application"
echo "💡 Restart Cloud Shell if connection issues occur"
