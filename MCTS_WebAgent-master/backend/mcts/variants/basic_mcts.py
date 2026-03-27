# backend/mcts/variants/basic_mcts.py
"""
Basic MCTS — standard textbook UCB1 + random rollout. Baseline variant.
No retrieval, no LLM, no external calls.
"""

import sys
import os
import time
import random


# ──────────────────────────────────────────────────────────────────
# NOTHING runs at module level except stdlib imports above.
# All project imports happen inside run_basic_mcts() at call time.
# ──────────────────────────────────────────────────────────────────

def _setup():
    """Add backend/ to sys.path and return config values."""
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import MAX_MCTS_DEPTH
    from mcts.nodes import MonteCarloTreeSearchNode
    from mcts.search import MonteCarloTreeSearch
    return MAX_MCTS_DEPTH, MonteCarloTreeSearchNode, MonteCarloTreeSearch


# ──────────────────────────────────────────────────────────────────
# Runner — all logic lives here, built fresh on each call
# ──────────────────────────────────────────────────────────────────

def run_basic_mcts(query: str, simulations: int = 5) -> dict:

    MAX_MCTS_DEPTH, MonteCarloTreeSearchNode, MonteCarloTreeSearch = _setup()

    # ── State ─────────────────────────────────────────────────────
    class BasicMCTSState:

        def __init__(self, query, steps=None, depth=0, max_depth=MAX_MCTS_DEPTH):
            self.query     = query
            self.steps     = steps or []
            self.depth     = depth
            self.max_depth = max_depth

        def get_possible_actions(self):
            q = self.query.lower()
            if any(w in q for w in ["buy", "purchase", "compare", "price", "shop"]):
                pool = ["Search Primary Platform", "Search Secondary Platform",
                        "Extract Product Details", "Compare Prices",
                        "Analyze Customer Reviews", "Finalize Recommendation"]
            elif any(w in q for w in ["plan", "book", "trip", "schedule", "itinerary"]):
                pool = ["Research Destinations", "Check Availability",
                        "Compare Options", "Create Itinerary", "Finalize Plan"]
            elif any(w in q for w in ["analyze", "data", "research", "study", "compare"]):
                pool = ["Gather Information", "Analyze Data", "Compare Alternatives",
                        "Draw Conclusions", "Provide Recommendations"]
            else:
                pool = ["Research Topic", "Gather Information", "Analyze Options",
                        "Organize Results", "Provide Recommendations"]
            return [a for a in pool if a not in self.steps]

        def move(self, action):
            return BasicMCTSState(self.query, self.steps + [action],
                                  self.depth + 1, self.max_depth)

        def is_terminal(self):
            return self.depth >= self.max_depth

        def evaluate(self):
            score = 4.0
            step_values = {
                "Search Primary Platform": 2.0, "Search Secondary Platform": 1.8,
                "Extract Product Details": 2.0, "Compare Prices": 2.5,
                "Analyze Customer Reviews": 1.8, "Finalize Recommendation": 2.5,
                "Research Destinations": 1.8, "Check Availability": 1.5,
                "Compare Options": 2.0, "Create Itinerary": 2.0, "Finalize Plan": 2.0,
                "Gather Information": 1.5, "Analyze Data": 2.0,
                "Compare Alternatives": 2.0, "Draw Conclusions": 2.2,
                "Provide Recommendations": 2.2, "Research Topic": 1.5,
                "Analyze Options": 1.8, "Organize Results": 1.5,
            }
            for step in self.steps:
                score += step_values.get(step, 1.0)
            if len(self.steps) != len(set(self.steps)):
                score -= 4.0
            good = {"Finalize Recommendation", "Provide Recommendations",
                    "Finalize Plan", "Draw Conclusions"}
            if self.steps and self.steps[-1] in good:
                score += 2.0
            if len(self.steps) >= 3:
                score += 1.0
            return min(max(score, 1.0), 10.0)

    # ── Node ──────────────────────────────────────────────────────
    class BasicMCTSNode(MonteCarloTreeSearchNode):

        def untried_actions(self):
            tried = {c.state.steps[-1] for c in self.children if c.state.steps}
            return [a for a in self.state.get_possible_actions() if a not in tried]

        def expand(self):
            untried = self.untried_actions()
            if not untried:
                return self
            child = BasicMCTSNode(
                self.state.move(random.choice(untried)), parent=self
            )
            self.children.append(child)
            return child

        def is_terminal_node(self):
            return self.state.is_terminal()

        def rollout(self):
            state = self.state
            while not state.is_terminal():
                actions = state.get_possible_actions()
                if not actions:
                    break
                state = state.move(random.choice(actions))
            return state.evaluate()

    # ── Run MCTS ──────────────────────────────────────────────────
    root      = BasicMCTSNode(BasicMCTSState(query))
    t0        = time.perf_counter()
    mcts      = MonteCarloTreeSearch(root)
    best_node = mcts.best_action(simulations)
    elapsed   = (time.perf_counter() - t0) * 1000

    plan  = best_node.state.steps if best_node.state.steps else ["Direct Response"]
    score = best_node.state.evaluate()

    return {
        "variant":     "Basic-MCTS",
        "plan":        plan,
        "score":       round(score, 2),
        "simulations": simulations,
        "time_ms":     round(elapsed, 2),
        "description": "Standard MCTS — UCB1 selection, random rollout, heuristic evaluation.",
    }
# ##################################################################################
# # backend/mcts/variants/basic_mcts.py
# """
# Basic MCTS (Standard Monte Carlo Tree Search)
# =============================================
# Pure textbook MCTS implementation with 4 phases:
#   1. Selection   — traverse tree using UCB1 to pick most promising node
#   2. Expansion   — add one new child node for an untried action
#   3. Simulation  — random rollout to terminal state (no heuristics, no LLM)
#   4. Backprop    — propagate reward back up to root

# No retrieval, no LLM scoring, no world model, no RAG.
# Evaluation is purely heuristic — step count and basic keyword matching.
# This serves as the baseline to compare all other variants against.
# """

# import time
# import random
# from mcts.nodes import MonteCarloTreeSearchNode
# from config import MAX_MCTS_DEPTH


# # ──────────────────────────────────────────────────────────────────
# # Basic MCTS State
# # ──────────────────────────────────────────────────────────────────

# class BasicMCTSState:
#     """
#     Standard planning state.
#     Action space is keyword-driven but evaluation is pure heuristic
#     with NO external calls — making this the fastest and simplest variant.
#     """

#     def __init__(self, query: str, steps=None, depth=0, max_depth=MAX_MCTS_DEPTH):
#         self.query     = query
#         self.steps     = steps or []
#         self.depth     = depth
#         self.max_depth = max_depth

#     # ── Action space ──────────────────────────────────────────────

#     def get_possible_actions(self) -> list:
#         q = self.query.lower()

#         if any(w in q for w in ["buy", "purchase", "compare", "price", "shop"]):
#             pool = [
#                 "Search Primary Platform",
#                 "Search Secondary Platform",
#                 "Extract Product Details",
#                 "Compare Prices",
#                 "Analyze Customer Reviews",
#                 "Finalize Recommendation",
#             ]
#         elif any(w in q for w in ["plan", "book", "trip", "schedule", "itinerary"]):
#             pool = [
#                 "Research Destinations",
#                 "Check Availability",
#                 "Compare Options",
#                 "Create Itinerary",
#                 "Finalize Plan",
#             ]
#         elif any(w in q for w in ["analyze", "data", "research", "study", "compare"]):
#             pool = [
#                 "Gather Information",
#                 "Analyze Data",
#                 "Compare Alternatives",
#                 "Draw Conclusions",
#                 "Provide Recommendations",
#             ]
#         else:
#             pool = [
#                 "Research Topic",
#                 "Gather Information",
#                 "Analyze Options",
#                 "Organize Results",
#                 "Provide Recommendations",
#             ]

#         return [a for a in pool if a not in self.steps]

#     # ── Transition ─────────────────────────────────────────────────

#     def move(self, action: str) -> "BasicMCTSState":
#         return BasicMCTSState(
#             self.query,
#             self.steps + [action],
#             self.depth + 1,
#             self.max_depth,
#         )

#     def is_terminal(self) -> bool:
#         return self.depth >= self.max_depth

#     # ── Evaluation — pure heuristic, zero external calls ──────────

#     def evaluate(self) -> float:
#         """
#         Standard heuristic scoring:
#         - Base score
#         - Per-step value lookup
#         - Bonus for good terminal step
#         - Penalty for duplicate steps
#         No LLM, no retrieval, no web calls.
#         """
#         score = 4.0

#         step_values = {
#             # E-commerce
#             "Search Primary Platform":    2.0,
#             "Search Secondary Platform":  1.8,
#             "Extract Product Details":    2.0,
#             "Compare Prices":             2.5,
#             "Analyze Customer Reviews":   1.8,
#             "Finalize Recommendation":    2.5,
#             # Planning
#             "Research Destinations":      1.8,
#             "Check Availability":         1.5,
#             "Compare Options":            2.0,
#             "Create Itinerary":           2.0,
#             "Finalize Plan":              2.0,
#             # Research / Analysis
#             "Gather Information":         1.5,
#             "Analyze Data":               2.0,
#             "Compare Alternatives":       2.0,
#             "Draw Conclusions":           2.2,
#             "Provide Recommendations":    2.2,
#             # General
#             "Research Topic":             1.5,
#             "Analyze Options":            1.8,
#             "Organize Results":           1.5,
#         }

#         for step in self.steps:
#             score += step_values.get(step, 1.0)

#         # Penalty: duplicate steps
#         if len(self.steps) != len(set(self.steps)):
#             score -= 4.0

#         # Bonus: good terminal step
#         good_terminals = {
#             "Finalize Recommendation", "Provide Recommendations",
#             "Finalize Plan", "Draw Conclusions",
#         }
#         if self.steps and self.steps[-1] in good_terminals:
#             score += 2.0

#         # Bonus: sufficient depth (complete plan)
#         if len(self.steps) >= 3:
#             score += 1.0

#         return min(max(score, 1.0), 10.0)


# # ──────────────────────────────────────────────────────────────────
# # Basic MCTS Node
# # ──────────────────────────────────────────────────────────────────

# class BasicMCTSNode(MonteCarloTreeSearchNode):
#     """
#     Standard MCTS node.
#     Expansion: picks a random untried action (no guidance).
#     Rollout:   fully random simulation to terminal state.
#     """

#     def untried_actions(self) -> list:
#         tried = {child.state.steps[-1] for child in self.children if child.state.steps}
#         return [a for a in self.state.get_possible_actions() if a not in tried]

#     def expand(self) -> "BasicMCTSNode":
#         untried = self.untried_actions()
#         if not untried:
#             return self
#         # ── Pure random expansion — no guidance whatsoever ──
#         action = random.choice(untried)
#         child  = BasicMCTSNode(self.state.move(action), parent=self)
#         self.children.append(child)
#         return child

#     def is_terminal_node(self) -> bool:
#         return self.state.is_terminal()

#     def rollout(self) -> float:
#         """
#         Pure random rollout — standard MCTS simulation phase.
#         No heuristics, no retrieval, no LLM. Fully random.
#         """
#         state = self.state
#         while not state.is_terminal():
#             actions = state.get_possible_actions()
#             if not actions:
#                 break
#             state = state.move(random.choice(actions))  # completely random
#         return state.evaluate()


# # ──────────────────────────────────────────────────────────────────
# # Basic MCTS Runner
# # ──────────────────────────────────────────────────────────────────

# def run_basic_mcts(query: str, simulations: int = 5) -> dict:
#     """
#     Run standard MCTS planning for the given query.

#     Phases per simulation:
#       Selection   → UCB1 tree traversal (from nodes.py best_child)
#       Expansion   → random untried action
#       Simulation  → random rollout
#       Backprop    → reward propagated to root

#     Returns:
#         dict with keys: variant, plan, score, simulations, time_ms, description
#     """
#     from mcts.search import MonteCarloTreeSearch

#     initial_state = BasicMCTSState(query, max_depth=MAX_MCTS_DEPTH)
#     root          = BasicMCTSNode(initial_state)

#     t0        = time.perf_counter()
#     mcts      = MonteCarloTreeSearch(root)
#     best_node = mcts.best_action(simulations)
#     elapsed_ms = (time.perf_counter() - t0) * 1000

#     plan  = best_node.state.steps if best_node.state.steps else ["Direct Response"]
#     score = best_node.state.evaluate()

#     return {
#         "variant":     "Basic-MCTS",
#         "plan":        plan,
#         "score":       round(score, 2),
#         "simulations": simulations,
#         "time_ms":     round(elapsed_ms, 2),
#         "description": (
#             "Standard MCTS — UCB1 selection, random expansion, "
#             "random rollout, heuristic evaluation. No retrieval or LLM."
#         ),
#     }