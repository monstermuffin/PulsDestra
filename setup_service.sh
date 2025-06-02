#!/bin/bash
set -e

echo "🔧 Setting up PulsDestra as a system service..."

CURRENT_USER=$(whoami)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "📍 Current directory: $SCRIPT_DIR"
echo "👤 Current user: $CURRENT_USER"

if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root."
   exit 1
fi

if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "❌ Virtual environment not found. Please run the setup first:"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/config.yaml" ]; then
    echo "❌ config.yaml not found. Please create it from config_example.yaml first."
    exit 1
fi

echo "🔐 Adding user to gpio and i2c groups..."
sudo usermod -a -G gpio,i2c $CURRENT_USER

SERVICE_FILE="/tmp/pulsedestra.service"
cat > $SERVICE_FILE << EOF
[Unit]
Description=PulsDestra
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$SCRIPT_DIR/.venv/bin
ExecStart=$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "📋 Installing systemd service..."
sudo cp $SERVICE_FILE /etc/systemd/system/pulsedestra.service
sudo chmod 644 /etc/systemd/system/pulsedestra.service

echo "🔄 Enabling PulsDestra service..."
sudo systemctl daemon-reload
sudo systemctl enable pulsedestra.service

echo "✅ PulsDestra service has been installed and enabled!"
echo ""
echo "📋 Service Management Commands:"
echo "   Start service:    sudo systemctl start pulsedestra"
echo "   Stop service:     sudo systemctl stop pulsedestra"
echo "   Service status:   sudo systemctl status pulsedestra"
echo "   View logs:        sudo journalctl -u pulsedestra -f"
echo "   Disable service:  sudo systemctl disable pulsedestra"
echo ""
echo "⚠️  IMPORTANT: You need to log out and back in (or reboot) for group changes to take effect!"
echo "   After logging back in, start the service with: sudo systemctl start pulsedestra"
echo ""