# # backend/mcts/benchmark.py
# """
# MCTS Variant Analyser
# =====================
# Runs all 4 MCTS variants on the same query and returns a structured
# analysis table with the following standard metrics:

# Accuracy Formula — Task Success Rate (TSR):
#   TSR (%) = (plan_score / 10.0) * 100

#   This is the standard metric used in agentic task benchmarks
#   (AgentBench, WebArena, ALFWorld). It measures how well the
#   agent's plan achieves the goal on a normalised 0-100 scale.

# Plan Quality Score (PQS) — the raw MCTS heuristic score (0-10).

# Step Efficiency = plan_score / max(num_steps, 1)
#   Reward per planning step — higher means more efficient.

# Speed = wall-clock time in ms for the full MCTS run.

# Improvement vs Baseline = ((tsr - baseline_tsr) / baseline_tsr) * 100
#   % improvement over Basic-MCTS (the baseline variant).
# """

# import time
# from mcts.variants import VARIANT_RUNNERS


# def run_benchmark(query: str, simulations: int = 5) -> dict:
#     """
#     Run all 4 MCTS variants and return a full analysis table.

#     Returns:
#         {
#           query, simulations,
#           results: [ { variant, plan, num_steps, plan_score,
#                        tsr_accuracy, step_efficiency, time_ms,
#                        simulations, improvement_vs_baseline,
#                        rank, description }, ... ],
#           summary: { fastest, most_accurate, most_efficient,
#                      best_overall, baseline_tsr }
#         }
#     """
#     raw_results = []

#     # ── Run all 4 variants ─────────────────────────────────────────
#     for variant_key, runner in VARIANT_RUNNERS.items():
#         try:
#             result = runner(query, simulations)
#             raw_results.append(result)
#         except Exception as e:
#             raw_results.append({
#                 "variant":     variant_key.upper(),
#                 "plan":        [],
#                 "score":       0.0,
#                 "simulations": simulations,
#                 "time_ms":     0.0,
#                 "error":       str(e),
#                 "description": f"Failed: {str(e)[:80]}",
#             })

#     # ── Compute standard metrics ───────────────────────────────────
#     results = []
#     for r in raw_results:
#         plan       = r.get("plan", [])
#         num_steps  = len(plan) if plan and plan != ["Direct Response"] else 0
#         score      = r.get("score", 0.0)

#         # Task Success Rate — standard agentic benchmark metric
#         tsr = round((score / 10.0) * 100, 1)

#         # Step Efficiency — reward per planning step
#         step_eff = round(score / max(num_steps, 1), 2)

#         results.append({
#             "variant":           r.get("variant", variant_key),
#             "plan":              plan,
#             "num_steps":         num_steps,
#             "plan_score":        round(score, 2),
#             "tsr_accuracy":      tsr,           # primary accuracy metric
#             "step_efficiency":   step_eff,
#             "time_ms":           round(r.get("time_ms", 0.0), 1),
#             "simulations":       r.get("simulations", simulations),
#             "retrieved_snippets": r.get("retrieved_snippets", None),
#             "description":       r.get("description", ""),
#             "error":             r.get("error", None),
#         })

#     # ── Baseline (Basic-MCTS) metrics ─────────────────────────────
#     baseline = next((r for r in results if r["variant"] == "Basic-MCTS"), None)
#     baseline_tsr = baseline["tsr_accuracy"] if baseline else 0.0

#     for r in results:
#         if r["variant"] != "Basic-MCTS" and baseline_tsr > 0:
#             r["improvement_vs_baseline"] = round(
#                 ((r["tsr_accuracy"] - baseline_tsr) / baseline_tsr) * 100, 1
#             )
#         else:
#             r["improvement_vs_baseline"] = 0.0

#     # ── Rank by TSR accuracy (desc), then speed (asc) ─────────────
#     valid = [r for r in results if not r.get("error")]
#     valid_sorted = sorted(valid, key=lambda r: (-r["tsr_accuracy"], r["time_ms"]))
#     for i, r in enumerate(valid_sorted):
#         r["rank"] = i + 1

#     # Fill rank for errored variants
#     for r in results:
#         if "rank" not in r:
#             r["rank"] = len(results)

#     # ── Summary winners ───────────────────────────────────────────
#     fastest        = min(valid, key=lambda r: r["time_ms"])        if valid else None
#     most_accurate  = max(valid, key=lambda r: r["tsr_accuracy"])   if valid else None
#     most_efficient = max(valid, key=lambda r: r["step_efficiency"]) if valid else None
#     best_overall   = valid_sorted[0] if valid_sorted else None

#     return {
#         "query":       query,
#         "simulations": simulations,
#         "results":     results,
#         "summary": {
#             "fastest":          fastest["variant"]        if fastest        else "N/A",
#             "most_accurate":    most_accurate["variant"]  if most_accurate  else "N/A",
#             "most_efficient":   most_efficient["variant"] if most_efficient else "N/A",
#             "best_overall":     best_overall["variant"]   if best_overall   else "N/A",
#             "baseline_tsr":     baseline_tsr,
#         },
#         "metric_info": {
#             "tsr_accuracy":    "Task Success Rate = (score/10)*100 — standard AgentBench/WebArena metric",
#             "plan_score":      "Raw MCTS heuristic score (0–10)",
#             "step_efficiency": "Score per planning step (reward/steps)",
#             "time_ms":         "Wall-clock time for full MCTS run in milliseconds",
#         },
#     }
########################################################################3
# backend/mcts/benchmark.py
"""
MCTS Variant Analyser — works for ALL action types:
  chat         → benchmark planning quality on the text query
  price-compare→ benchmark scraping strategy + platform coverage
  scrape-data  → benchmark web extraction planning
  send-email   → benchmark email composition planning
  fetch-email  → benchmark email retrieval planning

Each action type has its own scoring rubric so the analysis
is meaningful regardless of what the user is doing.
"""

import sys
import os
import time


def _ensure_path():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


# ──────────────────────────────────────────────────────────────────
# Action-specific synthetic query builders
# Converts any action input into a meaningful MCTS planning query
# ──────────────────────────────────────────────────────────────────
def _make_planning_query(action_type: str, inputs: dict) -> str:
    """
    Convert any action's inputs into a descriptive planning query
    that all 4 MCTS variants can meaningfully plan on.
    """
    if action_type == "chat":
        return inputs.get("query", "general task")

    elif action_type == "price-compare":
        product = inputs.get("product", "product")
        return f"compare prices of {product} across Amazon, Flipkart, Myntra and official site"

    elif action_type == "scrape-data":
        url = inputs.get("url", "website")
        return f"scrape and extract structured data, tables and links from {url}"

    elif action_type == "send-email":
        subject = inputs.get("subject", "email")
        recipient = inputs.get("recipient", "recipient")
        return f"compose and send professional email about '{subject}' to {recipient}"

    elif action_type == "fetch-email":
        return "fetch, retrieve and summarize latest inbox emails"

    return inputs.get("query", "task")


# ──────────────────────────────────────────────────────────────────
# Action-specific performance metrics
# ──────────────────────────────────────────────────────────────────
def _action_metrics(action_type: str) -> dict:
    """Return action-specific metric labels and descriptions."""
    metrics = {
        "chat": {
            "label":       "General Query Planning",
            "description": "How well each MCTS variant plans a multi-step answer strategy",
            "step_label":  "Research steps",
            "score_label": "Answer quality score",
        },
        "price-compare": {
            "label":       "Price Comparison Strategy",
            "description": "Platform visit order optimisation and scraping strategy quality",
            "step_label":  "Platform steps",
            "score_label": "Coverage score",
        },
        "scrape-data": {
            "label":       "Web Scraping Plan",
            "description": "Content extraction strategy — depth vs breadth trade-off",
            "step_label":  "Extraction steps",
            "score_label": "Extraction quality",
        },
        "send-email": {
            "label":       "Email Composition Plan",
            "description": "How each variant structures email writing and sending workflow",
            "step_label":  "Composition steps",
            "score_label": "Composition score",
        },
        "fetch-email": {
            "label":       "Email Retrieval Plan",
            "description": "Strategy for fetching, filtering and summarising inbox emails",
            "step_label":  "Retrieval steps",
            "score_label": "Retrieval score",
        },
    }
    return metrics.get(action_type, metrics["chat"])


# ──────────────────────────────────────────────────────────────────
# Main benchmark runner
# ──────────────────────────────────────────────────────────────────
def run_benchmark(query: str, simulations: int = 5) -> dict:
    """Legacy interface — used by /mcts/benchmark endpoint (chat only)."""
    return run_benchmark_action(
        action_type="chat",
        inputs={"query": query},
        simulations=simulations,
    )


def run_benchmark_action(
    action_type: str,
    inputs: dict,
    simulations: int = 5,
) -> dict:
    """
    Run all 4 MCTS variants for any action type and return full analysis.

    Parameters:
        action_type: "chat" | "price-compare" | "scrape-data" |
                     "send-email" | "fetch-email"
        inputs:      dict with action-specific fields:
                       chat:          {"query": "..."}
                       price-compare: {"product": "...", "official_url": "..."}
                       scrape-data:   {"url": "..."}
                       send-email:    {"recipient": "...", "subject": "...", "body": "..."}
                       fetch-email:   {}
        simulations: MCTS simulation count
    """
    _ensure_path()
    from mcts.variants import VARIANT_RUNNERS

    # Build a meaningful planning query for this action
    planning_query = _make_planning_query(action_type, inputs)
    action_info    = _action_metrics(action_type)

    # ── Run all 4 variants ────────────────────────────────────────
    raw_results = []
    for variant_key, runner in VARIANT_RUNNERS.items():
        try:
            t0     = time.perf_counter()
            result = runner(planning_query, simulations)
            elapsed = (time.perf_counter() - t0) * 1000

            # Override time if variant provides its own (more accurate)
            if result.get("time_ms"):
                elapsed = result["time_ms"]

            raw_results.append({**result, "time_ms": elapsed})

        except Exception as e:
            raw_results.append({
                "variant":     variant_key.upper(),
                "plan":        [],
                "score":       0.0,
                "simulations": simulations,
                "time_ms":     0.0,
                "error":       str(e),
                "description": f"Failed: {str(e)[:80]}",
            })

    # ── Compute metrics ───────────────────────────────────────────
    results = []
    for r in raw_results:
        plan      = r.get("plan", [])
        num_steps = len(plan) if plan and plan != ["Direct Response"] else 0
        score     = float(r.get("score", 0.0))
        tsr       = round((score / 10.0) * 100, 1)
        step_eff  = round(score / max(num_steps, 1), 2)

        results.append({
            "variant":            r.get("variant", "Unknown"),
            "plan":               plan,
            "num_steps":          num_steps,
            "plan_score":         round(score, 2),
            "tsr_accuracy":       tsr,
            "step_efficiency":    step_eff,
            "time_ms":            round(r.get("time_ms", 0.0), 1),
            "simulations":        r.get("simulations", simulations),
            "retrieved_snippets": r.get("retrieved_snippets", None),
            "retrieved_chunks":   r.get("retrieved_chunks", None),
            "description":        r.get("description", ""),
            "error":              r.get("error", None),
        })

    # ── Baseline comparison ───────────────────────────────────────
    baseline     = next((r for r in results if r["variant"] == "Basic-MCTS"), None)
    baseline_tsr = baseline["tsr_accuracy"] if baseline else 0.0

    for r in results:
        if r["variant"] == "Basic-MCTS" or baseline_tsr == 0:
            r["improvement_vs_baseline"] = 0.0
        else:
            r["improvement_vs_baseline"] = round(
                ((r["tsr_accuracy"] - baseline_tsr) / baseline_tsr) * 100, 1
            )

    # ── Rank by TSR desc, then speed asc ─────────────────────────
    valid        = [r for r in results if not r.get("error")]
    valid_sorted = sorted(valid, key=lambda r: (-r["tsr_accuracy"], r["time_ms"]))
    for i, r in enumerate(valid_sorted):
        r["rank"] = i + 1
    for r in results:
        if "rank" not in r:
            r["rank"] = len(results)

    fastest        = min(valid, key=lambda r: r["time_ms"])         if valid else None
    most_accurate  = max(valid, key=lambda r: r["tsr_accuracy"])    if valid else None
    most_efficient = max(valid, key=lambda r: r["step_efficiency"])  if valid else None
    best_overall   = valid_sorted[0]                                  if valid_sorted else None

    return {
        "action_type":    action_type,
        "action_label":   action_info["label"],
        "action_desc":    action_info["description"],
        "planning_query": planning_query,
        "inputs":         inputs,
        "simulations":    simulations,
        "results":        results,
        "summary": {
            "fastest":        fastest["variant"]        if fastest        else "N/A",
            "most_accurate":  most_accurate["variant"]  if most_accurate  else "N/A",
            "most_efficient": most_efficient["variant"] if most_efficient else "N/A",
            "best_overall":   best_overall["variant"]   if best_overall   else "N/A",
            "baseline_tsr":   baseline_tsr,
        },
        "metric_info": {
            "tsr_accuracy":    "Task Success Rate = (score/10)×100 — AgentBench/WebArena standard",
            "plan_score":      f"Raw MCTS heuristic score (0–10) for {action_info['score_label']}",
            "step_efficiency": f"Score per {action_info['step_label']}",
            "time_ms":         "Wall-clock planning time in milliseconds",
        },
    }