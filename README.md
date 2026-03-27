AI Agents Hub (News_AI_Agent_Review2)

A unified workspace that bundles four AI agents—each built around Monte Carlo Tree Search (MCTS) reasoning—plus a single HTML dashboard that launches them from one place.

This project demonstrates how different AI agents can be combined into a single multi-agent environment for research, experimentation, and learning.

🚀 Features
Multi-Agent Architecture
MCTS-based reasoning across agents
Local LLM support via Ollama
Unified HTML dashboard
Multimodal processing (text, image, video)
RAG-based PDF Q&A
Browser automation with Chrome extension
🧠 Agents Included
1. News AI Agent

MCTS-based news topic summarization using the MIND dataset.

Features:

Topic summarization
Dataset fallback when MIND is missing
LLM-powered reasoning
2. Multimodal Summarizer Agent

Summarizes text, images, and videos using multiple specialized agents with MCTS selection.

Features:

Text summarization
Image analysis
Video summarization
Multi-agent reasoning
3. Homework Helper Agent

A PDF-grounded Q&A system using:

RAG (Retrieval Augmented Generation)
FAISS vector search
MCTS reasoning
Ollama LLM

Users can upload PDFs and ask questions about the document.

4. MCTS Web Agent

A Chrome Extension + FastAPI backend for:

Web scraping
Product comparison
General web queries
📁 Repository Structure
News_AI_Agent_Review2/

├── main_dashboard.html
├── dashboard.html

├── News_AI_Agent/
│
├── Summarizer-Agent-main/
│
├── Homework-Helper-MCTS-main/
│
└── MCTS_WebAgent-master/
⚙️ Prerequisites

Install the following before running the agents:

Python 3.10+ (3.11 recommended)
Ollama installed and running

Default Ollama endpoint:

http://localhost:11434
Required Ollama Models

Install:

llama3.2:1b
llava:7b

Example:

ollama pull llama3.2:1b
ollama pull llava:7b
▶️ Running the Agents

Each agent runs independently on its own port.

1️⃣ News AI Agent

Location

News_AI_Agent/

Port

5001

Run:

cd News_AI_Agent

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python app.py

Notes

Uses MIND dataset if available:
News_AI_Agent/data/MIND/MINDsmall_train/news.tsv
Falls back to sample news if dataset is missing.
2️⃣ Multimodal Summarizer Agent

Location

Summarizer-Agent-main/

Port

5007

Run:

cd Summarizer-Agent-main

python -m venv venv
venv\Scripts\activate

pip install flask requests opencv-python Pillow werkzeug nltk pandas

python app.py

Features

Upload text
Upload images
Upload videos
Uses:
llava:7b for visual analysis
llama3.2:1b for summarization
3️⃣ Homework Helper Agent

Location

Homework-Helper-MCTS-main/

Port

5000

Run:

cd Homework-Helper-MCTS-main

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python app.py

Features

Upload PDFs
Ask questions about the document
Uses FAISS vector search
Temporary vector data stored in local temp directory
4️⃣ MCTS Web Agent

Backend location

MCTS_WebAgent-master/backend

Port

8000

Run backend:

cd MCTS_WebAgent-master/backend

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python main.py
🌐 Chrome Extension Setup
Open Chrome
Go to
chrome://extensions/
Enable Developer Mode
Click Load unpacked
Select
MCTS_WebAgent-master/extension
📧 Optional Email Configuration

Edit:

MCTS_WebAgent-master/backend/.env

Add SMTP/IMAP credentials if you want to enable email automation tools.

🖥️ Unified Dashboard

Open the dashboard:

main_dashboard.html

This provides a single interface to launch and view all agents.

Configured endpoints:

Agent	URL
News AI Agent	http://localhost:5001

Multimodal Summarizer	http://localhost:5007

Homework Helper	http://localhost:5000

Web Agent Backend	http://localhost:8000

If you change ports, update them in:

main_dashboard.html
🛠️ Troubleshooting
Ollama Not Running

Agents will fallback to placeholder responses if Ollama is unavailable.

Start Ollama:

ollama serve
Dashboard Shows “Offline”

Check that the agent is running on the expected port.

Example:

http://localhost:5001
Chrome Extension Not Working

Ensure backend is running:

http://localhost:8000
