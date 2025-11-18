#!/bin/bash

function goto
{
    label=$1
    cd 
    cmd=$(sed -n "/^:[[:blank:]][[:blank:]]*${label}/{:a;n;p;ba};" $0 | 
          grep -v ':$')
    eval "$cmd"
    exit
}

clear
echo "Repo: Custom RustDesk Ubuntu Desktop"
echo "======================="
echo "Starting Ubuntu XFCE container with RustDesk..."
docker run --rm -d --network host --privileged --name rustdesk-ubuntu --cap-add=SYS_PTRACE --shm-size=1g danchitnis/xrdp:ubuntu-xfce user 123456 no
sleep 5  # Wait for container to start

# Install RustDesk as root
docker exec -u root rustdesk-ubuntu apt update -qq >/dev/null 2>&1
docker exec -u root rustdesk-ubuntu apt install -y wget >/dev/null 2>&1
docker exec -u root rustdesk-ubuntu wget -q https://github.com/rustdesk/rustdesk/releases/download/1.4.3/rustdesk-1.4.3-x86_64.deb
docker exec -u root rustdesk-ubuntu dpkg -i rustdesk-1.4.3-x86_64.deb || docker exec -u root rustdesk-ubuntu apt install -f -y >/dev/null 2>&1
docker exec -u root rustdesk-ubuntu rm rustdesk-1.4.3-x86_64.deb

# Set permanent password and start service as user
docker exec -u user rustdesk-ubuntu rustdesk --password 123456
docker exec -u user rustdesk-ubuntu rustdesk --service &

sleep 5  # Wait for service to start

clear
echo "Download RustDesk client: https://rustdesk.com/download"
echo "======================="
echo Done! RustDesk Information:
echo ID:
docker exec -u user rustdesk-ubuntu rustdesk --get-id
echo Password: 123456
echo "Enter ID and Password in your RustDesk app to connect."
echo "Works from any country via relay servers."
echo "VM can't connect? Restart Cloud Shell then Re-run script."
seq 1 43200 | while read i; do echo -en "\r Running .     $i s /43200 s";sleep 0.1;echo -en "\r Running ..    $i s /43200 s";sleep 0.1;echo -en "\r Running ...   $i s /43200 s";sleep 0.1;echo -en "\r Running ....  $i s /43200 s";sleep 0.1;echo -en "\r Running ..... $i s /43200 s";sleep 0.1;echo -en "\r Running     . $i s /43200 s";sleep 0.1;echo -en "\r Running  .... $i s /43200 s";sleep 0.1;echo -en "\r Running   ... $i s /43200 s";sleep 0.1;echo -en "\r Running    .. $i s /43200 s";sleep 0.1;echo -en "\r Running     . $i s /43200 s";sleep 0.1; done
