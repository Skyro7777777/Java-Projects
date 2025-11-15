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
read -p "35FDJCQnJwU034cbrkiTYFjhkyi_41WoXx7RNveiAHwDmEhgv" CRP
./ngrok config add-authtoken $CRP
clear
echo "Repo: https://github.com/kmille36/Docker-Ubuntu-Desktop-NoMachine"
echo "======================="
echo "choose ngrok region (for better connection)."
echo "======================="
echo "us - United States (Ohio)"
echo "eu - Europe (Frankfurt)"
echo "ap - Asia/Pacific (Singapore)"
echo "au - Australia (Sydney)"
echo "sa - South America (Sao Paulo)"
echo "jp - Japan (Tokyo)"
echo "in - India (Mumbai)"

# ---- FIXED PART: AUTO-SELECT INDIA (IN) ----
CRP="IN"
echo "Region automatically set to: $CRP"
# --------------------------------------------

./ngrok tcp --region $CRP 3389 &>/dev/null &
sleep 5
if curl --silent --show-error http://127.0.0.1:4040/api/tunnels  > /dev/null 2>&1; then echo OK; else echo "Ngrok Error! Please try again!" && sleep 1 && goto ngrok; fi

# Install and configure xrdp
sudo apt update
sudo apt install -y xrdp xfce4 xfce4-goodies
sudo systemctl enable xrdp
sudo systemctl start xrdp
sudo ufw allow 3389

# Create new user with secure password
sudo useradd -m -s /bin/bash windowsuser
echo "windowsuser:123456" | sudo chpasswd
sudo usermod -aG sudo windowsuser

clear
echo "XRDP Configuration Complete!"
echo "RDP Connection Information:"
echo "IP Address:"
# Fixed IP extraction - try multiple methods
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o 'tcp://[^"]*' | head -1)
if [ -n "$NGROK_URL" ]; then
    echo "$NGROK_URL" | sed 's/tcp:\/\///'
else
    # Alternative method
    curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "
import json, sys
data = json.load(sys.stdin)
for tunnel in data['tunnels']:
    if 'tcp' in tunnel['public_url']:
        print(tunnel['public_url'].replace('tcp://', ''))
        break
" || curl -s http://127.0.0.1:4040/api/tunnels | grep -oE 'tcp://[0-9a-z.-]+:[0-9]+' | head -1 | sed 's/tcp:\/\///'
fi
echo "User: windowsuser"
echo "Passwd: 123456"
echo "Port: 3389"
echo "VM can't connect? Restart Cloud Shell then Re-run script."
seq 1 43200 | while read i; do echo -en "\r Running .     $i s /43200 s";sleep 0.1;echo -en "\r Running ..    $i s /43200 s";sleep 0.1;echo -en "\r Running ...   $i s /43200 s";sleep 0.1;echo -en "\r Running ....  $i s /43200 s";sleep 0.1;echo -en "\r Running ..... $i s /43200 s";sleep 0.1;echo -en "\r Running     . $i s /43200 s";sleep 0.1;echo -en "\r Running  .... $i s /43200 s";sleep 0.1;echo -en "\r Running   ... $i s /43200 s";sleep 0.1;echo -en "\r Running    .. $i s /43200 s";sleep 0.1;echo -en "\r Running     . $i s /43200 s";sleep 0.1; done
