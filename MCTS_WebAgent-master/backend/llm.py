#backend/llm.py

from langchain_ollama import OllamaLLM
from config import OLLAMA_MODEL

def get_llm():
    return OllamaLLM(
        model=OLLAMA_MODEL,
        temperature=0.7
    )



