# # backend/mcts/variants/__init__.py
# """
# Lazy-loading variant registry.
# All imports happen inside functions — never at module load time.
# This avoids ModuleNotFoundError on Windows with uvicorn --reload.
# """

# import sys
# import os


# def _ensure_backend_on_path():
#     """Make sure backend/ is on sys.path so absolute imports work."""
#     # Walk up from this file: variants/ -> mcts/ -> backend/
#     backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#     if backend_dir not in sys.path:
#         sys.path.insert(0, backend_dir)


# def run_basic_mcts(query: str, simulations: int = 5) -> dict:
#     _ensure_backend_on_path()
#     from mcts.variants.basic_mcts import run_basic_mcts as _fn
#     return _fn(query, simulations)


# def run_r_mcts(query: str, simulations: int = 5) -> dict:
#     _ensure_backend_on_path()
#     from mcts.variants.r_mcts import run_r_mcts as _fn
#     return _fn(query, simulations)


# def run_wm_mcts(query: str, simulations: int = 5) -> dict:
#     _ensure_backend_on_path()
#     from mcts.variants.world_model_mcts import run_wm_mcts as _fn
#     return _fn(query, simulations)


# def run_rag_mcts(query: str, simulations: int = 5) -> dict:
#     _ensure_backend_on_path()
#     from mcts.variants.rag_mcts import run_rag_mcts as _fn
#     return _fn(query, simulations)


# VARIANT_RUNNERS = {
#     "basic-mcts": run_basic_mcts,
#     "r-mcts":     run_r_mcts,
#     "wm-mcts":    run_wm_mcts,
#     "rag-mcts":   run_rag_mcts,
# }

# __all__ = [
#     "run_basic_mcts",
#     "run_r_mcts",
#     "run_wm_mcts",
#     "run_rag_mcts",
#     "VARIANT_RUNNERS",
# ]
###########################
# backend/mcts/variants/__init__.py
"""
MCTS variant registry.
Uses importlib.util to load each variant file directly by path,
completely bypassing sys.modules package resolution issues on Windows.
"""

import sys
import os
import importlib.util


def _load_variant(filename):
    """Load a variant .py file directly by filesystem path."""
    variants_dir = os.path.dirname(os.path.abspath(__file__))
    filepath     = os.path.join(variants_dir, filename)

    # Unique module name avoids any sys.modules collision
    module_name = f"_mcts_variant_{filename[:-3]}"

    # Return cached module if already loaded successfully
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec   = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_basic_mcts(query: str, simulations: int = 5) -> dict:
    mod = _load_variant("basic_mcts.py")
    return mod.run_basic_mcts(query, simulations)


def run_r_mcts(query: str, simulations: int = 5) -> dict:
    mod = _load_variant("r_mcts.py")
    return mod.run_r_mcts(query, simulations)


def run_wm_mcts(query: str, simulations: int = 5) -> dict:
    mod = _load_variant("world_model_mcts.py")
    return mod.run_wm_mcts(query, simulations)


def run_rag_mcts(query: str, simulations: int = 5) -> dict:
    mod = _load_variant("rag_mcts.py")
    return mod.run_rag_mcts(query, simulations)


VARIANT_RUNNERS = {
    "basic-mcts": run_basic_mcts,
    "r-mcts":     run_r_mcts,
    "wm-mcts":    run_wm_mcts,
    "rag-mcts":   run_rag_mcts,
}

__all__ = ["run_basic_mcts", "run_r_mcts", "run_wm_mcts", "run_rag_mcts", "VARIANT_RUNNERS"]