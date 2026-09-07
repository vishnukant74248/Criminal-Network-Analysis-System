# Criminal Network Analysis System (SENTINEL & SIH 2025)

An AI-driven Defense Surveillance, Edge Video Analytics, and Criminal Network Analysis platform designed for intelligent tracking, real-time threat detection, and comprehensive evidence forensics.

## 🚀 Key Modules & Architecture

### 1. Sentinel Edge Analytics & C2 Platform (`sentinel/`)
- **Live Person & Object Detection**: YOLOv8-powered real-time detection and ByteTrack multi-target tracking.
- **Visual Analytics**: Interactive bounding box rendering (live detection and uploaded photo matching).
- **FastAPI Edge Engine**: RESTful endpoints and real-time WebSocket telemetry for surveillance feeds.
- **Command & Control Dashboard**: Responsive React-based monitoring interface with live feeds and spatial tracking.
- **Audit & Forensics**: Cryptographic hashing and evidence logging.

### 2. SIH 2025 Submission Materials
- **Presentation Deck**: `SIH2025_Criminal_Network_Analysis_System.pptx`
- **Specification Document**: `SIH2025_Criminal_Network_Analysis_System.pdf`
- **Format Reference**: `SIH2025-IDEA-Presentation-Format.pptx`

### 3. Network Monitor (`network_monitor-Ritu/`)
- Distributed device and CCTV camera ping engine, connectivity telemetry, and network status dashboards.

### 4. Intelligent Border Video Analytics Platform (`IBVAP-main/`)
- Core blockchain evidence tracking, vector geofencing, and multi-camera orchestration.

---

## 🛠️ Quick Start & Setup Guide (For Friends & Teammates)

### 1. Prerequisites
Ensure you have the following installed on your machine:
- **Git**: [https://git-scm.com/](https://git-scm.com/)
- **Python 3.10+**: [https://www.python.org/](https://www.python.org/)
- **Node.js 18+**: [https://nodejs.org/](https://nodejs.org/)

---

### 2. Clone the Repository
Open your terminal (PowerShell, Command Prompt, or Bash) and run:
```bash
git clone https://github.com/vishnukant74248/Criminal-Network-Analysis-System.git
cd Criminal-Network-Analysis-System
```

---

### 3. Run the Project

#### Option A: One-Click Instant Start (Windows)
Simply run the root start script:
```bash
.\start.bat
```
*(Or press `Ctrl + Shift + B` in VS Code and select `Start SENTINEL (Backend + Frontend)`).*

#### Option B: Manual Setup (Terminal by Terminal)

**Step 1 — Backend (FastAPI + AI Engine):**
```bash
cd sentinel/backend
python -m venv .venv

# Activate virtual environment:
# On Windows:
.\.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install dependencies:
pip install -r requirements.txt

# Start backend server:
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```
- API is live at: `http://127.0.0.1:8000`
- Interactive Swagger docs: `http://127.0.0.1:8000/docs`

**Step 2 — Frontend (Vite + React UI):**
Open a new terminal window:
```bash
cd sentinel/frontend
npm install
npm run dev
```
- Web Application Console: `http://localhost:5173/`

---

## 👥 How to Work Together (Team Git Workflow)

### 1. Add Collaborators on GitHub:
1. Go to repository on GitHub: `https://github.com/vishnukant74248/Criminal-Network-Analysis-System`
2. Click **Settings** ➔ **Collaborators** (under Access).
3. Click **Add people** and enter your friend's GitHub username or email.
4. Your friend will receive an invitation email or notification to accept.

### 2. Daily Development Workflow:
Always pull the latest changes before starting work:
```bash
git pull origin main
```

Create a new branch for your feature:
```bash
git checkout -b feature/my-new-feature
```

Make your code changes, stage, and commit:
```bash
git add .
git commit -m "feat: describe what you added or fixed"
```

Push your branch to GitHub:
```bash
git push origin feature/my-new-feature
```
Then open a Pull Request (PR) on GitHub to review and merge into `main`!

