# 🔍 SkillSync AI — Full Stack Application

A complete AI-powered resume analysis and skill gap tracker with:
- **Frontend**: HTML + CSS + JavaScript
- **Backend**: Python Flask REST API
- **Database**: SQLite (no setup required)

---

## 📁 Project Structure

```
skillsync/
├── backend/
│   ├── app.py              ← Flask backend (all API routes)
│   ├── requirements.txt    ← Python dependencies
│   └── skillsync.db        ← SQLite database (auto-created on first run)
├── frontend/
│   ├── templates/
│   │   └── index.html      ← Main HTML page
│   └── static/
│       ├── css/
│       │   └── style.css   ← All styles + dark/light mode
│       ├── js/
│       │   └── app.js      ← All frontend logic
│       └── uploads/        ← Uploaded resumes stored here
├── run.bat                 ← One-click run for Windows
├── run.sh                  ← One-click run for Mac/Linux
└── README.md               ← This file
```

---

## 🚀 How to Run

### Prerequisites
- Python 3.8 or higher → https://python.org/downloads
- pip (comes with Python)

---

### ▶️ Windows — Double click `run.bat`
OR open terminal in the `skillsync` folder and run:
```bash
cd backend
pip install -r requirements.txt
python app.py
```

---

### ▶️ Mac / Linux — Run `run.sh`
```bash
chmod +x run.sh
./run.sh
```
OR manually:
```bash
cd backend
pip3 install -r requirements.txt
python3 app.py
```

---

### 🌐 Open in Browser
Once running, open: **http://localhost:5000**

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 Register / Login | JWT-based authentication stored in SQLite |
| 📄 Resume Upload | Supports PDF and TXT files |
| 🧠 Skill Extraction | NLP-based keyword extraction from resume |
| 📊 Skill Gap Analysis | Matches skills against role requirements |
| 💡 Role Suggestion | Suggests a better-fit role after analysis |
| 🎯 Skill Tracker | Per-skill deadlines auto-distributed until interview |
| 📝 Quiz System | 3-question quiz — all 3 must be correct to pass |
| 🔄 Smart Rotation | Each retry gets different questions from a 12-question bank |
| ▶️ Video Resources | YouTube tutorial links per skill |
| 🌙☀️ Dark/Light Mode | Theme saved in DB per user |
| ⬇️ Download Resume | Updated resume with learned skills appended |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python 3, Flask, Flask-CORS |
| Database | SQLite (via Python sqlite3) |
| PDF Parsing | pdfplumber |
| Auth | JWT (PyJWT) |
| Password | SHA-256 hashing |

---

## 🗄️ Database Tables

| Table | Purpose |
|---|---|
| `users` | Stores registered users, theme preference |
| `applications` | Resume analysis results per user |
| `skill_items` | Individual skills with deadlines and completion status |
| `quiz_history` | Tracks which questions each user has seen per skill |

---

## 🔧 VS Code Tips

1. Install **Python** extension
2. Install **Live Server** extension (optional)
3. Open the `skillsync` folder: `File → Open Folder`
4. Open terminal: `` Ctrl+` ``
5. Run the backend commands above
6. Visit http://localhost:5000

---

## ⚠️ Notes

- The SQLite database (`skillsync.db`) is created automatically on first run
- Uploaded resumes are saved in `frontend/static/uploads/`
- Internet needed only for Google Fonts and YouTube video links
- All user data is stored locally on your machine
