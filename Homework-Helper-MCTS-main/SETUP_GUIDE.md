# Homework Helper Agent with MCTS

A Flask-based homework helper that uses LangChain, FAISS, and Google's Generative AI to help students with their homework questions.

## Features

- 📄 **PDF Upload**: Upload your homework notes and documents
- 🤖 **AI-Powered**: Uses Google's Gemini API for intelligent responses
- 🔍 **Semantic Search**: FAISS vector database for finding relevant content
- 🌳 **MCTS**: Monte Carlo Tree Search for exploring multiple solution paths
- 💬 **Multi-mode**: Works with PDF context or general knowledge

## Setup

**1. Prerequisites**

Make sure you have the following installed:

Python (>= 3.9)

pip (Python package manager)

Git

Ollama (for running LLM locally)

**2. Install Ollama**

Download and install Ollama from:
👉 https://ollama.com/download

After installation, pull the required models:

ollama pull llama3.2:1b
ollama pull nomic-embed-text

**3. Create Virtual Environment**
python -m venv venv

Activate it:

Windows:

venv\Scripts\activate

Mac/Linux:

source venv/bin/activate

**4. Install Dependencies**
pip install -r requirements.txt

If requirements.txt is not available, install manually:

pip install flask langchain langchain-core langchain-community langchain-ollama faiss-cpu pypdf

**5. Run the Application**
python app.py

**6. Open in Browser**

Go to:

http://127.0.0.1:5000/

**7. How to Use**

Upload a PDF document

Enter your question

Get answers using:

Basic RAG

MCTS-based reasoning

Different MCTS variations

**8. MCTS Exploration**

Navigate to:

http://127.0.0.1:5000/mcts

Enter question

Select variation:

Standard MCTS

R-MCTS

MCTS-RAG

World Guided MCTS

View step-by-step reasoning

**9. Project Structure**
├── app.py              # Main Flask application
├── templates/
│   ├── index.html     # Main UI
│   └── mcts.html      # MCTS visualization UI
├── static/            # CSS/JS files
├── requirements.txt   # Dependencies

**10. Notes**

Ensure Ollama is running in the background

First run may take time due to model loading

FAISS database is created dynamically after PDF upload
