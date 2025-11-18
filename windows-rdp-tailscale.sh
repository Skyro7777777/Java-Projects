#!/bin/bash
# RustDesk Windows RDP Setup for Google Cloud Shell
# This script creates a temporary Windows-like RDP environment using RustDesk instead of NoMachine

wget -O ng.sh https://github.com/kmille36/Docker-Ubuntu-Desktop-NoMachine/raw/main/ngrok.sh > /dev/null 2>&1
chmod +x ng.sh
./ng.sh

function goto
{
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
echo "Repo: https://github.com/linuxserver/rustdesk"
echo "======================="
echo "choose ngrok region (for better connection)."
echo "======================="
echo "US - United States (Ohio)"
echo "EU - Europe (Frankfurt)"
echo "AP - Asia/Pacific (Singapore)"
echo "AU - Australia (Sydney)"
echo "SA - South America (Sao Paulo)"
echo "JP - Japan (Tokyo)"
echo "IN - India (Mumbai)"
read -p "choose ngrok region: " CRP
./ngrok tcp --region $CRP 21116 &>/dev/null &
sleep 1
if curl --silent --show-error http://127.0.0.1:4040/api/tunnels > /dev/null 2>&1; then 
    echo "Ngrok tunnel established successfully!"
else 
    echo "Ngrok Error! Please try again!" && sleep 1 && goto ngrok
fi

# Run RustDesk Docker container with Windows-like environment
clear
echo "Starting RustDesk Windows Desktop Environment..."
docker run --rm -d \
    --name rustdesk-windows \
    -e PUID=1000 \
    -e PGID=1000 \
    -e TZ=America/New_York \
    -e PASSWORD=RandomItIs@12345 \
    -e SUBFOLDER=/ \
    -e CUSTOM_USER=user \
    -p 21115-21119:21115-21119 \
    -p 3000:3000 \
    --network host \
    --privileged \
    --cap-add=SYS_PTRACE \
    --shm-size=1g \
    linuxserver/rustdesk:latest

# Wait for RustDesk to initialize
echo "Waiting for RustDesk to initialize..."
sleep 15

clear
echo "RustDesk Windows Desktop Setup Complete!"
echo "==============================="
echo "Connection Information:"
echo "==============================="
echo "RustDesk ID: $(docker logs rustdesk-windows 2>&1 | grep -oP 'ID:\s*\K\d+' | head -1 || echo 'Check logs manually')"
echo "RustDesk Password: RandomItIs@12345"
echo ""
echo "To connect:"
echo "1. Download RustDesk client from https://rustdesk.com/"
echo "2. Enter the ID and password above"
echo "3. You'll get a Windows-like desktop environment"
echo ""
echo "Note: If ID doesn't appear above, check container logs with:"
echo "docker logs rustdesk-windows"
echo ""
echo "VM can't connect? Restart Cloud Shell then Re-run script."
echo ""
echo "Session will run for 12 hours (43200 seconds)"

# Countdown timer
seq 1 43200 | while read i; do 
    echo -en "\r Running .     $i s /43200 s";sleep 0.1
    echo -en "\r Running ..    $i s /43200 s";sleep 0.1
    echo -en "\r Running ...   $i s /43200 s";sleep 0.1
    echo -en "\r Running ....  $i s /43200 s";sleep 0.1
    echo -en "\r Running ..... $i s /43200 s";sleep 0.1
    echo -en "\r Running     . $i s /43200 s";sleep 0.1
    echo -en "\r Running  .... $i s /43200 s";sleep 0.1
    echo -en "\r Running   ... $i s /43200 s";sleep 0.1
    echo -en "\r Running    .. $i s /43200 s";sleep 0.1
    echo -en "\r Running     . $i s /43200 s";sleep 0.1
done

# Cleanup on exit
echo "Stopping RustDesk container..."
docker stop rustdesk-windows >/dev/null 2>&1
echo "Session ended. Container cleaned up."
