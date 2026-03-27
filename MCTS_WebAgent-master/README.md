# Web AI Agent

A Chrome extension powered by an AI agent backend with MCTS (Monte Carlo Tree Search) for intelligent web scraping, supporting e-commerce price comparison, web data extraction, and general queries.

## Features

- 🤖 **MCTS-Driven Web Scraping**: Intelligent retry logic for robust data extraction
- 💰 **E-commerce Price Comparison**: Real-time prices from Amazon, Flipkart, Myntra
- 🌐 **Web Data Extraction**: Scrape any URL with structured content parsing
- 📧 **Email Operations**: Send and fetch emails (optional)
- 🔄 **Offline Operation**: Works with local Ollama LLM (llama3.2)

## Quick Start

### 1. Backend Setup

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Email (Optional)

Edit `backend/.env`:

```env
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

Get Gmail App Password: https://myaccount.google.com/apppasswords

### 3. Start Backend

**Method 1: Direct Python (Recommended for offline)**

```cmd
cd backend
python main.py
```

**Method 2: Uvicorn CLI**

```cmd
cd backend
uvicorn main:app --reload
```

**Difference:**

- `python main.py`: Simpler, works offline, auto-configures server
- `uvicorn main:app --reload`: More control, manual configuration

### 4. Install Extension

1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select `extension` folder

---

### Full Setup & Dependencies (Complete)

- **Python**: Recommended Python 3.10 or 3.11 (anything 3.9+ may work, but 3.10+ tested).
- **Virtual environment**: Use `python -m venv venv` and activate the virtualenv before installing.
- **Backend dependencies**: See [backend/requirements.txt](backend/requirements.txt#L1-L20). Main packages:
  - `fastapi`, `uvicorn` — web server and ASGI runner
  - `langchain`, `langchain-ollama` — LLM integration (local Ollama)
  - `python-dotenv` — `.env` support
  - `requests`, `beautifulsoup4`, `lxml` — scraping and HTML parsing
  - `pydantic`, `numpy` — data models and helpers

### .env file (required / optional keys)

Create a file named `.env` in the `backend` folder (path: [backend/.env](backend/.env)). Example template:

```
# Local Ollama (optional if you use defaults in config.py)
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

# Email (optional — required if you want email send/fetch features)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
IMAP_HOST=imap.gmail.com
```

Notes:

- `SMTP_USER` and `SMTP_PASSWORD` are required for the email tools (`tools/mail.py`). For Gmail, use an App Password (see Google account security settings).
- If you do not configure email vars, email endpoints return an error message indicating missing credentials.
- `OLLAMA_BASE_URL` and `OLLAMA_MODEL` are set by default in `backend/config.py` (see [backend/config.py](backend/config.py#L1-L60)). Change them in that file or provide matching environment variables if you adapt the code to read envs.

### Local LLM (Ollama) — offline usage

- This project is designed to run with a local Ollama server (recommended for offline use). By default the code expects Ollama at `http://localhost:11434` and model `llama3.2` (see [backend/config.py](backend/config.py#L1-L10)).
- Run Ollama separately and ensure the HTTP API is reachable at the configured `OLLAMA_BASE_URL`.

### Running the Backend

Two recommended ways to run the backend (from `backend` folder):

1. Simple Python runner (auto-configures some defaults):

```bash
cd backend
python main.py
```

2. Uvicorn (for development with autoreload):

```bash
cd backend
uvicorn main:app --reload
```

After startup the backend listens on `http://127.0.0.1:8000` by default and OpenAPI docs are at `http://127.0.0.1:8000/docs`.

### Endpoints to test

- `GET /` — root health check
- `GET /health` — status
- `POST /ask` — query the agent (see `backend/models.py` for request schema) — uses MCTS + LLM for general queries
- `POST /send-email` — send email (requires SMTP vars in `.env`)
- `POST /fetch-emails` — fetch unread emails (requires SMTP/IMAP creds)
- `POST /mcts/run` — run specific MCTS variant (basic-mcts, r-mcts, wm-mcts, rag-mcts)

### Chrome extension

- Load the `extension` folder in Chrome via `chrome://extensions` → Developer mode → Load unpacked.
- The extension communicates with the backend endpoints above. Ensure the backend is running and CORS is allowed (`main.py` config allows `*`).

### Troubleshooting & Tips

- If LLM calls fail: verify Ollama server is running and reachable at `OLLAMA_BASE_URL` or edit `backend/config.py` to point to your server.
- If email send/fetch fails: confirm `SMTP_USER` and `SMTP_PASSWORD` are correct and the SMTP provider allows SMTP connections (Gmail requires App Passwords and less-restrictive account settings).
- If scraping fails frequently: increase timeouts in [backend/config.py](backend/config.py#L40-L120) (variables like `REQUEST_TIMEOUT`, `TIER1_TIMEOUT`, `SCRAPE_RETRIES`).
- Use a fresh virtualenv per-project to avoid dependency conflicts.

### Development notes (where things live)

- Backend entrypoint: [backend/main.py](backend/main.py#L1-L200)
- Config defaults: [backend/config.py](backend/config.py#L1-L200)
- LLM wrapper: [backend/llm.py](backend/llm.py#L1-L50)
- Email tool: [backend/tools/mail.py](backend/tools/mail.py#L1-L300)
- Scrapers & MCTS: [backend/mcts/](backend/mcts)
- Chrome extension: [extension/](extension)

---

If you want, I can also:

- generate a ready-to-copy `backend/.env.example` file,
- add a small `Makefile` or `scripts` to automate venv creation and start commands,
- or run a quick validation script to confirm required env vars are present on your machine.
