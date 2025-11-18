#!/bin/bash

# Run the Docker container (using the same base image for Ubuntu/XFCE desktop)
docker run --rm -d --network host --privileged --name rustdesk-xfce4 -e PASSWORD=RandomItIs@12345 -e USER=user --cap-add=SYS_PTRACE --shm-size=1g thuonghai2711/nomachine-ubuntu-desktop:windows10

# Wait for container to start
sleep 30

# Update and install dependencies
docker exec rustdesk-xfce4 apt update -qq
docker exec rustdesk-xfce4 apt install -y xserver-xorg-video-dummy wget

# Configure dummy display for headless
docker exec rustdesk-xfce4 sh -c 'cat > /etc/X11/xorg.conf.d/10-dummy.conf << "EOF"
Section "Device"
    Identifier "Dummy Device"
    Driver "dummy"
EndSection
Section "Monitor"
    Identifier "Dummy Monitor"
    HorizSync 28.0-80.0
    VertRefresh 48.0-75.0
    Modeline "1920x1080" 172.80 1920 2048 2248 2576 1080 1081 1084 1118 -hsync +vsync
    Option "PreferredMode" "1920x1080"
EndSection
Section "Screen"
    Identifier "Dummy Screen"
    Device "Dummy Device"
    Monitor "Dummy Monitor"
    DefaultDepth 24
    SubSection "Display"
        Modes "1920x1080"
        Depth 24
    EndSubSection
EndSection
EOF'

# Download and install latest RustDesk
docker exec rustdesk-xfce4 wget -q https://github.com/rustdesk/rustdesk/releases/download/1.4.3/rustdesk-1.4.3-x86_64.deb
docker exec rustdesk-xfce4 apt install -fy ./rustdesk-1.4.3-x86_64.deb

# Enable headless mode
docker exec rustdesk-xfce4 rustdesk --option allow-linux-headless Y

# Set password
docker exec rustdesk-xfce4 rustdesk --password RandomItIs@12345

# Get ID
ID=$(docker exec rustdesk-xfce4 rustdesk --get-id)

# Start RustDesk service in background
docker exec rustdesk-xfce4 rustdesk --service &

clear
echo "RustDesk Ready!"
echo "======================="
echo "Download client: https://rustdesk.com/download"
echo "ID: $ID"
echo "Password: RandomItIs@12345"
echo "Connect using RustDesk client."
echo "VM issues? Restart Cloud Shell and re-run."
echo "======================="

# Keep running for 12 hours
seq 1 43200 | while read i; do
    echo -en "\r Running .     $i s /43200 s"; sleep 0.1
    echo -en "\r Running ..    $i s /43200 s"; sleep 0.1
    echo -en "\r Running ...   $i s /43200 s"; sleep 0.1
    echo -en "\r Running ....  $i s /43200 s"; sleep 0.1
    echo -en "\r Running ..... $i s /43200 s"; sleep 0.1
    echo -en "\r Running     . $i s /43200 s"; sleep 0.1
    echo -en "\r Running  .... $i s /43200 s"; sleep 0.1
    echo -en "\r Running   ... $i s /43200 s"; sleep 0.1
    echo -en "\r Running    .. $i s /43200 s"; sleep 0.1
    echo -en "\r Running     . $i s /43200 s"; sleep 0.1
done
