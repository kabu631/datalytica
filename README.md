# Datalytica

> **AI-powered desktop analytics platform** — ingest, clean, transform, explore and narrate your data, all offline.

![Version](https://img.shields.io/badge/version-1.0.0-6c63ff)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![Electron](https://img.shields.io/badge/electron-31-47848f)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

| Module | Description |
|---|---|
| **Ingest** | Upload CSV, Excel, JSON, Parquet — instant schema detection |
| **Cleanse** | Rule-based null handling, deduplication, normalisation |
| **ETL** | Chain transforms: rename, filter, pivot, melt, cast, derive columns |
| **EDA** | Summary stats, correlation matrix, distributions, outlier detection |
| **Charts** | Interactive Plotly charts (bar, line, scatter, pie, heatmap, bubble…) |
| **AI Narrative** | One-click reports via DeepSeek API or local Ollama |
| **License** | Built-in license key validation system |

---

## 🏗 Project Structure

```
datalytica/
├── backend/              # FastAPI + SQLAlchemy + pandas
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── routers/          # One router per feature
│   └── services/         # Business logic, decoupled from HTTP
├── frontend/             # Electron shell
│   ├── main.js           # Main process — spawns backend, creates window
│   ├── preload.js        # Context bridge (IPC + fetch API)
│   └── renderer/
│       ├── index.html    # App shell with sidebar navigation
│       ├── styles/       # Design system CSS
│       └── pages/        # One HTML page per feature
└── installer/
    ├── build.py          # Full build orchestrator
    └── datalytica.spec   # PyInstaller spec for backend binary
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional) [Ollama](https://ollama.com) for local AI

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend (Development)

```bash
cd frontend
npm install
npm start          # Launches Electron in dev mode
```

### 3. Production Build

```bash
python installer/build.py
# Output is placed in dist/
```

---

## 🔑 Environment Variables

Create a `.env` file in `backend/`:

```env
DEEPSEEK_API_KEY=sk-your-key-here
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
DATABASE_URL=sqlite:///./datalytica.db
```

---

## 🧩 API Reference

The FastAPI backend auto-generates interactive docs at:

- **Swagger UI** → [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**       → [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/ingest/upload` | Upload a data file |
| GET  | `/api/ingest/datasets` | List all datasets |
| POST | `/api/cleanse/apply` | Apply cleansing rules |
| POST | `/api/etl/transform` | Run ETL pipeline |
| GET  | `/api/eda/summary/{id}` | Descriptive statistics |
| GET  | `/api/eda/correlation/{id}` | Correlation matrix |
| POST | `/api/charts/build` | Generate Plotly chart |
| POST | `/api/narrative/generate` | AI report generation |
| POST | `/api/license/activate` | Activate license key |

---

## 🎨 Tech Stack

**Backend**
- [FastAPI](https://fastapi.tiangolo.com) — HTTP API framework
- [SQLAlchemy](https://sqlalchemy.org) — ORM + SQLite
- [pandas](https://pandas.pydata.org) — Data processing
- [Plotly](https://plotly.com/python) — Chart generation

**Frontend**
- [Electron](https://electronjs.org) — Desktop shell
- Vanilla HTML/CSS/JS — Renderer UI
- [Plotly.js](https://plotly.com/javascript) — Interactive charts

**AI**
- [DeepSeek](https://platform.deepseek.com) — Cloud LLM
- [Ollama](https://ollama.com) — Local LLM inference

---

## 📄 License

MIT © Datalytica
