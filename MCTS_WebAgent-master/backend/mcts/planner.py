# #backend/mcts/planner.py
# import random
# import time
# from config import MAX_MCTS_DEPTH, LLM_RATE_LIMIT_DELAY
# from mcts.nodes import MonteCarloTreeSearchNode

# # Rate limiting for operations
# _last_operation = 0

# def rate_limited_delay():
#     """Apply rate limiting delay between operations"""
#     global _last_operation
    
#     elapsed = time.time() - _last_operation
#     if elapsed < LLM_RATE_LIMIT_DELAY:
#         time.sleep(LLM_RATE_LIMIT_DELAY - elapsed)
    
#     _last_operation = time.time()

# class PlanningState:

#     def __init__(self, query, steps=None, depth=0, max_depth=3):
#         self.query = query
#         self.steps = steps or []
#         self.depth = depth
#         self.max_depth = max_depth

#     def get_possible_actions(self):
#         """Dynamic action selection based on query type and current context"""
#         query_lower = self.query.lower()
        
#         # E-commerce specific actions with more granular steps
#         if any(word in query_lower for word in ['buy', 'purchase', 'shop', 'compare', 'product', 'price']):
#             base_actions = ["Search Primary Platform", "Search Secondary Platform", "Extract Product Details", "Compare Prices"]
            
#             # Add context-aware actions based on current steps
#             if not self.steps:
#                 return ["Search Primary Platform", "Identify Product Category", "Plan Search Strategy"]
#             elif "Search Primary Platform" in self.steps:
#                 return ["Search Secondary Platform", "Extract Product Details", "Verify Product Match"]
#             elif len([s for s in self.steps if "Search" in s]) >= 2:
#                 return ["Extract Product Details", "Compare Prices", "Analyze Reviews", "Finalize Recommendation"]
#             else:
#                 return ["Compare Prices", "Analyze Customer Reviews", "Check Availability", "Finalize Recommendation"]
        
#         # Planning/booking specific actions
#         elif any(word in query_lower for word in ['plan', 'book', 'schedule', 'trip', 'itinerary']):
#             return ["Research Destinations", "Check Availability", "Compare Options", "Create Itinerary", "Finalize Plan"]
        
#         # Data/analysis specific actions
#         elif any(word in query_lower for word in ['analyze', 'data', 'research', 'study', 'compare']):
#             return ["Gather Information", "Analyze Data", "Compare Alternatives", "Draw Conclusions", "Provide Recommendations"]
        
#         # General actions for complex tasks
#         return ["Research Topic", "Gather Information", "Analyze Options", "Organize Results", "Provide Recommendations"]

#     def move(self, action):
#         """Create new state with action"""
#         # Apply rate limiting
#         rate_limited_delay()
        
#         return PlanningState(
#             self.query,
#             self.steps + [action],
#             self.depth + 1,
#             self.max_depth
#         )

#     def is_terminal(self):
#         """Check if planning should stop"""
#         return self.depth >= self.max_depth

#     def evaluate_with_llm(self):
#         """Evaluate plan quality using enhanced heuristics"""
#         score = 5.0  # Base score
#         query_lower = self.query.lower()
        
#         # Enhanced scoring for e-commerce queries
#         if any(word in query_lower for word in ['buy', 'purchase', 'shop', 'compare']):
#             for action in self.steps:
#                 if action in ["Search Primary Platform", "Search Secondary Platform"]:
#                     score += 2.0  # High value for platform searches
#                 elif action in ["Extract Product Details", "Compare Prices"]:
#                     score += 2.5  # Very high value for price comparison
#                 elif action in ["Analyze Reviews", "Analyze Customer Reviews"]:
#                     score += 1.5  # Good value for review analysis
#                 elif action in ["Finalize Recommendation"]:
#                     score += 2.0  # High value for final recommendation
            
#             # Bonus for logical e-commerce flow
#             if len(self.steps) >= 2:
#                 if "Search" in self.steps[0] and ("Compare" in str(self.steps) or "Extract" in str(self.steps)):
#                     score += 2.0
            
#             # Bonus for comprehensive comparison (multiple platforms)
#             search_actions = [s for s in self.steps if "Search" in s]
#             if len(search_actions) >= 2:
#                 score += 3.0  # Bonus for multi-platform search
        
#         # Enhanced scoring for planning queries
#         elif any(word in query_lower for word in ['plan', 'trip', 'schedule']):
#             for action in self.steps:
#                 if action in ["Research Destinations", "Research Options"]:
#                     score += 1.8
#                 elif action in ["Compare Options", "Create Itinerary"]:
#                     score += 2.0
#                 elif action in ["Check Availability", "Finalize Plan"]:
#                     score += 1.5
        
#         # General scoring
#         else:
#             for action in self.steps:
#                 if action in ["Research Topic", "Gather Information"]:
#                     score += 1.5
#                 elif action in ["Analyze Options", "Compare Alternatives"]:
#                     score += 1.8
#                 elif action in ["Provide Recommendations"]:
#                     score += 2.0
        
#         # Penalty for redundant steps
#         if len(self.steps) != len(set(self.steps)):
#             score -= 3.0
        
#         # Penalty for too many steps
#         if len(self.steps) > 5:
#             score -= 1.5
        
#         # Bonus for logical flow patterns
#         if self.steps:
#             # Good starting actions
#             if self.steps[0] in ["Search Primary Platform", "Research Topic", "Identify Product Category"]:
#                 score += 1.5
            
#             # Good ending actions
#             if self.steps[-1] in ["Finalize Recommendation", "Provide Recommendations", "Finalize Plan"]:
#                 score += 2.5
            
#             # Good middle actions for e-commerce
#             if len(self.steps) >= 3 and any("Compare" in step for step in self.steps[1:-1]):
#                 score += 1.5
        
#         # Ensure score is in valid range
#         return min(max(score, 1.0), 10.0)


# class PlanningNode(MonteCarloTreeSearchNode):

#     def untried_actions(self):
#         """Get actions not yet tried"""
#         tried = [child.state.steps[-1] for child in self.children if child.state.steps]
#         available_actions = self.state.get_possible_actions()
#         return [a for a in available_actions if a not in tried]

#     def expand(self):
#         """Expand node with new action"""
#         untried = self.untried_actions()
#         if not untried:
#             return self
        
#         # For e-commerce, prioritize search actions early
#         if any(word in self.state.query.lower() for word in ['buy', 'compare', 'price']):
#             search_actions = [a for a in untried if "Search" in a]
#             if search_actions and self.state.depth < 2:
#                 action = random.choice(search_actions)
#             else:
#                 action = random.choice(untried)
#         else:
#             action = random.choice(untried)
        
#         next_state = self.state.move(action)
#         child = PlanningNode(next_state, parent=self)
#         self.children.append(child)
#         return child

#     def is_terminal_node(self):
#         """Check if node is terminal"""
#         return self.state.is_terminal()

#     def rollout(self):
#         """Simulate to terminal state and evaluate"""
#         current_state = self.state

#         while not current_state.is_terminal():
#             possible_actions = current_state.get_possible_actions()
            
#             # Smart action selection during rollout
#             if any(word in current_state.query.lower() for word in ['buy', 'compare', 'price']):
#                 # For e-commerce, prefer search and compare actions
#                 preferred_actions = [a for a in possible_actions if any(word in a for word in ['Search', 'Compare', 'Extract', 'Analyze'])]
#                 if preferred_actions:
#                     action = random.choice(preferred_actions)
#                 else:
#                     action = random.choice(possible_actions)
#             else:
#                 action = random.choice(possible_actions)
            
#             current_state = current_state.move(action)

#         return current_state.evaluate_with_llm()
###############################################################################################3

# backend/mcts/planner.py
"""
MCTS Planner — Central task planning engine.

MCTS is genuinely used to DRIVE execution, not just decorate output:

  plan_research()        → R-MCTS plan → each step fetches a real source
  plan_lead_generation() → MCTS picks URL visit order by priority score
  plan_summarize()       → MCTS-RAG seeds context → shapes extraction
  plan_job_search()      → R-MCTS retrieves live job snippets per node
  plan_monitor()         → MCTS decides what indicators to check first
  plan_schedule()        → WM-MCTS scores each booking option
  plan_qa_test()         → MCTS orders tests by impact (security first if low score)
  plan_general()         → any variant for free-form planning + LLM

All imports lazy — Windows uvicorn --reload safe.
"""

import sys
import os
import re
import time
import random
import requests
from bs4 import BeautifulSoup


def _ensure_path():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) "
    "Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


def _session(ref="https://www.google.co.in/"):
    s = requests.Session()
    s.headers.update({
        "User-Agent":      random.choice(_UA),
        "Accept-Language": "en-IN,en;q=0.9",
        "Accept":          "text/html,application/xhtml+xml,*/*;q=0.8",
        "Referer":         ref,
        "DNT":             "1",
        "Connection":      "keep-alive",
    })
    return s


# ──────────────────────────────────────────────────────────────────
# Core MCTS runner
# ──────────────────────────────────────────────────────────────────
def _run_mcts(query: str, variant_key: str = "basic-mcts",
              simulations: int = 4) -> dict:
    _ensure_path()
    from mcts.variants import VARIANT_RUNNERS
    key    = variant_key if variant_key in VARIANT_RUNNERS else "basic-mcts"
    return VARIANT_RUNNERS[key](query, simulations=simulations)


# ──────────────────────────────────────────────────────────────────
# Shared web helpers
# ──────────────────────────────────────────────────────────────────
def _fetch_page(url: str, timeout: int = 10) -> dict:
    """Fetch a URL and return structured content."""
    try:
        s = _session()
        r = s.get(url, timeout=timeout)
        if r.status_code != 200:
            return None
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer']):
            tag.decompose()
        text     = soup.get_text(separator=' ', strip=True)
        title    = (soup.find('h1') or soup.find('title'))
        headings = [h.get_text(strip=True) for h in soup.find_all(['h2','h3'])[:6]]
        paras    = [p.get_text(strip=True) for p in soup.find_all('p')
                    if len(p.get_text()) > 60][:5]
        emails   = list(set(re.findall(
            r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b', text)))[:5]
        phones   = list(set(re.findall(r'(?:\+91[\s\-]?)?[6-9]\d{9}', text)))[:3]
        prices   = list(set(re.findall(r'₹\s*[\d,]+', text)))[:5]
        return {
            "url":      url,
            "title":    title.get_text(strip=True)[:100] if title else url,
            "headings": headings,
            "paras":    paras,
            "emails":   emails,
            "phones":   phones,
            "prices":   prices,
            "text":     text[:3000],
            "status":   r.status_code,
            "load_ms":  0,
            "size_kb":  len(r.content) / 1024,
            "headers":  dict(r.headers),
        }
    except Exception as e:
        return {"url": url, "error": str(e)[:80]}


def _bing_search(query: str, n: int = 5) -> list:
    """Search Bing and return list of (title, url, snippet) tuples."""
    try:
        q   = query.replace(' ', '+')
        url = f"https://www.bing.com/search?q={q}&mkt=en-IN"
        s   = _session("https://www.bing.com/")
        r   = s.get(url, timeout=8)
        if r.status_code != 200:
            return []
        soup    = BeautifulSoup(r.text, 'html.parser')
        results = []
        for item in soup.select('li.b_algo')[:n]:
            title_el   = item.select_one('h2 a')
            snippet_el = item.select_one('p, .b_caption p')
            if title_el:
                results.append({
                    "title":   title_el.get_text(strip=True)[:100],
                    "url":     title_el.get('href', ''),
                    "snippet": snippet_el.get_text(strip=True)[:200] if snippet_el else '',
                })
        return results
    except Exception:
        return []


# ──────────────────────────────────────────────────────────────────
# Auto variant selector
# Picks the best MCTS variant based on query characteristics
# ──────────────────────────────────────────────────────────────────
def _select_best_variant(query: str) -> tuple:
    """
    Returns (variant_key, reason) — picks the most suitable MCTS variant.

    Decision logic:
      R-MCTS    → queries needing live web data (research, jobs, news)
      MCTS-RAG  → queries needing background context (summaries, explanations)
      WM-MCTS   → queries needing multi-step planning (strategy, planning)
      Basic-MCTS→ queries needing fast direct answers (facts, simple plans)
    """
    q = query.lower()

    # R-MCTS: live retrieval per node — best for queries needing current data
    r_mcts_signals = [
        'latest','recent','current','now','today','2024','2025',
        'competitor','market','industry','news','trend','update',
        'find','search','discover','compare','research','analyze',
        'who is','what does','how does','which company',
    ]
    r_mcts_score = sum(1 for s in r_mcts_signals if s in q)

    # MCTS-RAG: seeds context first — best for synthesis & explanation
    rag_signals = [
        'explain','understand','concept','theory','how to','guide',
        'tutorial','learn','difference between','what is','overview',
        'summarize','summary','key points','background','history',
        'introduction','basics','fundamentals',
    ]
    rag_score = sum(1 for s in rag_signals if s in q)

    # WM-MCTS: world-model scoring — best for planning & strategy
    wm_signals = [
        'plan','strategy','roadmap','steps','process','workflow',
        'how should','best approach','recommend','optimize','improve',
        'implement','build','create','design','develop','launch',
        'marketing','business','startup','project','campaign',
    ]
    wm_score = sum(1 for s in wm_signals if s in q)

    # Basic-MCTS: fast heuristic — best for direct factual answers
    basic_score = 1  # default fallback

    scores = {
        'r-mcts':    (r_mcts_score,  'Live web retrieval per node'),
        'rag-mcts':  (rag_score,     'Wikipedia context seeded before planning'),
        'wm-mcts':   (wm_score,      'World-model scores each step'),
        'basic-mcts':(basic_score,   'Fast UCB1 heuristic planning'),
    }

    best_key    = max(scores, key=lambda k: scores[k][0])
    best_reason = scores[best_key][1]

    # Break ties in favour of speed for short queries
    if len(query.split()) < 6:
        return 'basic-mcts', 'Short query — fast heuristic planning'

    return best_key, best_reason


def _variant_summary_line(variant_key: str, score: float,
                           time_ms: float, snippets: int = 0) -> str:
    """One-line summary showing what the variant contributed."""
    labels = {
        'Basic-MCTS': 'UCB1 heuristic | no retrieval',
        'R-MCTS':     f'live retrieval | {snippets} snippets fetched',
        'WM-MCTS':    'world-model scored each step',
        'MCTS-RAG':   f'Wikipedia context seeded | {snippets} chunks',
    }
    label = labels.get(variant_key, '')
    return (f"⚡ {variant_key} | Score: {score:.1f}/10 | "
            f"Time: {time_ms:.0f}ms | {label}")


# ══════════════════════════════════════════════════════════════════
# 1. COMPETITIVE RESEARCH
#
# HOW MCTS IMPROVES IT:
#   R-MCTS retrieves live Wikipedia/web snippets for EACH node during
#   tree search. The plan steps that win have the most relevant
#   retrieved content — so the plan is shaped by actual web data.
#   Each plan step maps to a REAL action: we search Bing for that step
#   and include the results in the LLM prompt.
# ══════════════════════════════════════════════════════════════════
def plan_research(query: str, simulations: int = 4) -> str:
    _ensure_path()
    from llm import get_llm

    # R-MCTS builds plan with live retrieval per node
    mcts  = _run_mcts(
        f"competitive intelligence research analysis: {query}",
        variant_key="r-mcts", simulations=simulations
    )
    plan  = mcts.get("plan", [])
    score = mcts.get("score", 0)

    out  = f"📊 Competitive Intelligence Report\n{'='*60}\n"
    out += f"🎯 Topic   : {query}\n"
    out += f"⚡ Variant : {mcts.get('variant','')} | "
    out += f"Score: {score:.1f}/10 | Time: {mcts.get('time_ms',0):.0f}ms\n"
    out += f"📡 Snippets retrieved during planning: {mcts.get('retrieved_snippets',0)}\n\n"
    out += f"🌳 R-MCTS Research Plan (shaped by live retrieval):\n"
    for i, step in enumerate(plan, 1):
        out += f"   {i}. {step}\n"
    out += "\n"

    # MCTS plan drives actual search: search Bing for each step
    live_findings = {}
    out += "🔍 Executing plan — live web search per step...\n"
    for step in plan[:4]:
        search_q = f"{query} {step}"
        results  = _bing_search(search_q, n=2)
        if results:
            live_findings[step] = results
            out += f"   ✅ {step}: {len(results)} source(s) found\n"
        else:
            out += f"   ⚠️  {step}: no results\n"
    out += "\n"

    # Build context from live findings
    context_parts = []
    for step, results in live_findings.items():
        for r in results:
            context_parts.append(
                f"[{step}] {r['title']}: {r['snippet']}"
            )
    context = "\n".join(context_parts[:8]) or "No live data retrieved."

    llm    = get_llm()
    report = llm.invoke(f"""You are a competitive intelligence analyst for Indian markets.

Research Task: {query}

MCTS R-MCTS Research Plan (steps shaped by live web retrieval):
{chr(10).join(f'{i+1}. {s}' for i,s in enumerate(plan))}

Live Web Evidence (retrieved during MCTS planning):
{context}

Based on the above plan and live evidence, generate a structured report:
1. Key Players & Market Position in India
2. Product / Service Comparison (with specifics)
3. Pricing Strategies (use ₹ INR)
4. Recent Developments (2024-2025)
5. SWOT: Opportunities & Threats
6. Recommended Strategic Actions

Be specific, factual, and practical. Use the live evidence where relevant.""")

    out += "📋 Intelligence Report:\n" + "-"*60 + "\n"
    out += str(report) + "\n"
    out += f"\n{'='*60}\n"
    sources_used = sum(len(v) for v in live_findings.values())
    out += _variant_summary_line(
        mcts.get('variant','R-MCTS'), score,
        mcts.get('time_ms',0), sources_used
    ) + "\n"
    out += ("💡 Why R-MCTS? — retrieves live web snippets per tree node so the plan "
            "is shaped by actual current web data, not just heuristics.\n")
    return out


# ══════════════════════════════════════════════════════════════════
# 2. LEAD GENERATION
#
# HOW MCTS IMPROVES IT:
#   Basic-MCTS plans which URLs to visit and in what order.
#   The plan steps map to real extraction actions (emails first,
#   then phones, then company details). MCTS score reflects how
#   many high-value steps were completed.
# ══════════════════════════════════════════════════════════════════
def plan_lead_generation(query: str, urls: list = None,
                         simulations: int = 4) -> str:
    _ensure_path()
    from llm import get_llm

    mcts = _run_mcts(
        f"extract contact lead information company details: {query}",
        variant_key="basic-mcts", simulations=simulations
    )
    plan  = mcts.get("plan", [])

    out  = f"👥 Lead Generation\n{'='*60}\n"
    out += f"🎯 Query   : {query}\n"
    out += f"⚡ Variant : {mcts.get('variant','')} | Score: {mcts.get('score',0):.1f}/10\n\n"
    out += f"🌳 MCTS Extraction Plan:\n"
    for i, step in enumerate(plan, 1):
        out += f"   {i}. {step}\n"
    out += "\n"

    # Map MCTS plan steps to actual extraction actions
    STEP_ACTIONS = {
        "Search Primary Platform":   ["emails", "phones"],
        "Search Secondary Platform": ["emails", "phones"],
        "Extract Product Details":   ["company", "summary"],
        "Gather Information":        ["emails", "summary"],
        "Analyze Data":              ["phones", "company"],
        "Provide Recommendations":   ["emails", "phones", "company"],
    }

    # Determine what to extract based on MCTS plan
    extract_types = set()
    for step in plan:
        for key, types in STEP_ACTIONS.items():
            if key.lower() in step.lower():
                extract_types.update(types)
    if not extract_types:
        extract_types = {"emails", "phones", "company", "summary"}

    out += f"📌 MCTS decided to extract: {', '.join(sorted(extract_types))}\n\n"

    if not urls:
        out += "💡 No URLs provided. Include URLs in your query:\n"
        out += "   Example: 'find leads from https://company.com/team'\n\n"
        llm    = get_llm()
        advice = llm.invoke(f"""Lead generation strategy for: {query}

MCTS Plan suggests focusing on: {', '.join(plan[:3])}

Provide:
1. Best sources to find these leads in India (LinkedIn, JustDial, Naukri etc.)
2. Exact URLs/platforms to target
3. Information to collect: {', '.join(sorted(extract_types))}
4. Outreach message template
5. Tools & automation options""")
        out += "📋 Lead Strategy:\n" + str(advice) + "\n"
        return out

    # Execute extraction in MCTS-planned order
    leads       = []
    total_emails = 0
    total_phones = 0

    out += f"🌐 Scraping {len(urls)} URL(s) per MCTS plan...\n"
    for i, url in enumerate(urls[:5]):
        page = _fetch_page(url)
        if not page or "error" in page:
            out += f"   ❌ {url}: {page.get('error','failed') if page else 'failed'}\n"
            continue

        lead = {"url": url, "company": page.get("title","Unknown")}

        if "emails" in extract_types:
            lead["emails"] = page.get("emails", [])
            total_emails  += len(lead["emails"])
        if "phones" in extract_types:
            lead["phones"] = page.get("phones", [])
            total_phones  += len(lead["phones"])
        if "summary" in extract_types:
            lead["summary"] = " ".join(page.get("paras", []))[:250]
        if "company" in extract_types:
            lead["headings"] = page.get("headings", [])

        leads.append(lead)
        out += f"   ✅ {url} — "
        out += f"E:{len(lead.get('emails',[]))} "
        out += f"P:{len(lead.get('phones',[]))}\n"

    out += f"\n📊 Results:\n{'='*60}\n"
    for i, lead in enumerate(leads, 1):
        out += f"\n#{i}  {lead.get('company','Unknown')[:60]}\n"
        out += f"    🔗 {lead.get('url','')}\n"
        if lead.get('emails'):
            out += f"    📧 {', '.join(lead['emails'])}\n"
        if lead.get('phones'):
            out += f"    📞 {', '.join(lead['phones'])}\n"
        if lead.get('summary'):
            out += f"    📝 {lead['summary'][:150]}\n"
        if lead.get('headings'):
            out += f"    🏷️  {' | '.join(lead['headings'][:3])}\n"

    out += f"\n{'='*60}\n"
    out += f"✅ {len(leads)} pages scraped | 📧 {total_emails} emails | 📞 {total_phones} phones\n"
    out += _variant_summary_line(
        mcts.get('variant','Basic-MCTS'), mcts.get('score',0),
        mcts.get('time_ms',0)
    ) + "\n"
    out += ("💡 Why Basic-MCTS? — fast UCB1 planning decides extraction priority order "
            "(emails > phones > company info) without slow LLM/retrieval calls.\n")
    return out


# ══════════════════════════════════════════════════════════════════
# 3. CONTENT SUMMARIZATION
#
# HOW MCTS IMPROVES IT:
#   MCTS-RAG seeds Wikipedia context BEFORE building the plan.
#   The retrieved chunks shape which "Retrieve" steps appear in the
#   plan, and those steps control what text the LLM focuses on.
# ══════════════════════════════════════════════════════════════════
def plan_summarize(query: str, urls: list = None,
                   simulations: int = 3) -> str:
    _ensure_path()
    from llm import get_llm

    # MCTS-RAG: Wikipedia context seeded before planning
    mcts  = _run_mcts(
        f"retrieve summarize extract key insights: {query}",
        variant_key="rag-mcts", simulations=simulations
    )
    plan   = mcts.get("plan", [])
    chunks = mcts.get("retrieved_chunks", 0)

    out  = f"📄 Content Summarization\n{'='*60}\n"
    out += f"🎯 Topic   : {query}\n"
    out += f"⚡ Variant : {mcts.get('variant','')} | Score: {mcts.get('score',0):.1f}/10\n"
    out += f"📡 Wikipedia chunks seeded: {chunks}\n\n"
    out += f"🌳 MCTS-RAG Extraction Plan:\n"
    for i, step in enumerate(plan, 1):
        out += f"   {i}. {step}\n"
    out += "\n"

    # MCTS plan steps determine extraction depth
    # "Retrieve" steps → fetch from URLs
    # "Analyze" steps  → deep extraction
    # "Synthesize"     → cross-source comparison
    do_deep    = any("Analyze" in s or "Data" in s for s in plan)
    do_compare = any("Synthesize" in s or "Compare" in s for s in plan)

    extracted = []
    if urls:
        out += f"🌐 Extracting from {len(urls)} URL(s) "
        out += f"({'deep' if do_deep else 'standard'} mode)...\n"
        for url in urls[:3]:
            page = _fetch_page(url)
            if page and "error" not in page:
                depth = 400 if do_deep else 200
                text  = " ".join(page.get("paras", []))[:depth]
                extracted.append({
                    "title":    page["title"],
                    "headings": page.get("headings", []),
                    "content":  text,
                    "url":      url,
                })
                out += f"   ✅ {page['title'][:60]}\n"

        if do_compare and len(extracted) > 1:
            out += f"   🔄 Cross-source comparison enabled by MCTS plan\n"
        out += "\n"

    llm = get_llm()
    if extracted:
        content_block = "\n\n".join(
            f"[SOURCE {i+1}: {e['title']}]\n"
            f"Headings: {' | '.join(e['headings'][:3])}\n"
            f"Content: {e['content']}"
            for i, e in enumerate(extracted)
        )
        prompt = f"""Summarize the following content for: {query}

MCTS-RAG Extraction Plan used:
{chr(10).join(f'{i+1}. {s}' for i,s in enumerate(plan))}

Web Content (extracted per plan):
{content_block[:2500]}

{'Compare across all sources.' if do_compare else ''}
{'Provide deep analysis with data points.' if do_deep else ''}

Provide:
1. Key Takeaways (3-5 bullet points)
2. Main Topics Covered
3. Important Data / Statistics
4. Actionable Insights"""
    else:
        prompt = f"""Provide a comprehensive summary for: {query}

MCTS-RAG Plan:
{chr(10).join(f'{i+1}. {s}' for i,s in enumerate(plan))}

Include:
1. Key Takeaways
2. Main Points
3. Important Facts / Statistics
4. Actionable Insights

Be concise and structured."""

    summary = llm.invoke(prompt)
    out += "📋 Summary:\n" + "-"*60 + "\n"
    out += str(summary) + "\n"
    out += f"\n{'='*60}\n"
    out += _variant_summary_line(
        mcts.get('variant','MCTS-RAG'), mcts.get('score',0),
        mcts.get('time_ms',0), chunks
    ) + "\n"
    out += ("💡 Why MCTS-RAG? — seeds Wikipedia context before planning so retrieved "
            "knowledge shapes which 'Retrieve' steps appear in the plan.\n")
    return out


# ══════════════════════════════════════════════════════════════════
# 4. JOB SEARCH
#
# HOW MCTS IMPROVES IT:
#   R-MCTS retrieves live job-market snippets per node.
#   The plan steps that score highest have the most relevant snippets.
#   Each plan step triggers a real Bing search for that aspect,
#   and the live snippets are fed into the LLM market analysis.
# ══════════════════════════════════════════════════════════════════
def plan_job_search(query: str, simulations: int = 4) -> str:
    _ensure_path()
    from llm import get_llm

    role = _extract_job_role(query)

    mcts  = _run_mcts(
        f"search find jobs career opportunities salary market: {query}",
        variant_key="r-mcts", simulations=simulations
    )
    plan  = mcts.get("plan", [])

    out  = f"💼 MCTS Job Search\n{'='*60}\n"
    out += f"🎯 Query   : {query}\n"
    out += f"🔍 Role    : {role}\n"
    out += f"⚡ Variant : {mcts.get('variant','')} | Score: {mcts.get('score',0):.1f}/10\n"
    out += f"📡 Live snippets during planning: {mcts.get('retrieved_snippets',0)}\n\n"
    out += f"🌳 R-MCTS Search Plan:\n"
    for i, step in enumerate(plan, 1):
        out += f"   {i}. {step}\n"
    out += "\n"

    # Each plan step → targeted Bing search for live job market data
    live_data = {}
    STEP_SEARCH_MAP = {
        "Search Primary Platform":   f"{role} jobs India 2025",
        "Search Secondary Platform": f"{role} hiring companies India salary",
        "Extract Product Details":   f"{role} skills requirements India job",
        "Gather Information":        f"{role} job market trends India",
        "Analyze Data":              f"{role} salary package India LPA",
        "Provide Recommendations":   f"how to get {role} job India tips",
        "Compare Alternatives":      f"{role} vs related roles career India",
    }

    out += "🔍 Live job market data per MCTS step...\n"
    for step in plan[:4]:
        search_q = STEP_SEARCH_MAP.get(step, f"{role} {step} India")
        results  = _bing_search(search_q, n=2)
        if results:
            live_data[step] = results
            out += f"   ✅ {step}: {results[0]['snippet'][:80]}...\n"
    out += "\n"

    # Job portals with MCTS-role-based search links
    q = role.replace(' ', '+')
    portals = {
        "LinkedIn":     f"https://www.linkedin.com/jobs/search/?keywords={role.replace(' ','%20')}&location=India",
        "Naukri":       f"https://www.naukri.com/{role.lower().replace(' ','-')}-jobs",
        "Indeed India": f"https://in.indeed.com/jobs?q={q}&l=India",
        "Internshala":  f"https://internshala.com/jobs/{role.lower().replace(' ','-')}-jobs",
        "Shine":        f"https://www.shine.com/job-search/{role.lower().replace(' ','-')}-jobs",
        "Glassdoor":    f"https://www.glassdoor.co.in/Job/india-{role.lower().replace(' ','-')}-jobs-SRCH_IL.0,5_IN115.htm",
        "Freshersworld":f"https://www.freshersworld.com/jobs/jobsearch/{role.lower().replace(' ','-')}-jobs-in-india",
    }
    out += "🔗 Search Links (R-MCTS optimised role):\n"
    for name, url in portals.items():
        out += f"   • {name:<16}: {url}\n"
    out += "\n"

    # Build live context from MCTS-retrieved snippets
    live_context = []
    for step, results in live_data.items():
        for r in results:
            live_context.append(f"[{step}] {r['snippet']}")
    live_text = "\n".join(live_context[:6]) or "No live data."

    llm      = get_llm()
    analysis = llm.invoke(f"""You are a job market expert for India (2024-2025).

Job Search: {query}
Role: {role}

MCTS R-MCTS Plan (shaped by live job market retrieval):
{chr(10).join(f'{i+1}. {s}' for i,s in enumerate(plan))}

Live Market Data (retrieved per MCTS step):
{live_text}

Using this live data, provide:
1. Current demand level (High / Medium / Low) and why
2. Top 6-8 hiring companies in India right now
3. Salary range ₹ INR: Fresher | 2-4 yrs | 5+ yrs
4. Must-have skills and certifications
5. Top 4-5 cities hiring for this role
6. Remote / WFH availability (%)
7. How to crack interviews at Indian companies
8. 6-month career roadmap to land this job""")

    out += "📊 Market Analysis (live data + MCTS plan):\n" + "-"*60 + "\n"
    out += str(analysis) + "\n"
    out += f"\n{'='*60}\n"
    live_total = sum(len(v) for v in live_data.values())
    out += _variant_summary_line(
        mcts.get('variant','R-MCTS'), mcts.get('score',0),
        mcts.get('time_ms',0), live_total
    ) + "\n"
    out += ("💡 Why R-MCTS? — retrieves live job market snippets per planning node "
            "so salary ranges and demand data reflect current 2024-2025 market.\n")
    return out


def _extract_job_role(query: str) -> str:
    stop = {'find','search','looking','jobs','job','positions','openings',
            'roles','opportunities','for','a','an','the','in','at',
            'india','remote','fresher','experienced','senior','junior',
            'python','developer','engineer','analyst','manager'}
    # Keep technical terms
    keep = {'python','java','javascript','react','node','data','machine',
            'learning','ai','ml','devops','cloud','aws','android','ios',
            'flutter','django','fastapi','software','full','stack','front',
            'back','cyber','security','product','ui','ux','marketing',
            'sales','finance','hr','operations','content'}
    words = [w for w in query.lower().split()
             if (w not in stop or w in keep) and len(w) > 1]
    return ' '.join(words[:6]).strip() or query[:40]


# ══════════════════════════════════════════════════════════════════
# 5. CONTENT MONITORING
#
# HOW MCTS IMPROVES IT:
#   MCTS plan steps map to specific detectors.
#   "Identify Pricing Data" → price extractor runs
#   "Find Recent Updates"   → date/recency checker runs
#   "Verify Information"    → content change detector runs
#   Score improves if high-value indicators found.
# ══════════════════════════════════════════════════════════════════
def plan_monitor(query: str, urls: list = None,
                 simulations: int = 3) -> str:
    _ensure_path()
    from llm import get_llm

    mcts  = _run_mcts(
        f"monitor track changes detect updates: {query}",
        variant_key="basic-mcts", simulations=simulations
    )
    plan  = mcts.get("plan", [])

    out  = f"👁️  Content Monitor\n{'='*60}\n"
    out += f"📋 Monitoring : {query}\n"
    out += f"⚡ Variant    : {mcts.get('variant','')} | Score: {mcts.get('score',0):.1f}/10\n\n"
    out += f"🌳 MCTS Monitoring Plan:\n"
    for i, step in enumerate(plan, 1):
        out += f"   {i}. {step}\n"
    out += "\n"

    # Map plan steps to detectors
    run_price   = any(s in ' '.join(plan).lower() for s in
                      ['price','product','compare','search'])
    run_recency = any(s in ' '.join(plan).lower() for s in
                      ['recent','update','find','gather'])
    run_jobs    = any(s in query.lower() for s in
                      ['job','hiring','career','vacancy'])
    run_product = any(s in query.lower() for s in
                      ['product','launch','release','stock'])

    out += f"📌 MCTS-activated detectors: "
    detectors = []
    if run_price:   detectors.append("💰 Price")
    if run_recency: detectors.append("🆕 Recency")
    if run_jobs:    detectors.append("💼 Jobs")
    if run_product: detectors.append("📦 Products")
    out += " | ".join(detectors) + "\n\n"

    if not urls:
        out += "💡 No URLs provided. Add URLs to monitor:\n"
        out += "   Example: 'monitor https://site.com for price drops'\n\n"
        llm    = get_llm()
        advice = llm.invoke(f"""Monitoring strategy for: {query}

MCTS Plan steps: {', '.join(plan)}

Provide:
1. Specific indicators to track (based on MCTS plan)
2. Recommended check frequency
3. Best monitoring tools/websites for India
4. Alert setup (price threshold, keywords)
5. What counts as a "significant change"
6. Automation scripts / services to use""")
        out += "📋 Monitoring Strategy:\n" + str(advice) + "\n"
        return out

    out += f"🌐 Checking {len(urls)} URL(s)...\n"
    changes_found = 0

    for url in urls[:5]:
        page = _fetch_page(url)
        if not page or "error" in page:
            out += f"\n❌ {url}: {page.get('error','failed') if page else 'failed'}\n"
            continue

        out += f"\n✅ {page['title'][:60]}\n"
        out += f"   URL     : {url}\n"

        # Run MCTS-activated detectors
        if run_price and page.get("prices"):
            out += f"   💰 Prices found: {', '.join(page['prices'][:4])}\n"
            changes_found += 1

        if run_recency:
            text = page.get("text", "")
            years_found = [y for y in ['2025','2024'] if y in text]
            if years_found:
                out += f"   🆕 Recent content: {', '.join(years_found)} mentions\n"
                changes_found += 1

        if run_jobs:
            text  = page.get("text","").lower()
            found = [kw for kw in ['hiring','apply now','job opening','vacancy','careers']
                     if kw in text]
            if found:
                out += f"   💼 Job indicators: {', '.join(found[:3])}\n"
                changes_found += 1

        if run_product:
            text  = page.get("text","").lower()
            found = [kw for kw in ['new','launch','release','available','stock']
                     if kw in text[:500]]
            if found:
                out += f"   📦 Product signals: {', '.join(found[:3])}\n"
                changes_found += 1

        if page.get("headings"):
            out += f"   📑 Sections: {' | '.join(page['headings'][:3])}\n"

    out += f"\n{'='*60}\n"
    out += f"📊 {changes_found} change indicator(s) detected across {len(urls)} URL(s)\n"
    out += _variant_summary_line(
        mcts.get('variant','Basic-MCTS'), mcts.get('score',0),
        mcts.get('time_ms',0)
    ) + "\n"
    out += ("💡 Why Basic-MCTS? — fast tree search maps plan steps to specific detectors "
            "(price / recency / jobs / products) without external API calls.\n")
    return out


# ══════════════════════════════════════════════════════════════════
# 6. SCHEDULING & BOOKING
#
# HOW MCTS IMPROVES IT:
#   WM-MCTS scores each booking step using a world model that
#   weights steps like "Compare Options" and "Finalize" higher.
#   The highest-scoring path through the tree = optimal booking
#   strategy. Plan steps drive which platform category is shown
#   and which LLM booking advice is generated.
# ══════════════════════════════════════════════════════════════════
def plan_schedule(query: str, simulations: int = 3) -> str:
    _ensure_path()
    from llm import get_llm

    mcts  = _run_mcts(
        f"plan book compare options finalize: {query}",
        variant_key="wm-mcts", simulations=simulations
    )
    plan    = mcts.get("plan", [])
    q_lower = query.lower()

    out  = f"📅 Booking & Scheduling\n{'='*60}\n"
    out += f"🎯 Request : {query}\n"
    out += f"⚡ Variant : {mcts.get('variant','')} | Score: {mcts.get('score',0):.1f}/10\n\n"
    out += f"🌳 WM-MCTS Booking Plan (world-model scored):\n"
    for i, step in enumerate(plan, 1):
        out += f"   {i}. {step}\n"
    out += "\n"

    # WM-MCTS plan drives platform selection and booking depth
    do_compare = any("Compare" in s or "Options" in s for s in plan)
    do_finalize= any("Finalize" in s or "Recommend" in s for s in plan)

    # Detect booking type from query
    if any(w in q_lower for w in ['flight','fly','air','ticket','airline']):
        booking_type = "flight"
        emoji = "✈️ "
        links = {
            "MakeMyTrip": "https://www.makemytrip.com/flights/",
            "Yatra":       "https://www.yatra.com/flights",
            "Cleartrip":   "https://www.cleartrip.com/flights/",
            "EaseMyTrip":  "https://www.easemytrip.com/flights.html",
            "IRCTC Air":   "https://www.air.irctc.co.in/",
            "Skyscanner":  "https://www.skyscanner.co.in/",
        }
    elif any(w in q_lower for w in ['hotel','stay','room','accommodation','resort']):
        booking_type = "hotel"
        emoji = "🏨 "
        links = {
            "MakeMyTrip": "https://www.makemytrip.com/hotels/",
            "OYO Rooms":  "https://www.oyorooms.com/",
            "Goibibo":    "https://www.goibibo.com/hotels/",
            "Booking.com":"https://www.booking.com/",
            "Treebo":     "https://www.treebohotels.com/",
            "Agoda":      "https://www.agoda.com/",
        }
    elif any(w in q_lower for w in ['train','rail','irctc','railway']):
        booking_type = "train"
        emoji = "🚂 "
        links = {
            "IRCTC":      "https://www.irctc.co.in/nget/train-search",
            "ixigo":      "https://www.ixigo.com/train-tickets",
            "Paytm Train":"https://tickets.paytm.com/trains/",
            "Goibibo":    "https://www.goibibo.com/trains/",
            "MakeMyTrip": "https://www.makemytrip.com/railways/",
        }
    elif any(w in q_lower for w in ['doctor','hospital','clinic','appointment','health']):
        booking_type = "healthcare"
        emoji = "🏥 "
        links = {
            "Practo":    "https://www.practo.com/",
            "Apollo247": "https://www.apollo247.com/",
            "1mg":       "https://www.1mg.com/",
            "Lybrate":   "https://www.lybrate.com/",
            "DocsApp":   "https://www.docsapp.in/",
        }
    elif any(w in q_lower for w in ['bus','volvo','sleeper']):
        booking_type = "bus"
        emoji = "🚌 "
        links = {
            "RedBus":     "https://www.redbus.in/",
            "AbhiBus":    "https://www.abhibus.com/",
            "MakeMyTrip": "https://www.makemytrip.com/bus-tickets/",
            "Goibibo":    "https://www.goibibo.com/bus/",
        }
    else:
        booking_type = "general"
        emoji = "📅 "
        links = {
            "MakeMyTrip": "https://www.makemytrip.com/",
            "Yatra":      "https://www.yatra.com/",
            "Goibibo":    "https://www.goibibo.com/",
        }

    out += f"{emoji}Booking Platforms"
    if do_compare:
        out += " (WM-MCTS: compare options enabled)"
    out += ":\n"
    for name, url in links.items():
        out += f"   • {name:<15}: {url}\n"
    out += "\n"

    llm    = get_llm()
    advice = llm.invoke(f"""You are a booking and travel expert for India.

Booking Request: {query}
Booking Type: {booking_type}

WM-MCTS Plan (world-model scored — higher score = better step):
{chr(10).join(f'{i+1}. {s}' for i,s in enumerate(plan))}

World Model said: {'Compare options before finalizing' if do_compare else 'Direct booking recommended'}

Provide:
1. Best time to book for lowest ₹ INR price
2. Expected price range (₹ INR)
3. {'Detailed comparison of top 3 options' if do_compare else 'Top recommended option'}
4. Step-by-step booking process
5. Cancellation / refund policy advice
6. Pro tips to save money in India
7. What to watch out for""")

    out += "💡 Booking Strategy:\n" + "-"*60 + "\n"
    out += str(advice) + "\n"
    out += f"\n{'='*60}\n"
    out += _variant_summary_line(
        mcts.get('variant','WM-MCTS'), mcts.get('score',0),
        mcts.get('time_ms',0)
    ) + "\n"
    out += f"   Compare mode: {'ON' if do_compare else 'OFF'} | Finalize: {'YES' if do_finalize else 'PENDING'}\n"
    out += ("💡 Why WM-MCTS? — world model scores 'Compare Options' and 'Finalize' "
            "steps higher, ensuring the plan always reaches a concrete booking decision.\n")
    return out


# ══════════════════════════════════════════════════════════════════
# 7. WEB QA TESTING
#
# HOW MCTS IMPROVES IT:
#   Basic-MCTS plans the order of test execution.
#   Low-scoring plans run fewer tests (quick audit).
#   High-scoring plans run deeper tests (full audit).
#   Plan steps map directly to which checks are run.
#   "Check Security" step → security checks execute.
#   "Analyze Performance" → performance suite runs.
# ══════════════════════════════════════════════════════════════════
def plan_qa_test(query: str, url: str = None, simulations: int = 4) -> str:
    _ensure_path()
    from llm import get_llm
    from config import REQUEST_TIMEOUT

    mcts  = _run_mcts(
        f"web testing quality assurance security performance analysis: {query}",
        variant_key="basic-mcts", simulations=simulations
    )
    plan  = mcts.get("plan", [])
    score = mcts.get("score", 0)

    out  = f"🧪 MCTS Web QA Testing\n{'='*60}\n"
    out += f"⚡ Variant : {mcts.get('variant','')} | Score: {score:.1f}/10\n\n"
    out += f"🌳 MCTS Test Plan (higher score = more thorough tests):\n"
    for i, step in enumerate(plan, 1):
        out += f"   {i}. {step}\n"
    out += "\n"

    # MCTS score determines test depth
    deep_test = score >= 7.0
    out += f"📌 Test depth: {'🔬 Full audit' if deep_test else '🔎 Standard audit'} "
    out += f"(MCTS score: {score:.1f}/10)\n\n"

    if not url:
        out += "⚠️  No URL provided.\n"
        out += "   Example: 'test https://yourwebsite.com'\n\n"
        llm    = get_llm()
        advice = llm.invoke(f"""QA testing guide for: {query}

MCTS Plan: {', '.join(plan)}
Test depth: {'Full audit' if deep_test else 'Standard audit'}

Provide a complete checklist.""")
        out += str(advice)
        return out

    out += f"🌐 Testing: {url}\n\n"

    # MCTS plan steps activate specific test suites
    run_security    = any(s in ' '.join(plan).lower() for s in
                          ['analyze','check','security','verify'])
    run_performance = any(s in ' '.join(plan).lower() for s in
                          ['analyze','performance','data','gather'])
    run_seo         = any(s in ' '.join(plan).lower() for s in
                          ['research','compare','alternatives'])

    # Always run core checks
    page = _fetch_page(url, timeout=REQUEST_TIMEOUT)
    results = {}

    if not page or "error" in page:
        out += f"❌ Could not access URL: {page.get('error','unknown') if page else 'failed'}\n"
        return out

    soup = BeautifulSoup(requests.get(
        url, headers={"User-Agent": random.choice(_UA)}, timeout=REQUEST_TIMEOUT
    ).text, 'html.parser')

    # --- Core: always run ---
    # HTTP
    load_ms = page.get("load_ms", 0)
    import time as _t
    t0 = _t.time()
    try:
        _r = requests.get(url, headers={"User-Agent": random.choice(_UA)},
                          timeout=REQUEST_TIMEOUT)
        load_ms = (_t.time() - t0) * 1000
        status  = _r.status_code
        resp_headers = dict(_r.headers)
    except Exception:
        status = 0
        resp_headers = {}

    results["HTTP Status"] = {
        "passed":  status == 200,
        "details": [
            f"Status: {status} {'✅ OK' if status==200 else '❌'}",
            f"Load time: {load_ms:.0f}ms {'✅ Fast' if load_ms<2000 else '⚠️  Slow (>2s)'}",
            f"Content-Type: {resp_headers.get('Content-Type','?')[:50]}",
        ]
    }

    title  = soup.find('title')
    h1s    = soup.find_all('h1')
    h2s    = soup.find_all('h2')
    results["Page Structure"] = {
        "passed":  bool(title) and len(h1s) == 1,
        "details": [
            f"Title: {'✅ '+title.get_text(strip=True)[:50] if title else '❌ MISSING'}",
            f"H1 count: {'✅ 1' if len(h1s)==1 else f'⚠️  {len(h1s)} (should be exactly 1)'}",
            f"H2 count: {len(h2s)} headings",
            f"Semantic tags: main={'✅' if soup.find('main') else '❌'} "
            f"nav={'✅' if soup.find('nav') else '⚠️'} "
            f"footer={'✅' if soup.find('footer') else '⚠️'}",
        ]
    }

    imgs   = soup.find_all('img')
    no_alt = [i for i in imgs if not i.get('alt')]
    results["Accessibility"] = {
        "passed":  len(no_alt) == 0,
        "details": [
            f"Images: {len(imgs)} total",
            f"Missing alt text: {'✅ None' if not no_alt else f'❌ {len(no_alt)} image(s)'}",
            f"Viewport meta: {'✅' if soup.find('meta',{'name':'viewport'}) else '⚠️  Missing (mobile)'}",
        ]
    }

    links     = soup.find_all('a', href=True)
    ext_links = [l for l in links if l['href'].startswith('http')]
    empty_l   = [l for l in links if not l['href'] or l['href']=='#']
    results["Links"] = {
        "passed":  len(empty_l) < 3,
        "details": [
            f"Total links: {len(links)}",
            f"External: {len(ext_links)}",
            f"Empty/# links: {len(empty_l)} {'✅' if len(empty_l)<3 else '⚠️  Clean these up'}",
        ]
    }

    # --- MCTS-activated: Security (if plan includes it) ---
    if run_security or deep_test:
        has_https = url.startswith('https')
        csp       = resp_headers.get('Content-Security-Policy')
        xframe    = resp_headers.get('X-Frame-Options')
        hsts      = resp_headers.get('Strict-Transport-Security')
        results["Security"] = {
            "passed":  has_https,
            "details": [
                f"HTTPS: {'✅' if has_https else '❌ NOT using HTTPS — critical!'}",
                f"CSP:  {'✅' if csp    else '⚠️  Missing Content-Security-Policy'}",
                f"X-Frame-Options: {'✅' if xframe else '⚠️  Missing (clickjacking risk)'}",
                f"HSTS: {'✅' if hsts   else 'ℹ️  Not set'}",
                f"Server: {resp_headers.get('Server','Hidden')}",
            ]
        }

    # --- MCTS-activated: SEO (if plan includes research steps) ---
    if run_seo or deep_test:
        desc = soup.find('meta', {'name':'description'})
        kw   = soup.find('meta', {'name':'keywords'})
        og   = soup.find('meta', {'property':'og:title'})
        can  = soup.find('link', {'rel':'canonical'})
        results["SEO"] = {
            "passed":  bool(desc),
            "details": [
                f"Meta desc:  {'✅ '+desc['content'][:50] if desc and desc.get('content') else '❌ Missing (hurts SEO)'}",
                f"Keywords:   {'✅' if kw  else 'ℹ️  Not set'}",
                f"OG tags:    {'✅' if og  else '⚠️  Missing (social sharing)'}",
                f"Canonical:  {'✅' if can else 'ℹ️  Not set'}",
            ]
        }

    # --- MCTS-activated: Performance (if plan includes analyze steps) ---
    if run_performance or deep_test:
        page_kb = page.get("size_kb", 0)
        scripts = len(soup.find_all('script'))
        css     = len(soup.find_all('link', {'rel':'stylesheet'}))
        results["Performance"] = {
            "passed":  page_kb < 500,
            "details": [
                f"Page size: {page_kb:.1f} KB {'✅' if page_kb<500 else '⚠️  Large — consider optimization'}",
                f"Scripts:   {scripts} {'✅' if scripts<10 else '⚠️  Many (check for unused)'}",
                f"CSS files: {css}",
                f"Forms:     {len(soup.find_all('form'))}",
            ]
        }

    # Output results
    out += "📊 Test Results:\n" + "-"*60 + "\n"
    passed = 0
    for category, result in results.items():
        icon = "✅" if result['passed'] else "⚠️ "
        if result['passed']:
            passed += 1
        out += f"\n{icon} {category}\n"
        for detail in result['details']:
            out += f"   {detail}\n"

    total    = len(results)
    qa_score = (passed / total) * 100 if total > 0 else 0

    out += f"\n{'='*60}\n"
    out += f"📈 QA Score: {qa_score:.0f}% ({passed}/{total} checks passed)\n"
    out += _variant_summary_line(
        mcts.get('variant','Basic-MCTS'), score,
        mcts.get('time_ms',0)
    ) + "\n"
    out += f"   Depth: {'Full audit' if deep_test else 'Standard audit'} | Tests run: {total}\n"

    if qa_score < 60:
        out += "🚨 Site needs immediate attention — multiple critical issues found\n"
    elif qa_score < 80:
        out += "⚠️  Site has issues — review warnings above\n"
    else:
        out += "✅ Site is in good shape!\n"

    out += ("💡 Why Basic-MCTS? — high-score plans activate deeper test suites "
            "(security, SEO, performance). Low-score plans run core checks only.\n")
    return out


# ══════════════════════════════════════════════════════════════════
# 8. GENERAL PLANNING (fallback for all other queries)
# ══════════════════════════════════════════════════════════════════
def plan_general(query: str, variant_key: str = "basic-mcts",
                 simulations: int = 5) -> dict:
    """
    General-purpose MCTS planning.
    If variant_key is "basic-mcts" (default), auto-selects the best
    variant based on query content. Always returns raw MCTS result dict.
    """
    _ensure_path()

    # Auto-select best variant when user hasn't explicitly chosen one
    final_key = variant_key
    auto_reason = ""
    if variant_key == "basic-mcts":
        auto_key, auto_reason = _select_best_variant(query)
        # Only auto-upgrade if the signal is strong (score > 1)
        q = query.lower()
        signals = {
            'r-mcts':   ['latest','current','recent','competitor','market',
                          'find','search','news','trend','2024','2025'],
            'rag-mcts': ['explain','understand','concept','summarize',
                          'how to','what is','guide','overview','learn'],
            'wm-mcts':  ['plan','strategy','steps','how should','recommend',
                          'build','create','marketing','roadmap','implement'],
        }
        for vk, kws in signals.items():
            if sum(1 for kw in kws if kw in q) >= 2:
                final_key   = vk
                auto_reason = f"Auto-selected: {signals[vk][0]} signals detected"
                break

    result = _run_mcts(query, variant_key=final_key, simulations=simulations)

    # Add auto-selection metadata to result
    result["auto_selected"]  = final_key != variant_key
    result["auto_reason"]    = auto_reason
    result["variant_key"]    = final_key
    return result


# ── Public API ─────────────────────────────────────────────────────
__all__ = [
    "plan_research", "plan_lead_generation", "plan_summarize",
    "plan_job_search", "plan_monitor", "plan_schedule",
    "plan_qa_test", "plan_general",
]