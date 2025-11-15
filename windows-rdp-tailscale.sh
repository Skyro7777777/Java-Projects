#!/bin/bash
set -euo pipefail

# -------------------------
# Configuration (edit here)
# -------------------------
# Paste your ngrok authtoken between the quotes if you don't want to be prompted:
NGROK_AUTHTOKEN="35FDJCQnJwU034cbrkiTYFjhkyi_41WoXx7RNveiAHwDmEhgv"

# You can also set NGROK_TOKEN env var before running and it will be used if above is empty.
: "${NGROK_AUTHTOKEN:=${NGROK_TOKEN:-}}"

# Default ngrok region (change if you like): us, eu, ap, au, sa, jp, in
NGROK_REGION="${NGROK_REGION:-IN}"
# -------------------------

# helper goto (kept from original script)
function goto {
  label=$1
  cd
  cmd=$(sed -n "/^:[[:blank:]][[:blank:]]*${label}/{:a;n;p;ba};" "$0" | grep -v ':$')
  eval "$cmd"
  exit
}

# If ngrok binary is not present, try to fetch/install it
ensure_ngrok() {
  if ! command -v ngrok >/dev/null 2>&1; then
    echo "ngrok not found: attempting installer..."
    # try to fetch a common install script if network allows (keeps original behavior)
    # if you already downloaded ng.sh earlier, skip this.
    if [ -f ./ng.sh ]; then
      chmod +x ./ng.sh
      ./ng.sh
    else
      echo "No local ng.sh found. Please install ngrok or place ./ngrok binary in the current directory."
      # continue: user might already have ngrok in PATH after earlier steps
    fi
  fi
}

# ---------
# NGROK
# ---------
: ngrok
clear
ensure_ngrok

if [ -z "$NGROK_AUTHTOKEN" ]; then
  echo "Go to: https://dashboard.ngrok.com/get-started/your-authtoken"
  read -r -p "Paste Ngrok Authtoken: " NGROK_AUTHTOKEN
fi

# add authtoken (works with ngrok v3 CLI)
if ! ngrok config add-authtoken "$NGROK_AUTHTOKEN" >/dev/null 2>&1; then
  # try legacy command location (if binary named ./ngrok)
  if [ -x ./ngrok ]; then
    ./ngrok config add-authtoken "$NGROK_AUTHTOKEN" >/dev/null 2>&1 || true
  else
    echo "Warning: failed to add ngrok authtoken. Check ngrok binary/permissions."
  fi
fi

clear
echo "Repo: https://github.com/kmille36/Docker-Ubuntu-Desktop-NoMachine"
echo "======================="
echo "Using ngrok region: $NGROK_REGION"
echo "======================="

# start ngrok tcp tunnel in background
# redirect logs to a file for debugging
NGROK_LOG="$HOME/ngrok.log"
if command -v ngrok >/dev/null 2>&1; then
  ngrok tcp --region "$NGROK_REGION" 3389 >"$NGROK_LOG" 2>&1 &
else
  ./ngrok tcp --region "$NGROK_REGION" 3389 >"$NGROK_LOG" 2>&1 &
fi

sleep 5
if curl --silent --show-error http://127.0.0.1:4040/api/tunnels >/dev/null 2>&1; then
  echo "Ngrok started."
else
  echo "Ngrok Error! Please try again!"
  sleep 1
  goto ngrok
fi

# ---------------------------
# System locale / keyboard
# ---------------------------
# Make apt noninteractive to avoid prompts
export DEBIAN_FRONTEND=noninteractive

# Update and install packages needed for locale & keyboard config
sudo apt update -y
# install locales and keyboard packages first so language/keyboard will be preconfigured
sudo apt install -y locales console-setup keyboard-configuration

# Generate and set UK locale (en_GB.UTF-8)
sudo locale-gen en_GB.UTF-8 >/dev/null 2>&1 || true
sudo update-locale LANG=en_GB.UTF-8

# Configure keyboard to English (UK) non-interactively
sudo bash -c 'cat > /etc/default/keyboard <<EOF
XKBMODEL="pc105"
XKBLAYOUT="gb"
XKBVARIANT=""
XKBOPTIONS=""
BACKSPACE="guess"
EOF'

# Reconfigure keyboard package non-interactively (may return non-zero in some containers, ignore errors)
sudo dpkg-reconfigure -f noninteractive keyboard-configuration || true

# ensure LANG exported in this session
export LANG=en_GB.UTF-8
export LC_ALL=en_GB.UTF-8

# ---------------------------
# Install and configure xrdp
# ---------------------------
sudo apt install -y xrdp xfce4 xfce4-goodies
sudo systemctl enable xrdp
sudo systemctl start xrdp
sudo ufw allow 3389 >/dev/null 2>&1 || true

# Create new user with secure password (change password below if you want)
USERNAME="windowsuser"
PASSWORD="123456"

if ! id -u "$USERNAME" >/dev/null 2>&1; then
  sudo useradd -m -s /bin/bash "$USERNAME"
fi
echo "${USERNAME}:${PASSWORD}" | sudo chpasswd
sudo usermod -aG sudo "$USERNAME"

clear
echo "XRDP Configuration Complete!"
echo "RDP Connection Information:"
echo "IP Address:"

# Get public ngrok tcp address from the API (robust extraction)
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o 'tcp://[^"]*' | head -1 || true)
if [ -n "$NGROK_URL" ]; then
  echo "$NGROK_URL" | sed 's/tcp:\/\///'
else
  # fallback to JSON parsing using python if available
  if command -v python3 >/dev/null 2>&1; then
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python3 -c "
import json,sys
try:
    data=json.load(sys.stdin)
    for t in data.get('tunnels',[]):
        pu=t.get('public_url','')
        if pu.startswith('tcp://'):
            print(pu.replace('tcp://',''))
            break
except Exception:
    pass
")
  fi
  if [ -n "$NGROK_URL" ]; then
    echo "$NGROK_URL"
  else
    # best-effort grep fallback
    curl -s http://127.0.0.1:4040/api/tunnels | grep -oE 'tcp://[0-9a-z.-]+:[0-9]+' | head -1 | sed 's/tcp:\/\///' || echo "ngrok tunnel not found"
  fi
fi

echo "User: $USERNAME"
echo "Passwd: $PASSWORD"
echo "Port: 3389"
echo "VM can't connect? Restart Cloud Shell then Re-run script."

# keep script running to show status (same spinner approach)
seq 1 43200 | while read -r i; do
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
