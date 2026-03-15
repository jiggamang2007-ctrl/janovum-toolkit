#!/bin/bash
# ════════════════════════════════════════════════════
# JANOVUM TOOLKIT — One-Click VPS Setup
# ════════════════════════════════════════════════════
# Paste this ENTIRE script into the "User Data" box
# when creating your VPS on DigitalOcean or Vultr.
# It installs everything and starts the toolkit.
#
# After the VPS boots (~2-3 min), open:
#   http://YOUR-VPS-IP:5050
# Then go to Settings and enter your domain.
# ════════════════════════════════════════════════════

set -e

REPO="https://github.com/jiggamang2007-ctrl/janovum-toolkit.git"
INSTALL_DIR="/root/janovum-toolkit"
DOMAIN=""  # Leave blank — set it from the dashboard later

echo "============================================"
echo "  JANOVUM TOOLKIT — VPS Setup Starting..."
echo "============================================"

# 1. System updates
echo "[1/8] Updating system..."
apt update && apt upgrade -y

# 2. Install system packages
echo "[2/8] Installing system packages..."
apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git curl ufw

# 3. Clone the toolkit
echo "[3/8] Cloning Janovum toolkit..."
if [ -d "$INSTALL_DIR" ]; then
    cd "$INSTALL_DIR" && git pull
else
    git clone "$REPO" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR/platform"

# 4. Install Python packages
echo "[4/8] Installing Python packages..."
pip3 install --break-system-packages flask requests loguru websockets
pip3 install --break-system-packages "pipecat-ai[cartesia,deepgram,silero]" fastapi uvicorn

# 5. Create data directories and default configs
echo "[5/8] Setting up directories and configs..."
mkdir -p data/clients/pids data/clients/logs data/audio data/conversations data/traces

# Create default toolkit config (user fills in via dashboard)
if [ ! -f data/toolkit_config.json ]; then
cat > data/toolkit_config.json << 'CONF'
{
  "domain": "",
  "twilio_account_sid": "",
  "twilio_auth_token": "",
  "auto_update_webhooks": true,
  "setup_complete": false
}
CONF
fi

# Create default platform config
if [ ! -f config.json ]; then
cat > config.json << 'CONF'
{
  "api_key": "",
  "model": "claude-sonnet-4-20250514",
  "max_monthly_spend_per_client": 300,
  "server_port": 5050,
  "modules_enabled": {}
}
CONF
fi

# Create empty clients index
if [ ! -f data/clients/clients_index.json ]; then
echo '{"clients":{}}' > data/clients/clients_index.json
fi

# 6. Set up systemd service (auto-start on boot)
echo "[6/8] Creating systemd service..."
cat > /etc/systemd/system/janovum-toolkit.service << 'EOF'
[Unit]
Description=Janovum Toolkit Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/janovum-toolkit/platform
ExecStart=/usr/bin/python3 server.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable janovum-toolkit
systemctl start janovum-toolkit

# 7. Set up nginx (reverse proxy)
echo "[7/8] Configuring nginx..."
cat > /etc/nginx/sites-available/janovum << 'NGINX'
server {
    listen 80;
    server_name _;

    # Toolkit dashboard
    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Client receptionists (ports 5051-5099)
    # Each client gets /client/{id}/ routed to their port
    # Or use subdomains — configure per client later

    # WebSocket support (needed for Twilio audio streaming)
    location /ws {
        proxy_pass http://127.0.0.1:5051;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Receptionist webhook
    location /incoming {
        proxy_pass http://127.0.0.1:5051;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/janovum /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 8. Configure firewall
echo "[8/8] Setting up firewall..."
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 5050/tcp  # Toolkit (direct access)
ufw --force enable

echo ""
echo "============================================"
echo "  JANOVUM TOOLKIT — SETUP COMPLETE!"
echo "============================================"
echo ""
echo "  Dashboard: http://$(curl -s ifconfig.me):5050"
echo ""
echo "  Next steps:"
echo "    1. Open the dashboard URL above"
echo "    2. Go to Settings tab"
echo "    3. Enter your domain name"
echo "    4. Run: sudo certbot --nginx -d yourdomain.com"
echo "    5. Go to Clients tab and add clients!"
echo ""
echo "  To check status:"
echo "    systemctl status janovum-toolkit"
echo ""
echo "  To view logs:"
echo "    journalctl -u janovum-toolkit -f"
echo ""
echo "============================================"
