# # backend/mcts/variants/r_mcts.py
# """
# R-MCTS (Retrieval MCTS)
# =======================
# Retrieval-driven MCTS where real web content is fetched PER NODE during
# tree expansion. Each candidate action triggers a targeted retrieval step
# that fetches live content relevant to that action, then uses the retrieved
# text to score the node — making expansion decisions data-grounded rather
# than purely heuristic.

# Key distinction from MCTS-RAG:
#   - MCTS-RAG: retrieves context ONCE before the search starts (batch seeding)
#   - R-MCTS:   retrieves context AT EACH NODE during expansion (per-node retrieval)

# This means R-MCTS always works with the freshest, most action-specific data
# at the cost of more retrieval calls. It gracefully degrades to heuristic
# scoring when retrieval fails (offline / rate-limited).
# """

# import time
# import re
# import requests
# from ..nodes import MonteCarloTreeSearchNode
# from config import R_MCTS_RETRIEVAL_TIMEOUT, R_MCTS_RETRIEVAL_TOP_K, R_MCTS_MAX_DEPTH


# # ──────────────────────────────────────────────────────────────────
# # Per-node Retriever
# # ──────────────────────────────────────────────────────────────────

# class PerNodeRetriever:
#     """
#     Fetches a short text snippet relevant to a specific (query + action) pair.
#     Uses Wikipedia search API as the retrieval backend — no API key needed,
#     works fully offline-graceful.

#     Results are cached by (query, action) key to avoid duplicate fetches
#     within one planning run.
#     """

#     WIKI_API = "https://en.wikipedia.org/w/api.php"
#     TIMEOUT  = R_MCTS_RETRIEVAL_TIMEOUT  # from config.py

#     def __init__(self):
#         self._cache: dict = {}

#     def retrieve(self, query: str, action: str, top_k: int = R_MCTS_RETRIEVAL_TOP_K) -> list:
#         """
#         Retrieve snippets relevant to (query + action).
#         Returns list of plain-text snippets (may be empty on failure).
#         """
#         cache_key = f"{query[:50]}|{action}"
#         if cache_key in self._cache:
#             return self._cache[cache_key]

#         snippets = self._fetch_wikipedia(query, action, top_k)
#         self._cache[cache_key] = snippets
#         return snippets

#     def _fetch_wikipedia(self, query: str, action: str, top_k: int) -> list:
#         """Query Wikipedia search API and return cleaned snippets."""
#         action_keywords = self._extract_action_keywords(action)
#         search_term = f"{query} {action_keywords}".strip()[:100]

#         try:
#             params = {
#                 "action":   "query",
#                 "list":     "search",
#                 "srsearch": search_term,
#                 "format":   "json",
#                 "srlimit":  top_k,
#             }
#             resp = requests.get(
#                 self.WIKI_API,
#                 params=params,
#                 timeout=self.TIMEOUT,
#                 headers={"User-Agent": "R-MCTS-Agent/1.0"},
#             )
#             if resp.status_code != 200:
#                 return []

#             data = resp.json()
#             results = data.get("query", {}).get("search", [])
#             snippets = []
#             for item in results:
#                 raw = item.get("snippet", "")
#                 clean = re.sub(r"<[^>]+>", "", raw).strip()
#                 if clean:
#                     snippets.append(clean[:400])
#             return snippets

#         except Exception:
#             return []

#     @staticmethod
#     def _extract_action_keywords(action: str) -> str:
#         """Pull meaningful keywords from an action label."""
#         stop = {"primary", "secondary", "final", "finalize", "create", "provide",
#                 "gather", "check", "extract", "draw"}
#         words = [w for w in action.lower().split() if w not in stop and len(w) > 2]
#         return " ".join(words[:3])


# # ──────────────────────────────────────────────────────────────────
# # R-MCTS State
# # ──────────────────────────────────────────────────────────────────

# class RMCTSState:
#     """
#     State for Retrieval MCTS.
#     Carries the accumulated retrieved_context forward so each node
#     inherits the evidence gathered along its branch.
#     """

#     def __init__(self, query: str, steps=None, retrieved_context=None,
#                  depth=0, max_depth=R_MCTS_MAX_DEPTH):
#         self.query             = query
#         self.steps             = steps or []
#         self.retrieved_context = retrieved_context or []
#         self.depth             = depth
#         self.max_depth         = max_depth

#     # ── Action space ──────────────────────────────────────────────

#     def get_possible_actions(self) -> list:
#         q = self.query.lower()

#         if any(w in q for w in ["buy", "purchase", "compare", "price", "shop"]):
#             pool = [
#                 "Search Product Listings",
#                 "Retrieve Price Data",
#                 "Compare Platform Prices",
#                 "Extract Product Specifications",
#                 "Retrieve Customer Reviews",
#                 "Finalize Best Deal",
#             ]
#         elif any(w in q for w in ["plan", "book", "trip", "schedule", "itinerary"]):
#             pool = [
#                 "Retrieve Destination Information",
#                 "Check Availability",
#                 "Compare Travel Options",
#                 "Retrieve User Reviews",
#                 "Create Itinerary",
#                 "Finalize Plan",
#             ]
#         elif any(w in q for w in ["analyze", "data", "research", "study", "compare"]):
#             pool = [
#                 "Retrieve Background Information",
#                 "Gather Statistical Data",
#                 "Analyze Retrieved Data",
#                 "Compare Alternatives",
#                 "Draw Evidence-Based Conclusions",
#                 "Provide Recommendations",
#             ]
#         else:
#             pool = [
#                 "Retrieve Relevant Information",
#                 "Research Topic",
#                 "Analyze Retrieved Content",
#                 "Synthesize Findings",
#                 "Provide Recommendations",
#             ]

#         return [a for a in pool if a not in self.steps]

#     # ── Transition ─────────────────────────────────────────────────

#     def move(self, action: str, new_snippets=None) -> "RMCTSState":
#         """Create successor state, appending newly retrieved snippets."""
#         combined_context = self.retrieved_context + (new_snippets or [])
#         return RMCTSState(
#             self.query,
#             self.steps + [action],
#             combined_context,
#             self.depth + 1,
#             self.max_depth,
#         )

#     def is_terminal(self) -> bool:
#         return self.depth >= self.max_depth

#     # ── Evaluation ─────────────────────────────────────────────────

#     def evaluate(self) -> float:
#         """
#         Score using:
#           1. Step quality heuristic
#           2. Retrieved context relevance bonus (keyword overlap)
#         """
#         base = self._heuristic_score()

#         if self.retrieved_context:
#             base += self._context_relevance_score()

#         return min(max(base, 1.0), 10.0)

#     def _heuristic_score(self) -> float:
#         score = 4.0

#         step_values = {
#             "Search Product Listings":           2.0,
#             "Retrieve Price Data":               2.5,
#             "Compare Platform Prices":           3.0,
#             "Extract Product Specifications":    2.0,
#             "Retrieve Customer Reviews":         1.8,
#             "Finalize Best Deal":                3.0,
#             "Retrieve Destination Information":  2.0,
#             "Check Availability":                1.8,
#             "Compare Travel Options":            2.5,
#             "Retrieve User Reviews":             1.8,
#             "Create Itinerary":                  2.5,
#             "Finalize Plan":                     2.5,
#             "Retrieve Background Information":   2.0,
#             "Gather Statistical Data":           2.0,
#             "Analyze Retrieved Data":            2.5,
#             "Compare Alternatives":              2.5,
#             "Draw Evidence-Based Conclusions":   2.8,
#             "Provide Recommendations":           2.8,
#             "Retrieve Relevant Information":     2.0,
#             "Research Topic":                    1.5,
#             "Analyze Retrieved Content":         2.2,
#             "Synthesize Findings":               2.5,
#         }

#         for step in self.steps:
#             score += step_values.get(step, 1.0)

#         # Penalty: duplicate steps
#         if len(self.steps) != len(set(self.steps)):
#             score -= 4.0

#         # Bonus: ends with a conclusive step
#         good_terminals = {
#             "Finalize Best Deal", "Provide Recommendations",
#             "Finalize Plan", "Draw Evidence-Based Conclusions", "Synthesize Findings",
#         }
#         if self.steps and self.steps[-1] in good_terminals:
#             score += 2.0

#         # Bonus: has at least one retrieval step
#         retrieval_steps = [s for s in self.steps if "Retrieve" in s or "Search" in s]
#         if retrieval_steps:
#             score += min(len(retrieval_steps) * 0.5, 1.5)

#         return score

#     def _context_relevance_score(self) -> float:
#         """
#         Bonus up to +2.0 based on keyword overlap between retrieved
#         snippets and the query + step labels.
#         """
#         q_words    = set(self.query.lower().split())
#         step_words = set(" ".join(self.steps).lower().split())
#         target     = q_words | step_words

#         total_overlap = 0
#         for snippet in self.retrieved_context:
#             total_overlap += len(target & set(snippet.lower().split()))

#         return min(total_overlap / 10.0, 2.0)


# # ──────────────────────────────────────────────────────────────────
# # R-MCTS Node
# # ──────────────────────────────────────────────────────────────────

# class RMCTSNode(MonteCarloTreeSearchNode):

#     def __init__(self, state: RMCTSState, parent=None, retriever=None):
#         super().__init__(state, parent)
#         # Share one retriever (with cache) across the whole tree
#         if retriever is not None:
#             self._retriever = retriever
#         elif parent is not None:
#             self._retriever = parent._retriever
#         else:
#             self._retriever = PerNodeRetriever()

#     def untried_actions(self) -> list:
#         tried = {child.state.steps[-1] for child in self.children if child.state.steps}
#         return [a for a in self.state.get_possible_actions() if a not in tried]

#     def expand(self) -> "RMCTSNode":
#         untried = self.untried_actions()
#         if not untried:
#             return self

#         # ── Retrieval-guided expansion ──────────────────────────────
#         # Fetch snippets for each untried action; pick the action whose
#         # retrieved content overlaps most with the query.
#         best_action   = untried[0]
#         best_snippets = []
#         best_overlap  = -1

#         for action in untried:
#             snippets = self._retriever.retrieve(self.state.query, action)
#             q_words  = set(self.state.query.lower().split())
#             overlap  = sum(
#                 len(q_words & set(s.lower().split())) for s in snippets
#             ) if snippets else 0

#             if overlap > best_overlap:
#                 best_overlap  = overlap
#                 best_action   = action
#                 best_snippets = snippets

#         next_state = self.state.move(best_action, best_snippets)
#         child = RMCTSNode(next_state, parent=self, retriever=self._retriever)
#         self.children.append(child)
#         return child

#     def is_terminal_node(self) -> bool:
#         return self.state.is_terminal()

#     def rollout(self) -> float:
#         """
#         Retrieval-guided rollout: fetch snippets per action and prefer
#         the action with the highest query overlap. Cache means no extra
#         HTTP calls for actions already seen during expansion.
#         """
#         state = self.state

#         while not state.is_terminal():
#             actions = state.get_possible_actions()
#             if not actions:
#                 break

#             best_action   = actions[0]
#             best_snippets = []
#             best_overlap  = -1

#             for action in actions:
#                 snippets = self._retriever.retrieve(state.query, action)
#                 q_words  = set(state.query.lower().split())
#                 overlap  = sum(
#                     len(q_words & set(s.lower().split())) for s in snippets
#                 ) if snippets else 0

#                 if overlap > best_overlap:
#                     best_overlap  = overlap
#                     best_action   = action
#                     best_snippets = snippets

#             state = state.move(best_action, best_snippets)

#         return state.evaluate()


# # ──────────────────────────────────────────────────────────────────
# # R-MCTS Runner
# # ──────────────────────────────────────────────────────────────────

# def run_r_mcts(query: str, simulations: int = 5) -> dict:
#     """
#     Run Retrieval MCTS planning for the given query.

#     Each node expansion performs a live retrieval step (Wikipedia API)
#     to ground action selection in freshly fetched content.

#     Returns:
#         dict with keys: variant, plan, score, simulations, time_ms,
#                         retrieved_snippets, description
#     """
#     from ..search import MonteCarloTreeSearch

#     retriever     = PerNodeRetriever()
#     initial_state = RMCTSState(query, max_depth=R_MCTS_MAX_DEPTH)
#     root          = RMCTSNode(initial_state, retriever=retriever)

#     t0        = time.perf_counter()
#     mcts      = MonteCarloTreeSearch(root)
#     best_node = mcts.best_action(simulations)
#     elapsed_ms = (time.perf_counter() - t0) * 1000

#     plan  = best_node.state.steps if best_node.state.steps else ["Direct Response"]
#     score = best_node.state.evaluate()

#     total_snippets = sum(len(v) for v in retriever._cache.values())

#     return {
#         "variant":            "R-MCTS",
#         "plan":               plan,
#         "score":              round(score, 2),
#         "simulations":        simulations,
#         "time_ms":            round(elapsed_ms, 2),
#         "retrieved_snippets": total_snippets,
#         "description": (
#             "Retrieval MCTS — live web retrieval per node during expansion; "
#             "action selection is grounded in freshly fetched content"
#         ),
#     }
####################################################################################
# backend/mcts/variants/r_mcts.py
"""R-MCTS — Retrieval MCTS. Nothing runs at module level."""

import sys
import os
import time
import re
import requests as _requests


def _setup():
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import R_MCTS_RETRIEVAL_TIMEOUT, R_MCTS_RETRIEVAL_TOP_K, R_MCTS_MAX_DEPTH
    from mcts.nodes import MonteCarloTreeSearchNode
    from mcts.search import MonteCarloTreeSearch
    return R_MCTS_RETRIEVAL_TIMEOUT, R_MCTS_RETRIEVAL_TOP_K, R_MCTS_MAX_DEPTH, \
           MonteCarloTreeSearchNode, MonteCarloTreeSearch


def run_r_mcts(query: str, simulations: int = 5) -> dict:

    TIMEOUT, TOP_K, MAX_DEPTH, MonteCarloTreeSearchNode, MonteCarloTreeSearch = _setup()
    WIKI = "https://en.wikipedia.org/w/api.php"

    # ── Per-node retriever cache ───────────────────────────────────
    cache = {}

    def retrieve(q, action):
        key = f"{q[:50]}|{action}"
        if key in cache: return cache[key]
        kws = [w for w in action.lower().split()
               if w not in {"primary","secondary","final","finalize","create",
                             "provide","gather","check","extract","draw"} and len(w) > 2]
        term = f"{q} {' '.join(kws[:3])}".strip()[:100]
        try:
            resp = _requests.get(WIKI, params={
                "action":"query","list":"search","srsearch":term,
                "format":"json","srlimit":TOP_K},
                timeout=TIMEOUT, headers={"User-Agent":"R-MCTS/1.0"})
            snips = []
            if resp.status_code == 200:
                for item in resp.json().get("query",{}).get("search",[]):
                    s = re.sub(r'<[^>]+>','',item.get("snippet","")).strip()
                    if s: snips.append(s[:400])
            cache[key] = snips
        except Exception:
            cache[key] = []
        return cache[key]

    def overlap(q, snips):
        qw = set(q.lower().split())
        return sum(len(qw & set(s.lower().split())) for s in snips)

    # ── State ─────────────────────────────────────────────────────
    class RMCTSState:
        def __init__(self, q, steps=None, ctx=None, depth=0, max_depth=MAX_DEPTH):
            self.query = q; self.steps = steps or []
            self.ctx = ctx or []; self.depth = depth; self.max_depth = max_depth

        def get_possible_actions(self):
            q = self.query.lower()
            if any(w in q for w in ["buy","purchase","compare","price","shop"]):
                pool = ["Search Product Listings","Retrieve Price Data",
                        "Compare Platform Prices","Extract Product Specifications",
                        "Retrieve Customer Reviews","Finalize Best Deal"]
            elif any(w in q for w in ["plan","book","trip","schedule"]):
                pool = ["Retrieve Destination Information","Check Availability",
                        "Compare Travel Options","Create Itinerary","Finalize Plan"]
            elif any(w in q for w in ["analyze","data","research","study"]):
                pool = ["Retrieve Background Information","Gather Statistical Data",
                        "Analyze Retrieved Data","Compare Alternatives",
                        "Draw Evidence-Based Conclusions","Provide Recommendations"]
            else:
                pool = ["Retrieve Relevant Information","Research Topic",
                        "Analyze Retrieved Content","Synthesize Findings",
                        "Provide Recommendations"]
            return [a for a in pool if a not in self.steps]

        def move(self, action, snips=None):
            return RMCTSState(self.query, self.steps+[action],
                              self.ctx+(snips or []), self.depth+1, self.max_depth)

        def is_terminal(self): return self.depth >= self.max_depth

        def evaluate(self):
            score = 4.0
            vals  = {
                "Search Product Listings":2.0,"Retrieve Price Data":2.5,
                "Compare Platform Prices":3.0,"Extract Product Specifications":2.0,
                "Retrieve Customer Reviews":1.8,"Finalize Best Deal":3.0,
                "Retrieve Destination Information":2.0,"Check Availability":1.8,
                "Compare Travel Options":2.5,"Create Itinerary":2.5,"Finalize Plan":2.5,
                "Retrieve Background Information":2.0,"Gather Statistical Data":2.0,
                "Analyze Retrieved Data":2.5,"Compare Alternatives":2.5,
                "Draw Evidence-Based Conclusions":2.8,"Provide Recommendations":2.8,
                "Retrieve Relevant Information":2.0,"Research Topic":1.5,
                "Analyze Retrieved Content":2.2,"Synthesize Findings":2.5,
            }
            for s in self.steps: score += vals.get(s, 1.0)
            if len(self.steps) != len(set(self.steps)): score -= 4.0
            good = {"Finalize Best Deal","Provide Recommendations","Finalize Plan",
                    "Draw Evidence-Based Conclusions","Synthesize Findings"}
            if self.steps and self.steps[-1] in good: score += 2.0
            rs = [s for s in self.steps if "Retrieve" in s or "Search" in s]
            if rs: score += min(len(rs)*0.5, 1.5)
            if self.ctx:
                qw = set(self.query.lower().split()) | set(" ".join(self.steps).lower().split())
                ov = sum(len(qw & set(s.lower().split())) for s in self.ctx)
                score += min(ov/10.0, 2.0)
            return min(max(score, 1.0), 10.0)

    # ── Node ──────────────────────────────────────────────────────
    class RMCTSNode(MonteCarloTreeSearchNode):
        def untried_actions(self):
            tried = {c.state.steps[-1] for c in self.children if c.state.steps}
            return [a for a in self.state.get_possible_actions() if a not in tried]

        def expand(self):
            untried = self.untried_actions()
            if not untried: return self
            best_a, best_s, best_ov = untried[0], [], -1
            for a in untried:
                snips = retrieve(self.state.query, a)
                ov    = overlap(self.state.query, snips)
                if ov > best_ov: best_ov, best_a, best_s = ov, a, snips
            child = RMCTSNode(self.state.move(best_a, best_s), parent=self)
            self.children.append(child)
            return child

        def is_terminal_node(self): return self.state.is_terminal()

        def rollout(self):
            state = self.state
            while not state.is_terminal():
                acts = state.get_possible_actions()
                if not acts: break
                best_a, best_s, best_ov = acts[0], [], -1
                for a in acts:
                    snips = retrieve(state.query, a)
                    ov    = overlap(state.query, snips)
                    if ov > best_ov: best_ov, best_a, best_s = ov, a, snips
                state = state.move(best_a, best_s)
            return state.evaluate()

    # ── Run ───────────────────────────────────────────────────────
    root      = RMCTSNode(RMCTSState(query))
    t0        = time.perf_counter()
    best_node = MonteCarloTreeSearch(root).best_action(simulations)
    elapsed   = (time.perf_counter() - t0) * 1000
    plan      = best_node.state.steps or ["Direct Response"]
    score     = best_node.state.evaluate()
    total     = sum(len(v) for v in cache.values())

    return {
        "variant": "R-MCTS", "plan": plan,
        "score": round(score, 2), "simulations": simulations,
        "time_ms": round(elapsed, 2), "retrieved_snippets": total,
        "description": "Retrieval MCTS — live web retrieval per node during expansion.",
    }