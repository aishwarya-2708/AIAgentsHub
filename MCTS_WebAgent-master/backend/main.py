# # backend/main.py

# from fastapi import FastAPI, Request
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from models import QueryRequest
# from agent import handle_query
# from tools.mail import send_email, fetch_unread_emails
# from pydantic import BaseModel
# from typing import Optional
# import traceback

# app = FastAPI()

# # Global exception handler — always returns JSON, never plain text
# @app.exception_handler(Exception)
# async def global_exception_handler(request: Request, exc: Exception):
#     return JSONResponse(
#         status_code=500,
#         content={"error": str(exc), "detail": traceback.format_exc()[-500:]},
#     )

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=False,
#     allow_methods=["GET", "POST", "OPTIONS"],
#     allow_headers=["Content-Type", "Accept", "Authorization"],
# )


# # ------------------------------------------------------------------
# # Request models
# # ------------------------------------------------------------------

# class EmailSendRequest(BaseModel):
#     recipient:        str
#     subject:          str
#     body:             str
#     attachment_data:  Optional[str] = None   # base64-encoded file bytes
#     attachment_name:  Optional[str] = None   # original filename with extension


# class ScrapeRequest(BaseModel):
#     url: str


# class MCTSVariantRequest(BaseModel):
#     query:       str
#     variant:     str = "basic-mcts"
#     simulations: Optional[int] = 5


# class BenchmarkRequest(BaseModel):
#     query:       str
#     simulations: Optional[int] = 5


# # ------------------------------------------------------------------
# # Existing endpoints
# # ------------------------------------------------------------------

# @app.get("/")
# async def root():
#     return {"Message": "✅ MCTS Web Agent is running...🚀"}


# @app.get("/health")
# def health():
#     return {"Status": "Running ✅"}


# @app.post("/ask")
# def ask(request: QueryRequest):
#     return handle_query(
#         request.query,
#         mcts_variant=request.variant,
#         simulations=request.simulations,
#     )


# @app.post("/send-email")
# def send_email_endpoint(request: EmailSendRequest):
#     result = send_email(
#         recipient       = request.recipient,
#         subject         = request.subject,
#         body            = request.body,
#         attachment_data = request.attachment_data,
#         attachment_name = request.attachment_name,
#     )
#     return {"message": result}


# @app.post("/fetch-emails")
# def fetch_emails_endpoint():
#     result = fetch_unread_emails()
#     return {"message": result}


# # ------------------------------------------------------------------
# # MCTS variant endpoint
# # ------------------------------------------------------------------

# @app.post("/mcts/run")
# def run_mcts_variant(request: MCTSVariantRequest):
#     """Run a specific MCTS variant: basic-mcts | r-mcts | wm-mcts | rag-mcts"""
#     from mcts.variants import VARIANT_RUNNERS

#     variant_key = request.variant.lower()
#     if variant_key not in VARIANT_RUNNERS:
#         return {
#             "error": f"Unknown variant '{variant_key}'. Choose from: {list(VARIANT_RUNNERS.keys())}"
#         }

#     runner = VARIANT_RUNNERS[variant_key]
#     result = runner(request.query, request.simulations)
#     return result


# # ------------------------------------------------------------------
# # Benchmark — runs all 4 variants
# # ------------------------------------------------------------------

# @app.post("/mcts/benchmark")
# def benchmark_mcts(request: BenchmarkRequest):
#     """
#     Run all 4 MCTS variants (Basic-MCTS, R-MCTS, WM-MCTS, MCTS-RAG)
#     on the same query and return speed + accuracy analysis table.
#     """
#     from mcts.benchmark import run_benchmark
#     return run_benchmark(request.query, request.simulations)


# # ------------------------------------------------------------------
# # List available variants
# # ------------------------------------------------------------------

# @app.get("/mcts/variants")
# def list_variants():
#     return {
#         "variants": [
#             {
#                 "key":         "basic-mcts",
#                 "name":        "Basic-MCTS",
#                 "label":       "Standard MCTS",
#                 "description": "Pure UCB1 selection, random rollout, heuristic scoring. Baseline variant.",
#             },
#             {
#                 "key":         "r-mcts",
#                 "name":        "R-MCTS",
#                 "label":       "Retrieval MCTS",
#                 "description": "Live web retrieval per node — action selection grounded in freshly fetched content.",
#             },
#             {
#                 "key":         "wm-mcts",
#                 "name":        "WM-MCTS",
#                 "label":       "World-Model MCTS",
#                 "description": "LLM predicts action quality before expansion — most accurate.",
#             },
#             {
#                 "key":         "rag-mcts",
#                 "name":        "MCTS-RAG",
#                 "label":       "RAG-Augmented MCTS",
#                 "description": "Retrieves live context upfront to guide search — context-aware.",
#             },
#         ]
#     }


# if __name__ == "__main__":
#     import uvicorn
#     print("🚀 Starting MCTS Web Agent Backend...")
#     print("📡 Server: http://localhost:8000")
#     print("📚 Docs: http://localhost:8000/docs")
#     print("🔄 Running OFFLINE with local Ollama LLM")
#     print("\n⚡ Press CTRL+C to stop\n")

#     uvicorn.run(
#         "main:app",
#         host="127.0.0.1",
#         port=8000,
#         reload=True,
#         log_level="info",
#     )
#################################################################
# backend/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from models import QueryRequest
from agent import handle_query
from tools.mail import send_email, fetch_unread_emails
from pydantic import BaseModel
from typing import Optional
import traceback

app = FastAPI()

# Global exception handler — always returns JSON, never plain text
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": traceback.format_exc()[-500:]},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization"],
)


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class EmailSendRequest(BaseModel):
    recipient:        str
    subject:          str
    body:             str
    attachment_data:  Optional[str] = None   # base64-encoded file bytes
    attachment_name:  Optional[str] = None   # original filename with extension


class ScrapeRequest(BaseModel):
    url: str


class MCTSVariantRequest(BaseModel):
    query:       str
    variant:     str = "basic-mcts"
    simulations: Optional[int] = 5


class BenchmarkRequest(BaseModel):
    query:       str
    simulations: Optional[int] = 5


class BenchmarkActionRequest(BaseModel):
    action_type:  str            = "chat"      # chat|price-compare|scrape-data|send-email|fetch-email
    inputs:       dict           = {}           # action-specific inputs
    simulations:  Optional[int]  = 5


# ------------------------------------------------------------------
# Existing endpoints
# ------------------------------------------------------------------

@app.get("/")
async def root():
    return {"Message": "✅ MCTS Web Agent is running...🚀"}


@app.get("/health")
def health():
    return {"Status": "Running ✅"}


@app.post("/ask")
def ask(request: QueryRequest):
    return handle_query(
        request.query,
        mcts_variant=request.variant,
        simulations=request.simulations,
    )


@app.post("/send-email")
def send_email_endpoint(request: EmailSendRequest):
    result = send_email(
        recipient       = request.recipient,
        subject         = request.subject,
        body            = request.body,
        attachment_data = request.attachment_data,
        attachment_name = request.attachment_name,
    )
    return {"message": result}


@app.post("/fetch-emails")
def fetch_emails_endpoint():
    result = fetch_unread_emails()
    return {"message": result}


# ------------------------------------------------------------------
# MCTS variant endpoint
# ------------------------------------------------------------------

@app.post("/mcts/run")
def run_mcts_variant(request: MCTSVariantRequest):
    """Run a specific MCTS variant: basic-mcts | r-mcts | wm-mcts | rag-mcts"""
    from mcts.variants import VARIANT_RUNNERS

    variant_key = request.variant.lower()
    if variant_key not in VARIANT_RUNNERS:
        return {
            "error": f"Unknown variant '{variant_key}'. Choose from: {list(VARIANT_RUNNERS.keys())}"
        }

    runner = VARIANT_RUNNERS[variant_key]
    result = runner(request.query, request.simulations)
    return result


# ------------------------------------------------------------------
# Benchmark — runs all 4 variants
# ------------------------------------------------------------------

@app.post("/mcts/benchmark")
def benchmark_mcts(request: BenchmarkRequest):
    """
    Legacy endpoint — chat query benchmark.
    Run all 4 MCTS variants and return analysis table.
    """
    from mcts.benchmark import run_benchmark
    return run_benchmark(request.query, request.simulations)


@app.post("/mcts/benchmark-action")
def benchmark_mcts_action(request: BenchmarkActionRequest):
    """
    Action-aware benchmark — works for ALL 5 action types.
    Compares all 4 MCTS variants on the planning task for this action.

    Body:
      action_type: "chat" | "price-compare" | "scrape-data" |
                   "send-email" | "fetch-email"
      inputs: {
        chat:          {"query": "..."}
        price-compare: {"product": "...", "official_url": "..."}
        scrape-data:   {"url": "..."}
        send-email:    {"recipient": "...", "subject": "...", "body": "..."}
        fetch-email:   {}
      }
      simulations: 2-15 (default 5)
    """
    from mcts.benchmark import run_benchmark_action
    return run_benchmark_action(
        action_type=request.action_type,
        inputs=request.inputs,
        simulations=request.simulations,
    )


# ------------------------------------------------------------------
# List available variants
# ------------------------------------------------------------------

@app.get("/mcts/variants")
def list_variants():
    return {
        "variants": [
            {
                "key":         "basic-mcts",
                "name":        "Basic-MCTS",
                "label":       "Standard MCTS",
                "description": "Pure UCB1 selection, random rollout, heuristic scoring. Baseline variant.",
            },
            {
                "key":         "r-mcts",
                "name":        "R-MCTS",
                "label":       "Retrieval MCTS",
                "description": "Live web retrieval per node — action selection grounded in freshly fetched content.",
            },
            {
                "key":         "wm-mcts",
                "name":        "WM-MCTS",
                "label":       "World-Model MCTS",
                "description": "LLM predicts action quality before expansion — most accurate.",
            },
            {
                "key":         "rag-mcts",
                "name":        "MCTS-RAG",
                "label":       "RAG-Augmented MCTS",
                "description": "Retrieves live context upfront to guide search — context-aware.",
            },
        ]
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MCTS Web Agent Backend...")
    print("📡 Server: http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")
    print("🔄 Running OFFLINE with local Ollama LLM")
    print("\n⚡ Press CTRL+C to stop\n")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )