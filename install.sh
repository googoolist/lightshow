#!/bin/bash
# Installation script for Raspberry Pi DMX Light Show

set -e

echo "╔════════════════════════════════════════╗"
echo "║     Raspberry Pi DMX Light Show        ║"
echo "║           Installation Script          ║"
echo "╚════════════════════════════════════════╝"
echo

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "   The installation will continue, but hardware features may not work"
    echo
fi

# Update system packages
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    portaudio19-dev \
    libasound2-dev \
    alsa-utils \
    pulseaudio \
    pulseaudio-utils

# Install USB audio support
echo "🎵 Installing USB audio support..."
sudo apt install -y \
    usb-modeswitch \
    usb-modeswitch-data

# Install DMX USB interface support
echo "💡 Installing DMX USB interface support..."
sudo apt install -y \
    libftdi1-dev \
    libusb-1.0-0-dev

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Setup udev rules for USB devices
echo "⚙️  Setting up USB device permissions..."
sudo tee /etc/udev/rules.d/99-dmx-usb.rules > /dev/null << 'EOF'
# DMX USB Pro
SUBSYSTEM=="usb", ATTR{idVendor}=="0403", ATTR{idProduct}=="6001", MODE="0666", GROUP="dialout"
# Generic FTDI devices
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666", GROUP="dialout"
# USB Audio devices
SUBSYSTEM=="sound", GROUP="audio", MODE="0664"
SUBSYSTEM=="usb", ATTR{bInterfaceClass}=="01", ATTR{bInterfaceSubClass}=="01", GROUP="audio"
EOF

# Add user to audio and dialout groups
echo "👤 Adding user to required groups..."
sudo usermod -a -G audio,dialout $USER

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Create systemd service file
echo "🔄 Creating systemd service..."
sudo tee /etc/systemd/system/dmx-lightshow.service > /dev/null << EOF
[Unit]
Description=Raspberry Pi DMX Light Show
After=sound.target graphical-session.target
Wants=sound.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$(pwd)
Environment="PATH=$(pwd)/venv/bin"
Environment="HOME=/home/$USER"
Environment="XDG_RUNTIME_DIR=/run/user/\$(id -u $USER)"
ExecStartPre=/bin/sleep 10
ExecStart=$(pwd)/venv/bin/python start_lightshow.py
Restart=always
RestartSec=10
TimeoutStartSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF

# Enable service (but don't start it yet)
sudo systemctl daemon-reload
sudo systemctl enable dmx-lightshow.service

# Create desktop shortcut
if [ -d "$HOME/Desktop" ]; then
    echo "🖥️  Creating desktop shortcut..."
    cat > "$HOME/Desktop/DMX Light Show.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=DMX Light Show
Comment=Audio-reactive lighting controller
Exec=$(pwd)/venv/bin/python $(pwd)/main.py
Icon=applications-multimedia
Terminal=true
Categories=AudioVideo;Audio;
EOF
    chmod +x "$HOME/Desktop/DMX Light Show.desktop"
fi

echo
echo "✅ Installation completed successfully!"
echo
echo "📋 Next Steps:"
echo "   1. Reboot your Raspberry Pi (required for group membership)"
echo "   2. Connect your Sound Blaster USB dongle"
echo "   3. Connect your DMX USB interface"
echo "   4. Edit config.yaml to match your setup"
echo "   5. Test with: ./venv/bin/python main.py"
echo
echo "🔧 Service Management:"
echo "   Start service:        sudo systemctl start dmx-lightshow"
echo "   Stop service:         sudo systemctl stop dmx-lightshow"
echo "   Disable auto-start:   sudo systemctl disable dmx-lightshow"
echo "   Enable auto-start:    sudo systemctl enable dmx-lightshow"
echo "   View logs:            sudo journalctl -u dmx-lightshow -f"
echo "   View startup logs:    tail -f /tmp/lightshow_startup.log"
echo
echo "⚠️  Please reboot before first use!"
echo

# Check for connected USB devices
echo "🔌 Connected USB Audio Devices:"
lsusb | grep -i audio || echo "   No USB audio devices found"
echo
echo "🔌 Connected USB Serial Devices:"
lsusb | grep -i "serial\|ftdi\|prolific" || echo "   No USB serial devices found"
echo

echo "Installation complete. Please reboot and enjoy your light show! 🎉"

