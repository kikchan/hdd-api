# 💾 Speedforce Disk API

A lightweight Flask API that exposes all mounted disks to Dashy with a clean, responsive web view.

It automatically:

- Lists every mounted drive
- Shows mount point
- Shows free / total space
- Displays a color usage bar (green → yellow → orange → red)
- Uses full widget width
- Auto height (no Dashy sizing hacks)
- Ignores /boot and /boot/efi
- Requires no Glances or heavy monitoring stacks

Perfect for simple dashboards and homelab setups.

---

## 📋 Prerequisites

Ensure your Linux environment has:

* **Python 3 & Pip**
* No extra system tools required (uses Python + psutil only)

Install base packages:

```bash
sudo apt update
sudo apt install python3-venv python3-pip -y
```

---

## 🚀 Quick Start

### 1. Create the environment
```bash
python3 -m venv venv
```

### 2. Activate the environment
```bash
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install flask flask-cors psutil
```

### 4. Run the app
```bash
python3 disks_api.py
```

### 5. Access it from
```bash
http://192.168.1.20:2014
```

---

## 📊 What You’ll See

Each drive shows:

• Mount point  
• Free space of total space  
• Colored usage bar  

### Color scale

| Usage | Color |
|------|-------|
| Low usage | Green |
| Medium-low | Green → Yellow |
| ~50% | Yellow |
| High | Orange |
| Nearly full | Red |

---

## ⚙️ Deployment (Systemd)

To ensure the API runs 24/7 and starts on boot:

### 1. Create service file
```bash
sudo nano /etc/systemd/system/disks_api.service
```

### 2. Add

```bash
[Unit]
Description=Speedforce Disk Usage API for Dashy
After=network.target

[Service]
User=kikchan
WorkingDirectory=/home/kikchan/Metalforce/hdd-api
ExecStart=/home/kikchan/Metalforce/hdd-api/venv/bin/python disks_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3. Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable disks_api.service
sudo systemctl start disks_api.service
```

### 4. Check status

```bash
systemctl status disks_api.service
```

---

## 📊 Dashy Config

Add this section to your `conf.yml`:

```yaml
	widgets:
      - type: embed
        options:
          html: >
            <p align="center">
                <iframe src="http://192.168.1.20:2014" 
                 frameborder='0' 
                 scrolling="no" 
                 style="overflow: hidden; height: 360px; width: 100%"
                />
            </p>
        id: 1_510_embed
```

Tip:
If height feels off, you can safely increase it — the page auto-scales.

---

## ✅ Why This API?

Compared to Glances:

✔ faster  
✔ simpler  
✔ zero heavy dependencies  
✔ cleaner layout for Dashy  
✔ purpose-built for disks only  

Perfect for homelabs and lightweight servers.

---

Enjoy your shiny dashboard 🚀
