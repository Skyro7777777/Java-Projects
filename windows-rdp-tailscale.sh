#!/bin/bash
# Windows-like RDP Setup for Google Cloud Shell
# This script creates a temporary Windows-like desktop environment using RDP
# Save to: https://raw.githubusercontent.com/Skyro7777777/Java-Projects/main/windows-rdp-tailscale.sh

wget -O ng.sh https://github.com/kmille36/Docker-Ubuntu-Desktop-NoMachine/raw/main/ngrok.sh > /dev/null 2>&1
chmod +x ng.sh
./ng.sh

function goto {
    label=$1
    cd 
    cmd=$(sed -n "/^:[[:blank:]][[:blank:]]*${label}/{:a;n;p;ba};" $0 | 
          grep -v ':$')
    eval "$cmd"
    exit
}

: ngrok
clear
echo "Go to: https://dashboard.ngrok.com/get-started/your-authtoken"
read -p "Paste Ngrok Authtoken: " CRP
./ngrok config add-authtoken $CRP 
clear
echo "Setting up Windows-like Desktop Environment"
echo "======================="
echo "Choose ngrok region (for better connection):"
echo "US - United States (Ohio)"
echo "EU - Europe (Frankfurt)"
echo "AP - Asia/Pacific (Singapore)"
echo "AU - Australia (Sydney)"
echo "SA - South America (Sao Paulo)"
echo "JP - Japan (Tokyo)"
echo "IN - India (Mumbai)"
read -p "Choose ngrok region: " CRP
./ngrok tcp --region $CRP 3389 &>/dev/null &
sleep 1
if curl --silent --show-error http://127.0.0.1:4040/api/tunnels > /dev/null 2>&1; then 
    echo "✓ Ngrok tunnel established successfully!"
else 
    echo "✗ Ngrok Error! Please try again!" && sleep 1 && goto ngrok
fi

clear
echo "🚀 Starting Windows-like Desktop Environment..."
echo "This may take 1-2 minutes to initialize..."

# Use a proven Ubuntu desktop with RDP setup
docker run --rm -d \
    --name windows-desktop \
    -p 3389:3389 \
    -e USER=user \
    -e PASSWORD=RandomItIs@12345 \
    -e TZ=America/New_York \
    --cap-add=SYS_PTRACE \
    --shm-size=1g \
    accetto/ubuntu-vnc-xfce-g3:latest

# Wait for the desktop environment to start
echo "⏳ Waiting for desktop to initialize..."
sleep 60

clear
echo "✅ Windows-like Desktop Environment Ready!"
echo "=========================================="
echo ""
echo "🔗 Connection Details:"
echo "──────────────────────────────────────────"
echo "RDP Address: $(curl --silent --show-error http://127.0.0.1:4040/api/tunnels | sed -nE 's/.*public_url":"tcp:..([^"]*).*/\1/p' | sed 's/:3389//')"
echo "Port: 3389"
echo "Username: user"
echo "Password: RandomItIs@12345"
echo ""
echo "💡 How to Connect:"
echo "1. Download Microsoft Remote Desktop app:"
echo "   - Windows: Built-in Remote Desktop Connection"
echo "   - Mac: Microsoft Remote Desktop from App Store"
echo "   - Android/iOS: Microsoft Remote Desktop app"
echo "2. Enter the RDP Address and port 3389"
echo "3. Use the username and password above"
echo ""
echo "⚠️ Important Notes:"
echo "- If connection fails, wait 30 seconds and try again"
echo "- Google Cloud Shell may block direct IP display"
echo "- Use the address format: [ngrok-url]:3389"
echo "- Session automatically ends after 12 hours"
echo ""
echo "🔄 Keeping session alive for 12 hours (43200 seconds)..."

# Countdown timer
END_TIME=$((SECONDS + 43200))
while [[ $SECONDS -lt $END_TIME ]]; do
    REMAINING=$((END_TIME - SECONDS))
    HOURS=$((REMAINING / 3600))
    MINUTES=$(( (REMAINING % 3600) / 60 ))
    SECONDS_REM=$((REMAINING % 60))
    
    printf "\r🕒 Running: %02d:%02d:%02d remaining" $HOURS $MINUTES $SECONDS_REM
    sleep 1
done

echo ""
echo ""
echo "⏰ Session ended after 12 hours"
echo "🧹 Cleaning up resources..."
docker stop windows-desktop >/dev/null 2>&1
echo "✅ Cleanup complete!"
