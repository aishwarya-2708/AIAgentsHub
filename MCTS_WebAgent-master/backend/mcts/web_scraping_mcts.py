# # backend/mcts/web_scraping_mcts.py
# """
# MCTS-based e-commerce scraping — decides optimal platform visit order.
# All mcts.* imports are lazy (inside functions) to avoid Windows import issues.
# """

# import sys
# import os
# import random
# import time


# def _ensure_path():
#     backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     if backend_dir not in sys.path:
#         sys.path.insert(0, backend_dir)


# _ensure_path()
# from config import WEB_REQUEST_DELAY


# # ──────────────────────────────────────────────────────────────────
# # State
# # ──────────────────────────────────────────────────────────────────
# class WebScrapingState:

#     def __init__(self, platforms, product_name, scraped_results=None, visited=None, depth=0):
#         self.platforms       = platforms
#         self.product_name    = product_name
#         self.scraped_results = scraped_results or {}
#         self.visited         = visited or []
#         self.depth           = depth
#         self.max_depth       = len(platforms)

#     def get_possible_actions(self):
#         return [p for p in self.platforms if p['name'] not in self.visited]

#     def execute_action(self, platform):
#         from tools.ecommerce import scrape_platform_real_time
#         time.sleep(WEB_REQUEST_DELAY)
#         new_results = self.scraped_results.copy()
#         try:
#             data = scrape_platform_real_time(platform, self.product_name)
#             if data and data.get('price'):
#                 new_results[platform['name']] = data
#         except Exception:
#             pass
#         return WebScrapingState(
#             self.platforms, self.product_name, new_results,
#             self.visited + [platform['name']], self.depth + 1
#         )

#     def is_terminal(self):
#         return len(self.visited) >= len(self.platforms)

#     def evaluate(self):
#         score   = len(self.scraped_results) * 5.0
#         if len(self.scraped_results) == len(self.platforms):
#             score += 10.0
#         if len(self.scraped_results) >= 2:
#             score += 5.0
#         failed  = len(self.visited) - len(self.scraped_results)
#         score  -= failed * 1.0
#         return max(score, 0.1)


# # ──────────────────────────────────────────────────────────────────
# # Node — built lazily
# # ──────────────────────────────────────────────────────────────────
# def _build_node_class():
#     from mcts.nodes import MonteCarloTreeSearchNode

#     class WebScrapingNode(MonteCarloTreeSearchNode):

#         def untried_actions(self):
#             tried     = [c.state.visited[-1] for c in self.children if c.state.visited]
#             available = self.state.get_possible_actions()
#             return [p for p in available if p['name'] not in tried]

#         def expand(self):
#             untried = self.untried_actions()
#             if not untried:
#                 return self
#             platform   = min(untried, key=lambda p: p.get('priority', 999))
#             next_state = self.state.execute_action(platform)
#             child      = WebScrapingNode(next_state, parent=self)
#             self.children.append(child)
#             return child

#         def is_terminal_node(self):
#             return self.state.is_terminal()

#         def rollout(self):
#             current = self.state
#             while not current.is_terminal():
#                 possible = current.get_possible_actions()
#                 if not possible:
#                     break
#                 action  = min(possible, key=lambda p: p.get('priority', 999))
#                 current = current.execute_action(action)
#             return current.evaluate()

#     return WebScrapingNode


# # ──────────────────────────────────────────────────────────────────
# # Runner
# # ──────────────────────────────────────────────────────────────────
# def run_mcts_scraping(platforms, product_name, simulations=5):
#     """
#     Run MCTS simulations to determine best scraping order,
#     then actually scrape all platforms in priority order.
#     """
#     from mcts.search import MonteCarloTreeSearch

#     WebScrapingNode = _build_node_class()

#     initial_state = WebScrapingState(platforms, product_name)
#     root_node     = WebScrapingNode(initial_state)
#     mcts          = MonteCarloTreeSearch(root_node)
#     mcts.best_action(simulations)

#     # Execute real scraping in priority order
#     final_results = {}
#     visited_order = []
#     sorted_platforms = sorted(platforms, key=lambda p: p.get('priority', 999))

#     from tools.ecommerce import scrape_platform_real_time

#     for platform in sorted_platforms:
#         visited_order.append(platform['name'])
#         time.sleep(WEB_REQUEST_DELAY)
#         try:
#             data = scrape_platform_real_time(platform, product_name)
#             if data and data.get('price'):
#                 final_results[platform['name']] = data
#         except Exception:
#             pass

#     return final_results, visited_order

#########################################################

# backend/mcts/web_scraping_mcts.py
"""
MCTS-based e-commerce platform order optimiser.
All imports are lazy (inside functions) — no module-level project imports.
"""

import sys
import os
import random
import time


def _setup():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import WEB_REQUEST_DELAY
    from mcts.nodes import MonteCarloTreeSearchNode
    from mcts.search import MonteCarloTreeSearch
    return WEB_REQUEST_DELAY, MonteCarloTreeSearchNode, MonteCarloTreeSearch


def run_mcts_scraping(platforms: list, product_name: str, simulations: int = 5):
    """
    Use MCTS to determine optimal platform visit order,
    then scrape all platforms in that order.
    Returns (results_dict, visited_list).
    """
    WEB_REQUEST_DELAY, MonteCarloTreeSearchNode, MonteCarloTreeSearch = _setup()

    # ── State ─────────────────────────────────────────────────────
    class WebScrapingState:
        def __init__(self, platforms, product, scraped=None, visited=None, depth=0):
            self.platforms = platforms
            self.product   = product
            self.scraped   = scraped or {}
            self.visited   = visited or []
            self.depth     = depth
            self.max_depth = len(platforms)

        def get_possible_actions(self):
            return [p for p in self.platforms if p['name'] not in self.visited]

        def execute_action(self, platform):
            from tools.ecommerce import scrape_platform_real_time
            time.sleep(WEB_REQUEST_DELAY)
            new_scraped = self.scraped.copy()
            try:
                data = scrape_platform_real_time(platform, self.product)
                if data and data.get('price'):
                    new_scraped[platform['name']] = data
            except Exception:
                pass
            return WebScrapingState(
                self.platforms, self.product, new_scraped,
                self.visited + [platform['name']], self.depth + 1)

        def is_terminal(self):
            return len(self.visited) >= len(self.platforms)

        def evaluate(self):
            score  = len(self.scraped) * 5.0
            if len(self.scraped) == len(self.platforms): score += 10.0
            if len(self.scraped) >= 2:                   score += 5.0
            score -= (len(self.visited) - len(self.scraped)) * 1.0
            return max(score, 0.1)

    # ── Node ──────────────────────────────────────────────────────
    class WebScrapingNode(MonteCarloTreeSearchNode):
        def untried_actions(self):
            tried = [c.state.visited[-1] for c in self.children if c.state.visited]
            return [p for p in self.state.get_possible_actions() if p['name'] not in tried]

        def expand(self):
            untried = self.untried_actions()
            if not untried: return self
            platform   = min(untried, key=lambda p: p.get('priority', 999))
            next_state = self.state.execute_action(platform)
            child      = WebScrapingNode(next_state, parent=self)
            self.children.append(child)
            return child

        def is_terminal_node(self):
            return self.state.is_terminal()

        def rollout(self):
            state = self.state
            while not state.is_terminal():
                possible = state.get_possible_actions()
                if not possible: break
                action = min(possible, key=lambda p: p.get('priority', 999))
                state  = state.execute_action(action)
            return state.evaluate()

    # ── Run MCTS simulations ──────────────────────────────────────
    root = WebScrapingNode(WebScrapingState(platforms, product_name))
    MonteCarloTreeSearch(root).best_action(simulations)

    # ── Execute actual scraping in priority order ─────────────────
    from tools.ecommerce import scrape_platform_real_time

    final_results = {}
    visited_order = []

    for platform in sorted(platforms, key=lambda p: p.get('priority', 999)):
        visited_order.append(platform['name'])
        time.sleep(WEB_REQUEST_DELAY)
        try:
            data = scrape_platform_real_time(platform, product_name)
            if data and data.get('price'):
                final_results[platform['name']] = data
        except Exception:
            pass

    return final_results, visited_order