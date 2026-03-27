# # backend/mcts/variants/rag_mcts.py
# """
# MCTS-RAG (Retrieval-Augmented MCTS)
# Augments standard MCTS with a retrieval step: before evaluating a node,
# it retrieves relevant context (from scraped content or a local knowledge
# store) and uses that to improve both action selection and scoring.

# In this implementation the "retrieval" step fetches a live web summary
# for the query when available, then passes that context to the evaluator.
# For offline/fast runs it falls back to a keyword-based relevance score.
# """

# import time
# import re
# import random
# from ..nodes import MonteCarloTreeSearchNode
# from config import RAG_MCTS_MAX_DEPTH, RAG_MCTS_SEED_LIMIT


# # ------------------------------------------------------------------
# # RAG Retriever — lightweight in-memory store + optional web fetch
# # ------------------------------------------------------------------

# class RAGRetriever:
#     """
#     Simple retrieval layer.
#     - Stores any text chunks passed in during the session.
#     - Scores a (query, steps) pair using keyword overlap with stored chunks.
#     - Optionally asks the LLM to summarise retrieved context for scoring.
#     """

#     def __init__(self):
#         self._chunks: list[str] = []
#         self._query_context: dict[str, str] = {}

#     def add_chunk(self, text: str):
#         self._chunks.append(text[:500])  # Cap chunk size

#     def retrieve(self, query: str, top_k: int = 3) -> list[str]:
#         """Return top-k chunks most relevant to query (keyword overlap)."""
#         if not self._chunks:
#             return []

#         q_words = set(query.lower().split())
#         scored = []
#         for chunk in self._chunks:
#             overlap = len(q_words & set(chunk.lower().split()))
#             scored.append((overlap, chunk))

#         scored.sort(key=lambda x: x[0], reverse=True)
#         return [c for _, c in scored[:top_k]]

#     def score_with_context(self, query: str, steps: list) -> float:
#         """
#         Score a plan using retrieved context + LLM (with fallback to heuristic).
#         """
#         retrieved = self.retrieve(query)
#         context_text = "\n".join(retrieved) if retrieved else "No additional context available."

#         try:
#             from llm import get_llm
#             llm = get_llm()

#             prompt = f"""You are evaluating a task plan using retrieved context.

# Task: {query}

# Retrieved Context:
# {context_text}

# Proposed Plan Steps: {' -> '.join(steps)}

# Rate this plan's quality from 1 to 10 (integer only).
# Consider: how well the plan uses available context, logical order, completeness.
# Reply with ONLY the integer score."""

#             response = str(llm.invoke(prompt)).strip()
#             match = re.search(r'\b([0-9]|10)\b', response)
#             score = float(match.group(1)) if match else 5.0

#         except Exception:
#             score = self._heuristic_score(query, steps, retrieved)

#         return min(max(score, 1.0), 10.0)

#     def _heuristic_score(self, query: str, steps: list, context: list) -> float:
#         score = 5.0
#         q = query.lower()

#         # Context bonus: if retrieved chunks are non-empty
#         if context:
#             score += min(len(context) * 0.5, 1.5)

#         # Step quality scoring
#         if any(w in q for w in ['buy', 'compare', 'price']):
#             for s in steps:
#                 if 'Search' in s:
#                     score += 1.5
#                 elif 'Compare' in s or 'Extract' in s:
#                     score += 2.0
#                 elif 'Recommend' in s or 'Finalize' in s:
#                     score += 1.5
#         else:
#             for s in steps:
#                 if 'Gather' in s or 'Research' in s:
#                     score += 1.0
#                 elif 'Analyze' in s or 'Compare' in s:
#                     score += 1.5
#                 elif 'Recommend' in s or 'Conclude' in s or 'Finalize' in s:
#                     score += 2.0

#         # Penalties
#         if len(steps) != len(set(steps)):
#             score -= 3.0
#         if len(steps) > 5:
#             score -= 1.0

#         return score


# # Shared retriever for one planning session
# _retriever = RAGRetriever()


# def seed_retriever_from_web(query: str):
#     """
#     Attempt to fetch a brief web summary to seed the retriever.
#     Silently skips if web is unavailable.
#     """
#     try:
#         import requests
#         search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query.replace(' ', '+')}&format=json&srlimit={RAG_MCTS_SEED_LIMIT}"
#         resp = requests.get(search_url, timeout=5)
#         if resp.status_code == 200:
#             data = resp.json()
#             snippets = data.get("query", {}).get("search", [])
#             for item in snippets:
#                 snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
#                 if snippet:
#                     _retriever.add_chunk(snippet)
#     except Exception:
#         pass  # Graceful degradation — RAG still works with empty store


# # ------------------------------------------------------------------
# # RAG-MCTS State
# # ------------------------------------------------------------------

# class RAGMCTSState:

#     def __init__(self, query: str, steps=None, depth=0, max_depth=RAG_MCTS_MAX_DEPTH):
#         self.query = query
#         self.steps = steps or []
#         self.depth = depth
#         self.max_depth = max_depth

#     def get_possible_actions(self):
#         q = self.query.lower()

#         if any(w in q for w in ['buy', 'purchase', 'compare', 'price', 'shop']):
#             base = [
#                 "Search Primary Platform",
#                 "Search Secondary Platform",
#                 "Extract Product Details",
#                 "Compare Prices",
#                 "Retrieve Product Reviews",
#                 "Analyze Retrieved Data",
#                 "Finalize Recommendation",
#             ]
#         elif any(w in q for w in ['plan', 'book', 'trip', 'schedule']):
#             base = [
#                 "Retrieve Destination Info",
#                 "Research Destinations",
#                 "Check Availability",
#                 "Compare Options",
#                 "Create Itinerary",
#                 "Finalize Plan",
#             ]
#         elif any(w in q for w in ['analyze', 'data', 'research', 'study']):
#             base = [
#                 "Retrieve Background Information",
#                 "Gather Information",
#                 "Analyze Retrieved Data",
#                 "Compare Alternatives",
#                 "Draw Conclusions",
#                 "Provide Recommendations",
#             ]
#         else:
#             base = [
#                 "Retrieve Relevant Context",
#                 "Research Topic",
#                 "Gather Information",
#                 "Analyze Options",
#                 "Provide Recommendations",
#             ]

#         return [a for a in base if a not in self.steps]

#     def move(self, action):
#         return RAGMCTSState(
#             self.query,
#             self.steps + [action],
#             self.depth + 1,
#             self.max_depth,
#         )

#     def is_terminal(self):
#         return self.depth >= self.max_depth

#     def evaluate(self):
#         if not self.steps:
#             return 5.0
#         return _retriever.score_with_context(self.query, self.steps)


# # ------------------------------------------------------------------
# # RAG-MCTS Node
# # ------------------------------------------------------------------

# class RAGMCTSNode(MonteCarloTreeSearchNode):

#     def untried_actions(self):
#         tried = {child.state.steps[-1] for child in self.children if child.state.steps}
#         return [a for a in self.state.get_possible_actions() if a not in tried]

#     def expand(self):
#         untried = self.untried_actions()
#         if not untried:
#             return self

#         # RAG-informed: prefer "Retrieve" actions early in the plan
#         retrieve_actions = [a for a in untried if 'Retrieve' in a]
#         if retrieve_actions and self.state.depth == 0:
#             action = retrieve_actions[0]
#         else:
#             action = random.choice(untried)

#         child = RAGMCTSNode(self.state.move(action), parent=self)
#         self.children.append(child)
#         return child

#     def is_terminal_node(self):
#         return self.state.is_terminal()

#     def rollout(self):
#         """RAG-augmented rollout: mix of retrieval-priority and random"""
#         state = self.state
#         while not state.is_terminal():
#             actions = state.get_possible_actions()
#             if not actions:
#                 break

#             # Prefer retrieval actions early
#             retrieve_acts = [a for a in actions if 'Retrieve' in a]
#             if retrieve_acts and state.depth <= 1:
#                 action = retrieve_acts[0]
#             else:
#                 action = random.choice(actions)

#             state = state.move(action)

#         return state.evaluate()


# # ------------------------------------------------------------------
# # RAG-MCTS Runner
# # ------------------------------------------------------------------

# def run_rag_mcts(query: str, simulations: int = 5) -> dict:
#     """
#     Run MCTS-RAG planning for the given query.

#     Returns:
#         dict with keys: plan, score, time_ms, variant
#     """
#     from ..search import MonteCarloTreeSearch

#     # Reset retriever and seed with any available context
#     global _retriever
#     _retriever = RAGRetriever()
#     seed_retriever_from_web(query)

#     t0 = time.perf_counter()

#     initial_state = RAGMCTSState(query, max_depth=RAG_MCTS_MAX_DEPTH)
#     root = RAGMCTSNode(initial_state)
#     mcts = MonteCarloTreeSearch(root)

#     best_node = mcts.best_action(simulations)

#     elapsed_ms = (time.perf_counter() - t0) * 1000

#     plan = best_node.state.steps if best_node.state.steps else ["Direct Response"]
#     score = best_node.state.evaluate()

#     retrieved_chunks = len(_retriever._chunks)

#     return {
#         "variant": "MCTS-RAG",
#         "plan": plan,
#         "score": round(score, 2),
#         "simulations": simulations,
#         "time_ms": round(elapsed_ms, 2),
#         "retrieved_chunks": retrieved_chunks,
#         "description": "MCTS-RAG — retrieval-augmented MCTS with context-informed scoring",
#     }
################################################################################
# backend/mcts/variants/rag_mcts.py
"""MCTS-RAG — Retrieval-Augmented MCTS. Nothing runs at module level."""

import sys
import os
import time
import random
import re


def _setup():
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import RAG_MCTS_MAX_DEPTH, RAG_MCTS_SEED_LIMIT
    from mcts.nodes import MonteCarloTreeSearchNode
    from mcts.search import MonteCarloTreeSearch
    return RAG_MCTS_MAX_DEPTH, RAG_MCTS_SEED_LIMIT, MonteCarloTreeSearchNode, MonteCarloTreeSearch


def run_rag_mcts(query: str, simulations: int = 5) -> dict:

    RAG_MCTS_MAX_DEPTH, RAG_MCTS_SEED_LIMIT, MonteCarloTreeSearchNode, MonteCarloTreeSearch = _setup()

    # ── Retriever ─────────────────────────────────────────────────
    chunks = []

    def seed_retriever():
        try:
            import requests
            resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={"action":"query","list":"search","srsearch":query,
                        "format":"json","srlimit":RAG_MCTS_SEED_LIMIT},
                timeout=4, headers={"User-Agent":"MCTS-RAG/1.0"})
            if resp.status_code == 200:
                for item in resp.json().get("query",{}).get("search",[]):
                    s = re.sub(r'<[^>]+>','',item.get("snippet","")).strip()
                    if s: chunks.append(s[:400])
        except Exception:
            pass

    def retrieve(q, top_k=3):
        if not chunks: return []
        qw = set(q.lower().split())
        return sorted(chunks, key=lambda c: len(qw & set(c.lower().split())),
                      reverse=True)[:top_k]

    def score_state(q, steps):
        ctx = "\n".join(retrieve(q)) or "No context."
        try:
            from llm import get_llm
            prompt = (f"Rate plan 1-10 using context.\nTask: {q}\n"
                      f"Context: {ctx}\nSteps: {' -> '.join(steps)}\nReply integer only.")
            resp = str(get_llm().invoke(prompt)).strip()
            m    = re.search(r'\b([0-9]|10)\b', resp)
            s    = float(m.group(1)) if m else 5.0
        except Exception:
            s = 5.0 + min(len(retrieve(q)) * 0.5, 1.5)
            for step in steps:
                if 'Retrieve' in step or 'Search' in step: s += 1.0
                elif 'Analyze' in step or 'Compare' in step: s += 1.5
                elif 'Recommend' in step or 'Finalize' in step: s += 2.0
            if len(steps) != len(set(steps)): s -= 3.0
        return min(max(s, 1.0), 10.0)

    seed_retriever()

    # ── State ─────────────────────────────────────────────────────
    class RAGMCTSState:
        def __init__(self, q, steps=None, depth=0, max_depth=RAG_MCTS_MAX_DEPTH):
            self.query = q; self.steps = steps or []
            self.depth = depth; self.max_depth = max_depth

        def get_possible_actions(self):
            q = self.query.lower()
            if any(w in q for w in ['buy','purchase','compare','price','shop']):
                base = ["Search Product Listings","Retrieve Price Data",
                        "Compare Platform Prices","Extract Product Specifications",
                        "Retrieve Customer Reviews","Finalize Best Deal"]
            elif any(w in q for w in ['plan','book','trip','schedule']):
                base = ["Retrieve Destination Information","Check Availability",
                        "Compare Travel Options","Create Itinerary","Finalize Plan"]
            elif any(w in q for w in ['analyze','data','research','study']):
                base = ["Retrieve Background Information","Gather Statistical Data",
                        "Analyze Retrieved Data","Compare Alternatives",
                        "Draw Evidence-Based Conclusions","Provide Recommendations"]
            else:
                base = ["Retrieve Relevant Information","Research Topic",
                        "Analyze Retrieved Content","Synthesize Findings",
                        "Provide Recommendations"]
            return [a for a in base if a not in self.steps]

        def move(self, action):
            return RAGMCTSState(self.query, self.steps+[action],
                                self.depth+1, self.max_depth)

        def is_terminal(self):
            return self.depth >= self.max_depth

        def evaluate(self):
            return score_state(self.query, self.steps) if self.steps else 5.0

    # ── Node ──────────────────────────────────────────────────────
    class RAGMCTSNode(MonteCarloTreeSearchNode):
        def untried_actions(self):
            tried = {c.state.steps[-1] for c in self.children if c.state.steps}
            return [a for a in self.state.get_possible_actions() if a not in tried]

        def expand(self):
            untried = self.untried_actions()
            if not untried: return self
            ra = [a for a in untried if 'Retrieve' in a]
            action = ra[0] if (ra and self.state.depth == 0) else random.choice(untried)
            child  = RAGMCTSNode(self.state.move(action), parent=self)
            self.children.append(child)
            return child

        def is_terminal_node(self):
            return self.state.is_terminal()

        def rollout(self):
            state = self.state
            while not state.is_terminal():
                acts = state.get_possible_actions()
                if not acts: break
                ra = [a for a in acts if 'Retrieve' in a]
                state = state.move(ra[0] if (ra and state.depth <= 1) else random.choice(acts))
            return state.evaluate()

    # ── Run ───────────────────────────────────────────────────────
    root      = RAGMCTSNode(RAGMCTSState(query))
    t0        = time.perf_counter()
    best_node = MonteCarloTreeSearch(root).best_action(simulations)
    elapsed   = (time.perf_counter() - t0) * 1000
    plan      = best_node.state.steps or ["Direct Response"]
    score     = best_node.state.evaluate()

    return {
        "variant": "MCTS-RAG", "plan": plan,
        "score": round(score, 2), "simulations": simulations,
        "time_ms": round(elapsed, 2),
        "retrieved_chunks": len(chunks),
        "description": "MCTS-RAG — seeds context from Wikipedia before search.",
    }   