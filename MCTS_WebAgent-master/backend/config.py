
# ###############################################################

# # backend/config.py

# # ──────────────────────────────────────────────
# # LLM Configuration
# # ──────────────────────────────────────────────
# OLLAMA_MODEL    = "llama3.2"
# OLLAMA_BASE_URL = "http://localhost:11434"

# # ──────────────────────────────────────────────
# # MCTS Core Configuration
# # ──────────────────────────────────────────────
# MCTS_SIMULATIONS        = 5   # Simulations for web-scraping MCTS (ecommerce)
# MCTS_WEB_SCRAPING_RETRIES = 2  # Retry attempts for general web scraping
# MAX_MCTS_DEPTH          = 3   # Max depth for MCTS planning tree

# # ──────────────────────────────────────────────
# # MCTS Variant Configuration
# # ──────────────────────────────────────────────

# # R-MCTS (Retrieval MCTS)
# # Fetches Wikipedia snippets per node via API — timeout keeps it fast
# R_MCTS_RETRIEVAL_TIMEOUT  = 4    # seconds per Wikipedia API call
# R_MCTS_RETRIEVAL_TOP_K    = 2    # snippets to fetch per (query, action) pair
# R_MCTS_MAX_DEPTH          = 3    # tree depth for R-MCTS

# # WM-MCTS (World-Model-Guided MCTS)
# # Uses local LLM to score each candidate action before expanding
# WM_MCTS_MAX_DEPTH         = 3    # tree depth for WM-MCTS

# # MCTS-RAG (Retrieval-Augmented MCTS)
# # Seeds retriever once from Wikipedia before search starts
# RAG_MCTS_MAX_DEPTH        = 3    # tree depth for MCTS-RAG
# RAG_MCTS_SEED_LIMIT       = 2    # Wikipedia results to seed retriever with

# # ──────────────────────────────────────────────
# # Rate Limiting
# # ──────────────────────────────────────────────
# LLM_RATE_LIMIT_DELAY = 0.1   # 100ms between LLM calls
# WEB_REQUEST_DELAY    = 0.5   # 500ms between web requests
# REQUEST_TIMEOUT      = 10    # 10 seconds timeout for web requests

# # ──────────────────────────────────────────────
# # Search / Scraping
# # ──────────────────────────────────────────────
# MAX_SEARCH_RESULTS  = 8      # Limit search results for faster processing
# MAX_SCRAPE_CONTENT  = 3000   # Max characters for scraped content

# # ──────────────────────────────────────────────
# # E-commerce
# # ──────────────────────────────────────────────
# MANDATORY_PLATFORMS = ['Amazon India', 'Flipkart', 'Myntra']
# PRICE_RANGE_MIN     = 50      # Minimum valid price in INR
# PRICE_RANGE_MAX     = 500000  # Maximum valid price in INR

# backend/config.py

# ──────────────────────────────────────────────
# LLM Configuration
# ──────────────────────────────────────────────
OLLAMA_MODEL    = "llama3.2:1b"
OLLAMA_BASE_URL = "http://localhost:11434"

# ──────────────────────────────────────────────
# MCTS Core Configuration
# ──────────────────────────────────────────────
MCTS_SIMULATIONS        = 5   # Simulations for web-scraping MCTS (ecommerce)
MCTS_WEB_SCRAPING_RETRIES = 2  # Retry attempts for general web scraping
MAX_MCTS_DEPTH          = 3   # Max depth for MCTS planning tree

# ──────────────────────────────────────────────
# MCTS Variant Configuration
# ──────────────────────────────────────────────

# R-MCTS (Retrieval MCTS)
# Fetches Wikipedia snippets per node via API — timeout keeps it fast
R_MCTS_RETRIEVAL_TIMEOUT  = 4    # seconds per Wikipedia API call
R_MCTS_RETRIEVAL_TOP_K    = 2    # snippets to fetch per (query, action) pair
R_MCTS_MAX_DEPTH          = 3    # tree depth for R-MCTS

# WM-MCTS (World-Model-Guided MCTS)
# Uses local LLM to score each candidate action before expanding
WM_MCTS_MAX_DEPTH         = 3    # tree depth for WM-MCTS

# MCTS-RAG (Retrieval-Augmented MCTS)
# Seeds retriever once from Wikipedia before search starts
RAG_MCTS_MAX_DEPTH        = 3    # tree depth for MCTS-RAG
RAG_MCTS_SEED_LIMIT       = 2    # Wikipedia results to seed retriever with

# ──────────────────────────────────────────────
# Rate Limiting
# ──────────────────────────────────────────────
LLM_RATE_LIMIT_DELAY = 0.1   # 100ms between LLM calls
WEB_REQUEST_DELAY    = 0.5   # 500ms between web requests
REQUEST_TIMEOUT      = 10    # 10 seconds timeout for web requests

# ──────────────────────────────────────────────
# Search / Scraping
# ──────────────────────────────────────────────
MAX_SEARCH_RESULTS  = 8      # Limit search results for faster processing
MAX_SCRAPE_CONTENT  = 3000   # Max characters for scraped content

# ──────────────────────────────────────────────
# E-commerce
# ──────────────────────────────────────────────
MANDATORY_PLATFORMS = ['Amazon India', 'Flipkart', 'Myntra']
PRICE_RANGE_MIN     = 50      # Minimum valid price in INR
PRICE_RANGE_MAX     = 500000  # Maximum valid price in INR


# ──────────────────────────────────────────────────────────────────
# E-commerce Tier Scraper Timeouts
# ──────────────────────────────────────────────────────────────────
TIER1_TIMEOUT   = 12    # Price comparison sites (smartprix, 91mobiles etc)
TIER2_TIMEOUT   = 10    # Direct platform scraping (amazon, flipkart)
TIER3_TIMEOUT   = 8     # Search engine snippets (bing)
SCRAPE_RETRIES  = 2     # Retry attempts per platform