#!/bin/bash

function goto {
    label=$1
    cmd=$(sed -n "/^:[[:blank:]][[:blank:]]*${label}/{:a;n;p;ba};" $0 | 
          grep -v ':$')
    eval "$cmd"
    exit
}

cat > Dockerfile << 'EOF'
FROM ubuntu:22.04

RUN
    apt-get install -y ca-certificates gnupg lsb-release && \
    apt-get install -y ubuntu-desktop xserver-xorg-video-dummy lightdm wget sudo dbus && \
    rm -rf /var/lib/apt/lists/*

# Configure dummy display
RUN mkdir -p /etc/X11/xorg.conf.d && \
    echo 'Section "Device" Identifier "dummy" Driver "dummy" VideoRam 256000 EndSection Section "Screen" Identifier "Dummy Screen" Device "dummy" DefaultDepth 24 SubSection "Display" Depth 24 Virtual 1920 1080 EndSubSection EndSection' > /etc/X11/xorg.conf.d/10-dummy.conf

# Install RustDesk
RUN VERSION="1.4.3" && \
    wget https://github.com/rustdesk/rustdesk/releases/download/v${VERSION}/rustdesk-${VERSION}-x86_64.deb && \
    dpkg -i rustdesk-${VERSION}-x86_64.deb || apt-get install -f -y && \
    rm rustdesk-${VERSION}-x86_64.deb

# Enable headless
RUN rustdesk --option allow-linux-headless Y

# Create user
RUN useradd -m -s /bin/bash -G sudo user && \
    echo "user:123456" | chpasswd && \
    echo "user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# LightDM autologin
RUN echo '[Seat:*] autologin-user=user autologin-user-timeout=0' > /etc/lightdm/lightdm.conf.d/autologin.conf

# Enable lightdm
RUN ln -sf /lib/systemd/system/lightdm.service /etc/systemd/system/display-manager.service

CMD ["/lib/systemd/systemd"]
EOF

docker build -t rustdesk-ubuntu-gnome .

docker run -d \
  --privileged \
  --network host \
  --shm-size=1g \
  --cap-add=SYS_PTRACE \
  --tmpfs /tmp \
  --tmpfs /run \
  --tmpfs /run/lock \
  -v /sys/fs/cgroup:/sys/fs/cgroup:ro \
  --name rustdesk-vm \
  rustdesk-ubuntu-gnome

sleep 60

docker exec rustdesk-vm systemctl daemon-reload
docker exec rustdesk-vm systemctl enable lightdm
docker exec rustdesk-vm systemctl start lightdm

sleep 20

docker exec rustdesk-vm rustdesk --password 123456

ID=$(docker exec rustdesk-vm rustdesk --get-id)

clear
echo "RustDesk Information:"
echo "ID: $ID"
echo "Password: 123456"
echo "======================="
echo "Download RustDesk client: https://rustdesk.com/download"
echo "Enter ID and password to connect."
echo "======================="
echo "VM can't connect? Restart Cloud Shell then Re-run script."

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
