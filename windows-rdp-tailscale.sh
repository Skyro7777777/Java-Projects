#!/bin/bash

function goto {
    label=$1
    cd 
    cmd=$(sed -n "/^:[[:blank:]][[:blank:]]*${label}/{:a;n;p;ba};" $0 | 
          grep -v ':$')
    eval "$cmd"
    exit
}

: tailscale
clear
echo "Go to: https://login.tailscale.com/admin/authkeys"
echo "Create ephemeral auth key and paste below."
read -p "Paste Tailscale Auth Key: " KEY
read -p "Enter hostname (default: cloudshell-windows): " HOSTNAME
HOSTNAME=${HOSTNAME:-cloudshell-windows}
clear
echo "Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh
sudo nohup tailscaled --state=mem: --tun=userspace-networking &>/dev/null &
sleep 10
sudo tailscale up --authkey=$KEY --hostname=$HOSTNAME --accept-routes --accept-dns=false
sleep 5
TSIP=$(sudo tailscale ip -4 | head -n1 | awk '{print $2}')
if [ -z "$TSIP" ]; then
    echo "Tailscale Error! Please try again!"
    sleep 1
    goto tailscale
fi
mkdir -p windows
clear
echo "Starting Windows container (installation ~5-10min; may be slow in Cloud Shell without KVM)..."
docker run -d --rm --name windows-rdp --privileged \
  -p 3389:3389/tcp -p 3389:3389/udp \
  -e VERSION=10 -e RAM_SIZE=1G -e CPU_CORES=1 -e DISK_SIZE=20G \
  -v $PWD/windows:/storage \
  dockur/windows
sleep 300  # Wait for initial setup
clear
echo "Done! RDP Information:"
echo "Tailscale IP: $TSIP"
echo "Connect: $TSIP:3389 (Microsoft RDP client)"
echo "User: Docker"
echo "Pass: admin"
echo "Repo: https://github.com/dockur/windows"
echo "Session max 12h; restart if needed. Performance may vary."
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
