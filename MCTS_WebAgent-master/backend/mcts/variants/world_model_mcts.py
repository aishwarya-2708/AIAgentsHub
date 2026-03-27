# # backend/mcts/variants/world_model_mcts.py
# """
# World-Model-Guided MCTS (WM-MCTS)
# Uses an internal world model (LLM-backed state transition predictor)
# to evaluate and guide tree expansion more accurately than pure heuristics.
# The world model predicts the likely outcome of each action sequence before
# committing real resources to it.
# """

# import time
# import random
# from ..nodes import MonteCarloTreeSearchNode
# from config import WM_MCTS_MAX_DEPTH


# # ------------------------------------------------------------------
# # World Model — LLM-backed state evaluator
# # ------------------------------------------------------------------

# class WorldModel:
#     """
#     Lightweight world model that uses the local LLM to score
#     a given plan's quality. Cached to avoid redundant LLM calls.
#     """

#     def __init__(self):
#         self._cache: dict[str, float] = {}

#     def predict_score(self, query: str, steps: list) -> float:
#         """
#         Ask the LLM to rate the plan quality (1-10).
#         Falls back to heuristic if LLM is unavailable.
#         """
#         key = f"{query[:40]}|{'->'.join(steps)}"
#         if key in self._cache:
#             return self._cache[key]

#         try:
#             from llm import get_llm
#             llm = get_llm()

#             prompt = f"""You are evaluating a task execution plan.

# Task: {query}
# Proposed steps: {' -> '.join(steps)}

# Rate this plan quality from 1 to 10 (integers only).
# Consider: logical order, completeness, efficiency.
# Reply with ONLY the integer score, nothing else."""

#             response = str(llm.invoke(prompt)).strip()

#             # Extract first number found
#             import re
#             match = re.search(r'\b([0-9]|10)\b', response)
#             score = float(match.group(1)) if match else 5.0

#         except Exception:
#             # Fallback heuristic
#             score = self._heuristic_score(query, steps)

#         score = min(max(score, 1.0), 10.0)
#         self._cache[key] = score
#         return score

#     def _heuristic_score(self, query: str, steps: list) -> float:
#         """Fallback when LLM is unavailable"""
#         score = 5.0
#         q = query.lower()

#         if any(w in q for w in ['buy', 'compare', 'price']):
#             if any('Search' in s for s in steps):
#                 score += 1.5
#             if any('Compare' in s for s in steps):
#                 score += 2.0
#             if any('Recommend' in s or 'Finalize' in s for s in steps):
#                 score += 1.5

#         if len(steps) >= 2:
#             score += 0.5
#         if len(steps) > 5:
#             score -= 1.5
#         if len(steps) != len(set(steps)):
#             score -= 3.0

#         return score


# # Shared singleton world model (shared across nodes in one planning run)
# _world_model = WorldModel()


# # ------------------------------------------------------------------
# # WM-MCTS State
# # ------------------------------------------------------------------

# class WMCTSState:

#     def __init__(self, query: str, steps=None, depth=0, max_depth=WM_MCTS_MAX_DEPTH):
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
#                 "Analyze Customer Reviews",
#                 "Finalize Recommendation",
#             ]
#         elif any(w in q for w in ['plan', 'book', 'trip', 'schedule']):
#             base = [
#                 "Research Destinations",
#                 "Check Availability",
#                 "Compare Options",
#                 "Create Itinerary",
#                 "Finalize Plan",
#             ]
#         elif any(w in q for w in ['analyze', 'data', 'research', 'study']):
#             base = [
#                 "Gather Information",
#                 "Analyze Data",
#                 "Compare Alternatives",
#                 "Draw Conclusions",
#                 "Provide Recommendations",
#             ]
#         else:
#             base = [
#                 "Research Topic",
#                 "Gather Information",
#                 "Analyze Options",
#                 "Organize Results",
#                 "Provide Recommendations",
#             ]

#         return [a for a in base if a not in self.steps]

#     def move(self, action):
#         return WMCTSState(
#             self.query,
#             self.steps + [action],
#             self.depth + 1,
#             self.max_depth,
#         )

#     def is_terminal(self):
#         return self.depth >= self.max_depth

#     def evaluate(self):
#         """World-model-guided evaluation"""
#         if not self.steps:
#             return 5.0
#         return _world_model.predict_score(self.query, self.steps)


# # ------------------------------------------------------------------
# # WM-MCTS Node
# # ------------------------------------------------------------------

# class WMCTSNode(MonteCarloTreeSearchNode):

#     def untried_actions(self):
#         tried = {child.state.steps[-1] for child in self.children if child.state.steps}
#         return [a for a in self.state.get_possible_actions() if a not in tried]

#     def expand(self):
#         untried = self.untried_actions()
#         if not untried:
#             return self

#         # World-model-guided selection: pick action that world model predicts highest score
#         best_action = untried[0]
#         best_predicted = -1.0

#         for action in untried:
#             candidate_steps = self.state.steps + [action]
#             predicted = _world_model.predict_score(self.state.query, candidate_steps)
#             if predicted > best_predicted:
#                 best_predicted = predicted
#                 best_action = action

#         child = WMCTSNode(self.state.move(best_action), parent=self)
#         self.children.append(child)
#         return child

#     def is_terminal_node(self):
#         return self.state.is_terminal()

#     def rollout(self):
#         """World-model-guided rollout: pick action with highest predicted score"""
#         state = self.state
#         while not state.is_terminal():
#             actions = state.get_possible_actions()
#             if not actions:
#                 break

#             # Score each action via world model
#             best_action = actions[0]
#             best_score = -1.0
#             for a in actions:
#                 s = _world_model.predict_score(state.query, state.steps + [a])
#                 if s > best_score:
#                     best_score = s
#                     best_action = a

#             state = state.move(best_action)

#         return state.evaluate()


# # ------------------------------------------------------------------
# # WM-MCTS Runner
# # ------------------------------------------------------------------

# def run_wm_mcts(query: str, simulations: int = 5) -> dict:
#     """
#     Run World-Model-Guided MCTS planning.

#     Returns:
#         dict with keys: plan, score, time_ms, variant
#     """
#     from ..search import MonteCarloTreeSearch

#     # Reset world model cache for fresh run
#     global _world_model
#     _world_model = WorldModel()

#     t0 = time.perf_counter()

#     initial_state = WMCTSState(query, max_depth=WM_MCTS_MAX_DEPTH)
#     root = WMCTSNode(initial_state)
#     mcts = MonteCarloTreeSearch(root)

#     best_node = mcts.best_action(simulations)

#     elapsed_ms = (time.perf_counter() - t0) * 1000

#     plan = best_node.state.steps if best_node.state.steps else ["Direct Response"]
#     score = best_node.state.evaluate()

#     return {
#         "variant": "WM-MCTS",
#         "plan": plan,
#         "score": round(score, 2),
#         "simulations": simulations,
#         "time_ms": round(elapsed_ms, 2),
#         "description": "World-Model-Guided MCTS — LLM predicts action quality before expansion",
#     }
###############################################################################

# backend/mcts/variants/world_model_mcts.py
"""WM-MCTS — World-Model-Guided MCTS. Nothing runs at module level."""

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
    from config import WM_MCTS_MAX_DEPTH
    from mcts.nodes import MonteCarloTreeSearchNode
    from mcts.search import MonteCarloTreeSearch
    return WM_MCTS_MAX_DEPTH, MonteCarloTreeSearchNode, MonteCarloTreeSearch


def run_wm_mcts(query: str, simulations: int = 5) -> dict:

    WM_MCTS_MAX_DEPTH, MonteCarloTreeSearchNode, MonteCarloTreeSearch = _setup()

    # ── World Model ───────────────────────────────────────────────
    cache = {}

    def predict_score(q, steps):
        key = f"{q[:40]}|{'->'.join(steps)}"
        if key in cache:
            return cache[key]
        try:
            from llm import get_llm
            llm    = get_llm()
            prompt = (f"Rate this task plan 1-10.\nTask: {q}\n"
                      f"Steps: {' -> '.join(steps)}\nReply ONLY with the integer.")
            resp   = str(llm.invoke(prompt)).strip()
            m      = re.search(r'\b([0-9]|10)\b', resp)
            score  = float(m.group(1)) if m else 5.0
        except Exception:
            score = _heuristic(q, steps)
        score = min(max(score, 1.0), 10.0)
        cache[key] = score
        return score

    def _heuristic(q, steps):
        s = 5.0
        if any(w in q for w in ['buy', 'compare', 'price']):
            if any('Search' in x for x in steps): s += 1.5
            if any('Compare' in x for x in steps): s += 2.0
            if any('Finalize' in x or 'Recommend' in x for x in steps): s += 1.5
        if len(steps) >= 2: s += 0.5
        if len(steps) > 5:  s -= 1.5
        if len(steps) != len(set(steps)): s -= 3.0
        return s

    # ── State ─────────────────────────────────────────────────────
    class WMCTSState:
        def __init__(self, q, steps=None, depth=0, max_depth=WM_MCTS_MAX_DEPTH):
            self.query = q; self.steps = steps or []
            self.depth = depth; self.max_depth = max_depth

        def get_possible_actions(self):
            q = self.query.lower()
            if any(w in q for w in ['buy','purchase','compare','price','shop']):
                base = ["Search Primary Platform","Search Secondary Platform",
                        "Extract Product Details","Compare Prices",
                        "Analyze Customer Reviews","Finalize Recommendation"]
            elif any(w in q for w in ['plan','book','trip','schedule']):
                base = ["Research Destinations","Check Availability",
                        "Compare Options","Create Itinerary","Finalize Plan"]
            elif any(w in q for w in ['analyze','data','research','study']):
                base = ["Gather Information","Analyze Data","Compare Alternatives",
                        "Draw Conclusions","Provide Recommendations"]
            else:
                base = ["Research Topic","Gather Information","Analyze Options",
                        "Organize Results","Provide Recommendations"]
            return [a for a in base if a not in self.steps]

        def move(self, action):
            return WMCTSState(self.query, self.steps+[action],
                              self.depth+1, self.max_depth)

        def is_terminal(self):
            return self.depth >= self.max_depth

        def evaluate(self):
            return predict_score(self.query, self.steps) if self.steps else 5.0

    # ── Node ──────────────────────────────────────────────────────
    class WMCTSNode(MonteCarloTreeSearchNode):
        def untried_actions(self):
            tried = {c.state.steps[-1] for c in self.children if c.state.steps}
            return [a for a in self.state.get_possible_actions() if a not in tried]

        def expand(self):
            untried = self.untried_actions()
            if not untried: return self
            best_a, best_s = untried[0], -1.0
            for a in untried:
                s = predict_score(self.state.query, self.state.steps+[a])
                if s > best_s: best_s, best_a = s, a
            child = WMCTSNode(self.state.move(best_a), parent=self)
            self.children.append(child)
            return child

        def is_terminal_node(self):
            return self.state.is_terminal()

        def rollout(self):
            state = self.state
            while not state.is_terminal():
                acts = state.get_possible_actions()
                if not acts: break
                best_a, best_s = acts[0], -1.0
                for a in acts:
                    s = predict_score(state.query, state.steps+[a])
                    if s > best_s: best_s, best_a = s, a
                state = state.move(best_a)
            return state.evaluate()

    # ── Run ───────────────────────────────────────────────────────
    root      = WMCTSNode(WMCTSState(query))
    t0        = time.perf_counter()
    best_node = MonteCarloTreeSearch(root).best_action(simulations)
    elapsed   = (time.perf_counter() - t0) * 1000
    plan      = best_node.state.steps or ["Direct Response"]
    score     = best_node.state.evaluate()

    return {
        "variant": "WM-MCTS", "plan": plan,
        "score": round(score, 2), "simulations": simulations,
        "time_ms": round(elapsed, 2),
        "description": "World-Model MCTS — LLM predicts action quality before expansion.",
    }