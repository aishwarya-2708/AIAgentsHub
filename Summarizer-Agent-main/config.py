# Configuration file for multimodal summarization system

# Ollama Configuration
OLLAMA_URL = "http://localhost:11435/api/generate"
MODEL_NAME = "llama3.2:latest"
TEXT_MODEL = MODEL_NAME          # alias for consistency
VISION_MODEL = "llava:7b"

# Multimodal Configuration
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv'}
UPLOAD_FOLDER = 'uploads'
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max

# MCTS Configuration
MCTS_EXPLORATION_WEIGHT = 1.414  # sqrt(2)
MCTS_DEFAULT_SIMULATIONS = 50
MCTS_MAX_SIMULATIONS = 200

# Agent Configuration
AGENT_TIMEOUT = 120  # seconds for multimodal
MAX_TOKENS = {
    "default": 200,
    "extractive": 150,
    "detailed": 250,
    "tldr": 100,
    "multimodal": 300
}

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 7860
DEBUG_MODE = True

# Media Processing
MAX_IMAGES = 10
VIDEO_FRAME_SAMPLE_RATE = 30  # Sample every Nth frame

# MCTS Variants Flags (can be overridden per request)
USE_REFLECTION = True      # R-MCTS: self-evaluation to reduce hallucinations
USE_RAG = True             # MCTS-RAG: retrieval-based grounding
USE_WORLD_GUIDANCE = True  # World-Guided MCTS: structured world knowledge

# Knowledge Base for RAG (simulated)
SIMULATED_KNOWLEDGE_BASE = {
    "artificial intelligence": "AI is the simulation of human intelligence in machines.",
    "machine learning": "ML is a subset of AI that enables systems to learn from data.",
    "neural networks": "Neural networks are computing systems inspired by biological brains.",
    "climate change": "Climate change refers to long-term shifts in temperatures and weather patterns.",
    "renewable energy": "Renewable energy comes from natural sources that are replenished constantly.",
}

# World Knowledge Graph for World-Guided MCTS (simulated)
WORLD_KNOWLEDGE_GRAPH = [
    ("AI", "field_of", "Computer Science"),
    ("Machine Learning", "subset_of", "AI"),
    ("Deep Learning", "subset_of", "Machine Learning"),
    ("Renewable Energy", "includes", "Solar Power"),
    ("Solar Power", "type_of", "Renewable Energy"),
]