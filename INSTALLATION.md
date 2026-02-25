# Viel AI — Installation Guide

> Having trouble getting started? This guide walks you through every method, step by step.

---

## Which method should I use?

| Method | Best for | Difficulty |
|--------|----------|------------|
| [Windows Installer](#method-1-windows-installer-easiest) | Windows users who want things done quickly | Beginner |
| [VPS (Hostinger / Linux server)](#method-2-vps-hostinger--any-linux-server) | Anyone who wants the bot online 24/7 | Intermediate |
| [Docker](#method-3-docker-all-platforms) | Anyone comfortable with Docker, or running a server 24/7 | Intermediate |
| [Manual (start.bat / start.sh)](#method-4-manual-installation) | Users who downloaded the source code | Intermediate |

---

## Method 1: Windows Installer (Easiest)

This is the recommended method for most Windows users.

### Step 1 — Download the installer

1. Go to the [Releases page](https://github.com/Iteranya/viel-ai/releases).
2. Under the latest release, download the file named **`installer.bat`**.

> **Note:** You do **not** need to download the full source code. Just `installer.bat` is enough.

### Step 2 — Run the installer

1. Locate the downloaded `installer.bat` file (usually in your `Downloads` folder).
2. **Double-click** it to run it.
3. Windows may show a security warning ("Windows protected your PC"). Click **"More info"** → **"Run anyway"**.
4. A terminal window will open and the installer will set everything up automatically. Wait for it to finish.

### Step 3 — Launch Viel AI

- When the installer finishes, it will have created a **"Viel AI" shortcut** on your Desktop.
- Double-click that shortcut to start the bot.
- Your browser will automatically open the control panel at **http://localhost:5666**.

**That's it for installation!** Continue to [First-Time Setup](#first-time-setup).

---

## Method 2: VPS (Hostinger / Any Linux Server)

This method lets Viel run **24/7**, even when your PC and phone are off. It's the recommended approach if you want the bot to always be available in Discord.

### Prerequisites

- A VPS running Ubuntu (20.04 or 22.04 recommended) — Hostinger's **KVM 1** plan is sufficient
- SSH access to your server (Hostinger provides this from their dashboard)

### Step 1 — Connect to your VPS

From your PC (Windows: use [PuTTY](https://www.putty.org/) or Windows Terminal), connect via SSH:

```bash
ssh root@your-vps-ip
```

Replace `your-vps-ip` with the IP address shown in your Hostinger panel.

### Step 2 — Install Docker

```bash
curl -fsSL https://get.docker.com | sh
```

This installs Docker in one command. When it finishes, verify it worked:

```bash
docker --version
```

### Step 3 — Download the docker-compose file

```bash
wget https://raw.githubusercontent.com/Iteranya/viel-ai/main/docker-compose.yml
```

### Step 4 — Start Viel AI

```bash
docker compose up -d
```

Viel AI is now running in the background. It will restart automatically if the server reboots.

### Step 5 — Open the firewall (Hostinger)

In your **Hostinger panel → VPS → Firewall**, allow inbound traffic on port **5666**.

### Step 6 — Access the control panel

From any device (PC, phone, etc.), open your browser and go to:

```
http://your-vps-ip:5666
```

You can now manage Viel from anywhere, at any time.

> **Security tip:** Port 5666 will be publicly accessible. Avoid using it for sensitive data, or set up a reverse proxy with HTTPS (nginx + Let's Encrypt) for production use.

**Continue to [First-Time Setup](#first-time-setup).**

---

## Method 3: Docker (All Platforms — Local Machine)

Docker works on Windows, macOS, and Linux. It is the most reliable method if you want to run Viel 24/7 on a server.

### Prerequisites

- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine (Linux).

### Step 1 — Get the docker-compose file

**Option A — Download it directly:**

```bash
wget https://raw.githubusercontent.com/Iteranya/viel-ai/main/docker-compose.yml
```

**Option B — Copy it manually:**

Create a file named `docker-compose.yml` and paste the contents from the [repository](https://github.com/Iteranya/viel-ai/blob/master/docker-compose.yml).

### Step 2 — Start Viel AI

In the folder containing `docker-compose.yml`, run:

```bash
docker-compose up -d
```

Docker will download the pre-built image and start Viel AI in the background.

### Step 3 — Open the control panel

Open your browser and go to **http://localhost:5666**.

**Continue to [First-Time Setup](#first-time-setup).**

---

## Method 4: Manual Installation

Use this method if you cloned or downloaded the source code from GitHub.

### Prerequisites

- **Python 3.10 or newer** — download from [python.org](https://www.python.org/downloads/).
  - During installation on Windows, check **"Add Python to PATH"**.

### On Windows

1. Open the folder where you cloned/extracted Viel AI.
2. Double-click **`start.bat`**.
   - The script will create a virtual environment, install all dependencies, and start the app.
3. Open your browser at **http://localhost:5666**.

### On Linux / macOS

1. Open a terminal in the Viel AI folder.
2. Make the script executable (first time only):
   ```bash
   chmod +x start.sh
   ```
3. Run it:
   ```bash
   ./start.sh
   ```
4. Open your browser at **http://localhost:5666**.

**Continue to [First-Time Setup](#first-time-setup).**

---

## First-Time Setup

Once the control panel is open at **http://localhost:5666**, follow these steps.

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **"New Application"** and give it a name (e.g. "Viel").
3. In the left sidebar, click **"Bot"**.
4. Scroll down to **"Privileged Gateway Intents"** and enable all three:
   - **Presence Intent**
   - **Server Members Intent**
   - **Message Content Intent**
5. Click **"Reset Token"**, then **copy** the token shown. Keep it private!

### 2. Configure the AI Provider

1. In the Viel control panel, go to **"AI Config"**.
2. Enter your AI provider details:
   - **OpenAI / Claude / etc.:** Enter your API key and select the model.
   - **Local model (Ollama / LM Studio):** Enter the local server URL (e.g. `http://localhost:11434`).

### 3. Enter Your Discord Bot Token

1. In the control panel, go to the main **Settings** page.
2. Paste your Discord bot token into the **"Bot Token"** field.
3. Click **Save**.

### 4. Start the Bot and Invite It

1. Click the **Big Red Button** in the control panel to turn the bot on.
2. An **invite link** will appear. Copy and open it in your browser.
3. Select your Discord server and confirm.

### 5. Register Viel in Your Server

1. In Discord, go to the channel where you want bot announcements (e.g. `#viel-hq`).
2. Type `/register` and press Enter.
3. In the control panel, go to **Channel Management**, find that channel, and enable the **"System"** toggle.

### 6. Add a Character to a Channel

1. In the control panel, go to **Channel Management**.
2. Find the channel where you want roleplay to happen.
3. Use the **Whitelist** to add a character (e.g. "Viel").

### 7. Test It

Go to the whitelisted channel in Discord and type something like:

```
Viel, tell me a story.
```

If the bot responds — **you're done!** Welcome to Viel AI.

---

## Troubleshooting

### The bot doesn't respond in Discord

- Make sure all three **Privileged Gateway Intents** are enabled in the Developer Portal.
- Make sure you clicked **Save** after entering the bot token.
- Make sure the bot is **turned on** (Big Red Button in the control panel).
- Make sure the channel has a character **whitelisted**.

### "Python is not installed" error (Windows)

1. Download Python from [python.org](https://www.python.org/downloads/).
2. During installation, tick **"Add Python to PATH"**.
3. Restart your computer and try again.

### The control panel doesn't open

- Make sure nothing else is using port **5666**.
- Try opening http://localhost:5666 manually in your browser.
- Check the terminal window for error messages.

### Docker: "port is already allocated"

Another service is using port 5666. Edit `docker-compose.yml` and change `"5666:5666"` to e.g. `"5667:5666"`, then access the panel at http://localhost:5667.

---

## Still stuck?

Open an issue on the [GitHub Issues page](https://github.com/Iteranya/viel-ai/issues) and describe your problem. Include:
- Your operating system
- Which installation method you used
- The error message you see (copy the full text from the terminal)
