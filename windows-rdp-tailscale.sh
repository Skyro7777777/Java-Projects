#!/bin/bash set -euo pipefail

-------------------------

USER CONFIGURATION

-------------------------

Paste your ngrok authtoken between the quotes below. If you leave it empty,

the script will prompt you to paste it at runtime.

NGROK_AUTHTOKEN="35FDJCQnJwU034cbrkiTYFjhkyi_41WoXx7RNveiAHwDmEhgv"   # <-- paste token here, e.g. "1a2b3C..."

Default ngrok region (auto-selected). "in" chooses India (Mumbai).

other valid values: us, eu, ap, au, sa, jp, in

NGROK_REGION="in"

Default system locale to auto-select "UK English" (en_GB.UTF-8)

TARGET_LOCALE="en_GB.UTF-8"

Make apt non-interactive so you won't be asked during installs

export DEBIAN_FRONTEND=noninteractive

-------------------------

helper: goto (keeps your original behaviour)

-------------------------

function goto { label=$1 cd cmd=$(sed -n "/^:[[:blank:]][[:blank:]]*${label}/{:a;n;p;ba};" "$0" | grep -v ':$') eval "$cmd" exit }

: ngrok clear

Prepare locale (auto-select UK English so "language prompts" are satisfied)

Install locales if missing and generate en_GB.UTF-8 quietly

sudo apt-get update -y >/dev/null sudo apt-get install -y locales >/dev/null if ! locale -a | grep -q "${TARGET_LOCALE}"; then sudo locale-gen "${TARGET_LOCALE}" >/dev/null || true sudo update-locale LANG="${TARGET_LOCALE}" LC_ALL="${TARGET_LOCALE}" >/dev/null || true fi export LANG="${TARGET_LOCALE}" export LC_ALL="${TARGET_LOCALE}"

Download the ngrok installer script (keeps original line)

wget -O ng.sh https://github.com/kmille36/Docker-Ubuntu-Desktop-NoMachine/raw/main/ngrok.sh > /dev/null 2>&1 || true chmod +x ng.sh || true

Run the downloaded script in background if it exists - ignore errors

if [ -f ./ng.sh ]; then ./ng.sh >/dev/null 2>&1 || true fi

Add authtoken: use embedded token if provided, otherwise prompt the user

if [ -n "${NGROK_AUTHTOKEN}" ]; then echo "Using embedded NGROK_AUTHTOKEN (no prompt)." ./ngrok config add-authtoken "${NGROK_AUTHTOKEN}" >/dev/null 2>&1 || true else clear echo "Go to: https://dashboard.ngrok.com/get-started/your-authtoken" read -p "Paste Ngrok Authtoken: " CRP ./ngrok config add-authtoken "$CRP" >/dev/null 2>&1 || true fi

clear echo "Repo: https://github.com/kmille36/Docker-Ubuntu-Desktop-NoMachine" echo "=======================" echo "Ngrok region is auto-selected to: ${NGROK_REGION}" echo "(change NGROK_REGION at the top of the script if you want a different region)" echo "======================="

Start ngrok TCP tunnel on port 3389 using the default region (no interactive prompt)

region value is case-insensitive; ensure it is in the expected short form

./ngrok tcp --region ${NGROK_REGION} 3389 &>/dev/null & sleep 5

Check if ngrok's local API is responding, otherwise retry label

if curl --silent --show-error http://127.0.0.1:4040/api/tunnels  > /dev/null 2>&1; then echo "Ngrok started OK" else echo "Ngrok Error! Trying again..." sleep 1 goto ngrok fi

-------------------------

Install and configure xrdp (non-interactive)

-------------------------

sudo apt-get update -y sudo apt-get install -y xrdp xfce4 xfce4-goodies >/dev/null sudo systemctl enable xrdp sudo systemctl start xrdp sudo ufw allow 3389 || true

-------------------------

Create new user with secure password (customise here if you want)

-------------------------

USERNAME="windowsuser" PASSWORD="123456"   # change if desired if ! id -u "$USERNAME" >/dev/null 2>&1; then sudo useradd -m -s /bin/bash "$USERNAME" echo "${USERNAME}:${PASSWORD}" | sudo chpasswd sudo usermod -aG sudo "$USERNAME" fi

clear echo "XRDP Configuration Complete!" echo "RDP Connection Information:" echo "IP Address:"

-------------------------

Fixed IP extraction - robust JSON parsing while avoiding external deps

-------------------------

NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 - <<'PY' import sys, json try: data = json.load(sys.stdin) for t in data.get('tunnels', []): pu = t.get('public_url','') if pu.startswith('tcp://'): print(pu.replace('tcp://','')) sys.exit(0) except Exception: pass sys.exit(1) PY ) || true

if [ -n "$NGROK_URL" ]; then echo "$NGROK_URL" else # fallback grep-based extraction NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -oE 'tcp://[0-9a-zA-Z.-]+:[0-9]+' | head -1 | sed 's|tcp://||') || true echo "${NGROK_URL:-Could not determine ngrok URL - check ngrok logs}" fi

echo "User: ${USERNAME}" echo "Passwd: ${PASSWORD}" echo "Port: 3389" echo "VM can't connect? Restart Cloud Shell then Re-run script."

Keep the process alive with a simple spinner so the script doesn't exit immediately

seq 1 43200 | while read i; do echo -en "\r Running .     $i s /43200 s"; sleep 0.1 echo -en "\r Running ..    $i s /43200 s"; sleep 0.1 echo -en "\r Running ...   $i s /43200 s"; sleep 0.1 echo -en "\r Running ....  $i s /43200 s"; sleep 0.1 echo -en "\r Running ..... $i s /43200 s"; sleep 0.1 echo -en "\r Running     . $i s /43200 s"; sleep 0.1 echo -en "\r Running  .... $i s /43200 s"; sleep 0.1 echo -en "\r Running   ... $i s /43200 s"; sleep 0.1 echo -en "\r Running    .. $i s /43200 s"; sleep 0.1 echo -en "\r Running     . $i s /43200 s"; sleep 0.1 done
