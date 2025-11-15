#!/usr/bin/env bash
set -euo pipefail

# Simple Google Cloud Shell + Docker + xrdp + ngrok setup
# - Exposes RDP (3389) via ngrok tcp
# - Builds a small Ubuntu image with XFCE + xrdp
# Notes:
#  - If you want a fixed user/password set env vars before running:
#      export RDP_USER="youruser"
#      export RDP_PASS="YourP@ssw0rd!"
#    Otherwise defaults: user="user", pass="123456"
#  - Requires Docker & curl available in Cloud Shell and ability to run privileged containers.
#  - Security: this opens RDP to the internet via ngrok. Use strong password and stop when done.

RDP_USER="${RDP_USER:-user}"
RDP_PASS="${RDP_PASS:-123456}"
IMAGE_NAME="ubuntu-xrdp-gnc"
CONTAINER_NAME="rdp-ubuntu"
NGROK_BIN="./ngrok"
TMPDIR="$(mktemp -d)"
CWD="$(pwd)"

cleanup() {
  echo
  echo "Cleaning up local temporaries..."
  rm -rf "$TMPDIR"
}
trap cleanup EXIT

cd "$TMPDIR"

cat > Dockerfile <<'DOCKERFILE'
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# install minimal desktop & xrdp
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      xfce4 xfce4-terminal xfce4-panel \
      xrdp dbus-x11 sudo wget ca-certificates \
      locales procps x11-xserver-utils pulseaudio psmisc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# create user (values will be overridden during build args, but keep fallback)
ARG RDP_USER=user
ARG RDP_PASS=123456
RUN useradd -m -s /bin/bash "$RDP_USER" && \
    echo "${RDP_USER}:${RDP_PASS}" | chpasswd && \
    usermod -aG sudo "$RDP_USER" || true

# ensure xfce session for xrdp
RUN echo "startxfce4" > /home/$RDP_USER/.xsession && chown $RDP_USER:$RDP_USER /home/$RDP_USER/.xsession

# allow anyone to start X sessions (avoid console-only restriction)
RUN sed -i 's/^allowed_users=.*/allowed_users=anybody/' /etc/X11/Xwrapper.config || true

# expose xrdp default port
EXPOSE 3389

# start dbus and xrdp processes; run xrdp in foreground so container stays alive
CMD dbus-daemon --system --fork || true && \
    /usr/sbin/xrdp-sesman & \
    /usr/sbin/xrdp -nodaemon
DOCKERFILE

echo "Building Docker image ($IMAGE_NAME). This may take several minutes..."
docker build --no-cache --build-arg RDP_USER="$RDP_USER" --build-arg RDP_PASS="$RDP_PASS" -t "$IMAGE_NAME" .

echo "Stopping & removing any existing container named $CONTAINER_NAME ..."
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

echo "Starting container $CONTAINER_NAME (host network)..."
# run with host networking so xrdp is reachable on host port 3389
docker run --rm -d --network host --privileged --name "$CONTAINER_NAME" --shm-size=1g "$IMAGE_NAME"

# --- ngrok setup
echo
echo "=== ngrok setup ==="
echo "If you don't have ngrok binary in the folder, the script will fetch it for linux-amd64."
if [ ! -x "$NGROK_BIN" ]; then
  echo "Downloading ngrok (linux-amd64)..."
  NGROK_URL="https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip"
  curl -sSL "$NGROK_URL" -o ngrok.zip
  unzip -q ngrok.zip
  rm -f ngrok.zip
  chmod +x ngrok
fi

# prompt for authtoken
read -r -p "Go to https://dashboard.ngrok.com/get-started/your-authtoken then paste your ngrok authtoken: " NGROK_AUTHTOKEN
"$NGROK_BIN" config add-authtoken "$NGROK_AUTHTOKEN" >/dev/null 2>&1 || true

echo
echo "Choose ngrok region for better latency (press Enter for 'us'):"
echo "  us - United States (Ohio)"
echo "  eu - Europe (Frankfurt)"
echo "  ap - Asia/Pacific (Singapore)"
echo "  au - Australia (Sydney)"
echo "  sa - South America (Sao Paulo)"
echo "  jp - Japan (Tokyo)"
echo "  in - India (Mumbai)"
read -r -p "Region (us/eu/ap/au/sa/jp/in): " NGROK_REGION
NGROK_REGION="${NGROK_REGION:-us}"

echo "Starting ngrok tcp tunnel for port 3389 (region: $NGROK_REGION)..."
# start ngrok in background
"$NGROK_BIN" tcp --region "$NGROK_REGION" 3389 &>/dev/null &
sleep 1

# wait for ngrok api and retrieve public URL
NGROK_API="http://127.0.0.1:4040/api/tunnels"
TRIES=0
NG_PUBLIC=""
while [ $TRIES -lt 15 ]; do
  sleep 1
  NG_PUBLIC=$(curl --silent --show-error "$NGROK_API" 2>/dev/null | sed -nE 's/.*"public_url":"tcp:\/\/([^"]*)".*/\1/p' || true)
  if [ -n "$NG_PUBLIC" ]; then break; fi
  TRIES=$((TRIES+1))
done

if [ -z "$NG_PUBLIC" ]; then
  echo "Ngrok didn't return a public tunnel. Check ngrok logs or your token. Exiting."
  docker logs "$CONTAINER_NAME" 2>/dev/null || true
  exit 1
fi

echo
echo "=== RDP Access Information ==="
echo "Connect using Microsoft Remote Desktop (or any RDP client) to:"
echo
echo "  ${NG_PUBLIC}"
echo
echo "Username: ${RDP_USER}"
echo "Password: ${RDP_PASS}"
echo
echo "Notes:"
echo " - When connecting, use the IP:PORT exactly as returned above (ngrok shows host:port)."
echo " - If RDP client complains about certificates, accept the warning (this is normal for this temporary setup)."
echo
echo "If you want a different user/password, stop this script and re-run with:"
echo "  export RDP_USER=\"myuser\"; export RDP_PASS=\"Secur3P@ss!\"; curl -sLkO <raw-url>; bash <script>"
echo

# simple keep-alive / status loop
echo "Press Ctrl+C to stop the script. Container will exit automatically when the script stops."
while true; do
  printf "\r[%s] RDP exposed at %s (container: %s) " "$(date '+%Y-%m-%d %H:%M:%S')" "$NG_PUBLIC" "$CONTAINER_NAME"
  sleep 5
done
