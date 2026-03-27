# # backend/agent.py
# from llm import get_llm
# from tools.ecommerce import handle_ecommerce
# from tools.scraper import scrape_and_summarize
# import re


# def classify(query: str) -> str:
#     """Route query to the correct handler."""
#     q = query.lower()

#     # ── E-commerce / price comparison ────────────────────────────
#     # Single strong keywords
#     ecommerce_single = [
#         'buy', 'purchase', 'cheapest', 'lowest price', 'best deal',
#         'price on amazon', 'price on flipkart', 'price on myntra',
#         'shop for', 'check price', 'find price', 'discount on',
#         'order online', 'add to cart', 'best buy', 'where to buy',
#         'how much does', 'how much is', 'cost of', 'price of',
#     ]
#     if any(kw in q for kw in ecommerce_single):
#         return "ecommerce"

#     # Combo: any price word + any platform/comparison word
#     price_words   = {'price','prices','cost','costs','rate','rates','cheap','cheaper',
#                      'cheapest','affordable','deal','deals','offer','offers','discount',
#                      'discounts','worth','expensive','inexpensive','budget'}
#     platform_words= {'amazon','flipkart','myntra','croma','reliance','tatacliq','meesho',
#                      'nykaa','platform','platforms','site','sites','store','stores',
#                      'online','website','websites','shopping','ecommerce','market',
#                      'marketplace','app','apps'}
#     compare_words = {'compare','comparison','versus','vs','difference','check','find',
#                      'show','list','search','best','top','which','where','across',
#                      'multiple','various','different','all'}
#     product_words = {'laptop','laptops','phone','mobile','mobiles','phones','tablet',
#                      'tablets','watch','watches','camera','cameras','headphone',
#                      'headphones','earphone','earphones','speaker','speakers',
#                      'keyboard','mouse','monitor','tv','television','refrigerator',
#                      'washing','machine','ac','cooler','fan','mixer','grinder',
#                      'juicer','oven','microwave','iron','trimmer','shaver',
#                      'printer','scanner','router','modem','purifier','heater',
#                      'product','item','gadget','device','appliance','electronic'}

#     q_words       = set(q.split())
#     has_price     = bool(q_words & price_words)
#     has_platform  = bool(q_words & platform_words)
#     has_compare   = bool(q_words & compare_words)
#     has_product   = bool(q_words & product_words)

#     if has_price and has_platform:              return "ecommerce"
#     if has_price and has_compare:               return "ecommerce"
#     if has_product and has_platform:            return "ecommerce"
#     if has_product and has_compare and has_price: return "ecommerce"
#     if re.search(r'https?://', q) and has_price: return "ecommerce"

#     # ── Scraper ───────────────────────────────────────────────────
#     if any(w in q for w in ['scrape','extract','fetch data','get content from']):
#         return "scraper"

#     # ── Email ─────────────────────────────────────────────────────
#     if any(w in q for w in ['email','send mail','compose email','latest mail']):
#         return "mail"

#     # ── Simple factual ────────────────────────────────────────────
#     simple_kw = ['what is','who is','when is','where is','capital of',
#                  'define ','explain ','tell me about','how many','what are']
#     if any(kw in q for kw in simple_kw) and len(query.split()) < 15:
#         return "simple"

#     return "general"


# def extract_url(query: str):
#     m = re.search(r'https?://[^\s]+', query)
#     return m.group(0) if m else None


# def handle_query(query: str, mcts_variant: str = "basic-mcts", simulations: int = 5):
#     """
#     Main query handler.
#     Ecommerce queries → real-time scraper (no LLM prices ever).
#     General queries   → MCTS planning + LLM answer (INR context injected).
#     """
#     task_type = classify(query)

#     # ── Simple ────────────────────────────────────────────────────
#     if task_type == "simple":
#         llm    = get_llm()
#         answer = llm.invoke(f"Answer concisely and accurately: {query}")
#         return {"mode":"Local LLM","task_type":task_type,
#                 "plan":["Direct LLM Response"],"answer":answer,
#                 "mcts_variant":None}

#     # ── E-commerce → 3-tier real-time scraper (ZERO LLM prices) ──
#     if task_type == "ecommerce":
#         result = handle_ecommerce(query)
#         return {"mode":"Real-Time Scraper (Amazon→Flipkart→Myntra→Official)",
#                 "task_type":task_type,
#                 "plan":["Direct: Amazon.in",
#                         "Direct: Flipkart.com",
#                         "Direct: Myntra.com",
#                         "Fallback: Bing snippets if blocked"],
#                 "answer":result,
#                 "mcts_variant":"web-scraping-mcts"}

#     # ── Web scraper ───────────────────────────────────────────────
#     if task_type == "scraper":
#         url = extract_url(query)
#         if url:
#             result = scrape_and_summarize(url)
#             return {"mode":"MCTS Web Scraper","task_type":task_type,
#                     "plan":["MCTS-driven web scraping"],
#                     "answer":result,"mcts_variant":"web-scraping-mcts"}
#         return {"mode":"Error","task_type":task_type,"plan":["Error"],
#                 "answer":"❌ Please provide a valid URL. Example: scrape https://example.com",
#                 "mcts_variant":None}

#     # ── Email ─────────────────────────────────────────────────────
#     if task_type == "mail":
#         return {"mode":"Email Tool","task_type":task_type,
#                 "plan":["Email Tool"],
#                 "answer":"Please use the Email section in the extension.",
#                 "mcts_variant":None}

#     # ── General: MCTS planning → LLM execution ───────────────────
#     from mcts.variants import VARIANT_RUNNERS

#     variant_key = (mcts_variant or "basic-mcts").lower()
#     if variant_key not in VARIANT_RUNNERS:
#         variant_key = "basic-mcts"

#     # Speed caps — prevent long waits
#     if   variant_key == "wm-mcts":  simulations = min(simulations, 3)
#     elif variant_key == "rag-mcts": simulations = min(simulations, 4)
#     else:                           simulations = min(simulations, 5)

#     runner      = VARIANT_RUNNERS[variant_key]
#     mcts_result = runner(query, simulations=simulations)
#     plan_steps  = mcts_result.get("plan", [])

#     llm = get_llm()
#     final_answer = llm.invoke(f"""You are a helpful AI assistant.
# Context: India. Use ₹ INR for any currency values.

# Task: {query}

# Execution Plan ({mcts_result['variant']}):
# {chr(10).join(f'  {i+1}. {s}' for i,s in enumerate(plan_steps))}

# Provide a clear, practical answer. Do not invent specific prices — if pricing
# information is needed, direct the user to Amazon.in, Flipkart, or Smartprix.""")

#     return {
#         "mode":         f"LLM + {mcts_result['variant']}",
#         "task_type":    task_type,
#         "plan":         plan_steps,
#         "answer":       final_answer,
#         "mcts_variant": mcts_result["variant"],
#         "mcts_score":   mcts_result.get("score"),
#         "mcts_time_ms": mcts_result.get("time_ms"),
#     }
# # # #########################################################################################
# backend/agent.py
"""
Central query router.
All advanced task planning delegated to mcts/planner.py.
"""

from llm import get_llm
from tools.ecommerce import handle_ecommerce
from tools.scraper import scrape_and_summarize
import re


def classify(query: str) -> str:
    q = query.lower()

    # ── E-commerce ────────────────────────────────────────────────
    ecommerce_single = [
        'buy','purchase','cheapest','lowest price','best deal',
        'price on amazon','price on flipkart','price on myntra',
        'shop for','check price','find price','discount on',
        'order online','where to buy','how much does','how much is',
        'cost of','price of',
    ]
    if any(kw in q for kw in ecommerce_single):
        return "ecommerce"

    price_words   = {'price','prices','cost','costs','rate','rates','cheap',
                     'cheaper','cheapest','affordable','deal','deals','offer',
                     'offers','discount'}
    platform_words= {'amazon','flipkart','myntra','croma','nykaa','meesho',
                     'platform','platforms','site','sites','store','stores',
                     'online','website','websites','shopping','marketplace'}
    product_words = {'laptop','phone','mobile','tablet','watch','camera',
                     'headphone','earphone','speaker','tv','television',
                     'refrigerator','washing','machine','ac','microwave',
                     'oven','printer','router','monitor','keyboard','mouse',
                     'gpu','ssd','trimmer','fan','cooler','purifier',
                     'product','item','gadget','device','appliance'}

    q_words    = set(q.split())
    has_price  = bool(q_words & price_words)
    has_plat   = bool(q_words & platform_words)
    has_prod   = bool(q_words & product_words)
    has_cmp    = bool(q_words & {'compare','comparison','versus','vs',
                                  'across','multiple','various'})

    if has_price and has_plat:               return "ecommerce"
    if has_price and has_cmp:                return "ecommerce"
    if has_prod  and has_plat:               return "ecommerce"
    if re.search(r'https?://', q) and has_price: return "ecommerce"

    # ── Lead Generation ───────────────────────────────────────────
    if any(kw in q for kw in ['lead generation','extract leads','find leads',
                               'contact information','find contacts',
                               'scrape contacts','extract emails','get contacts']):
        return "lead_generation"

    # ── Research / Competitive Intelligence ───────────────────────
    if any(kw in q for kw in ['competitor','competitive intelligence',
                               'market research','industry analysis',
                               'company research','business research',
                               'research report','analyze company',
                               'track competitor']):
        return "research"

    # ── Summarization ─────────────────────────────────────────────
    if any(kw in q for kw in ['summarize','summarise','summary',
                               'key points','key takeaways','tldr',
                               'tl;dr','brief me','main points',
                               'extract insights','flashcard']):
        return "summarize"

    # ── Job Search ────────────────────────────────────────────────
    if any(kw in q for kw in ['job','jobs','career','hiring','vacancy',
                               'vacancies','internship','internships',
                               'fresher jobs','work from home','remote job',
                               'naukri','apply for']):
        return "job_search"

    # ── Content Monitoring ────────────────────────────────────────
    if any(kw in q for kw in ['monitor','track changes','watch for',
                               'alert me','price drop','new product launch',
                               'price alert','stock alert','check for updates']):
        return "monitor"

    # ── Scheduling & Booking ──────────────────────────────────────
    if any(kw in q for kw in ['book flight','book hotel','book train',
                               'book ticket','schedule appointment',
                               'book doctor','hotel booking','flight booking',
                               'train ticket','irctc','makemytrip',
                               'travel planning','trip planning','book a']):
        return "schedule"

    # ── QA Testing ────────────────────────────────────────────────
    if any(kw in q for kw in ['test website','qa test','quality check',
                               'accessibility','page test','check website',
                               'audit website','website audit','broken links',
                               'seo check','website analysis','test url']):
        return "qa_test"

    # ── Web Scraper ───────────────────────────────────────────────
    if any(w in q for w in ['scrape','extract from','fetch data',
                             'get content from','extract data from','crawl']):
        return "scraper"

    # ── Email ─────────────────────────────────────────────────────
    if any(w in q for w in ['email','send mail','compose email',
                             'latest mail','inbox','draft email']):
        return "mail"

    # ── Simple factual ────────────────────────────────────────────
    simple_kw = ['what is','who is','when is','where is','capital of',
                 'define ','explain ','tell me about','how many',
                 'what are','full form','abbreviation']
    if any(kw in q for kw in simple_kw) and len(query.split()) < 15:
        return "simple"

    return "general"


def extract_url(query: str):
    m = re.search(r'https?://[^\s]+', query)
    return m.group(0).rstrip('.,)') if m else None


def extract_urls(query: str) -> list:
    return [u.rstrip('.,)') for u in re.findall(r'https?://[^\s]+', query)]


def handle_query(query: str, mcts_variant: str = "basic-mcts",
                 simulations: int = 5):
    """
    Route query to the correct handler.
    Advanced tasks → mcts/planner.py
    Price scraping  → tools/ecommerce.py
    Web scraping    → tools/scraper.py
    General         → MCTS variant + LLM
    """
    task_type = classify(query)
    urls      = extract_urls(query)
    url       = urls[0] if urls else None

    # ── Simple ────────────────────────────────────────────────────
    if task_type == "simple":
        llm    = get_llm()
        answer = llm.invoke(f"Answer concisely and accurately: {query}")
        return {"mode":"Local LLM","task_type":task_type,
                "plan":["Direct LLM Response"],"answer":answer,
                "mcts_variant":None}

    # ── E-commerce ────────────────────────────────────────────────
    if task_type == "ecommerce":
        result = handle_ecommerce(query)
        return {"mode":"3-Tier Real-Time Scraper","task_type":task_type,
                "plan":["Amazon.in","Flipkart","Myntra","Official Site",
                        "Bing/DDG fallback"],
                "answer":result,"mcts_variant":"web-scraping-mcts"}

    # ── Advanced tasks — all routed through planner.py ────────────
    if task_type == "lead_generation":
        from mcts.planner import plan_lead_generation
        result = plan_lead_generation(query, urls if urls else None, simulations)
        return {"mode":"MCTS Planner → Lead Extraction","task_type":task_type,
                "plan":["Fetch pages","Extract contacts","Compile leads"],
                "answer":result,"mcts_variant":"basic-mcts"}

    if task_type == "research":
        from mcts.planner import plan_research
        result = plan_research(query, simulations)
        return {"mode":"MCTS Planner → R-MCTS Research","task_type":task_type,
                "plan":["Search sources","Extract intel","Generate report"],
                "answer":result,"mcts_variant":"r-mcts"}

    if task_type == "summarize":
        from mcts.planner import plan_summarize
        result = plan_summarize(query, urls if urls else None, simulations)
        return {"mode":"MCTS Planner → MCTS-RAG Summarizer","task_type":task_type,
                "plan":["Retrieve context","Extract key points","Synthesize"],
                "answer":result,"mcts_variant":"rag-mcts"}

    if task_type == "job_search":
        from mcts.planner import plan_job_search
        result = plan_job_search(query, simulations)
        return {"mode":"MCTS Planner → R-MCTS Job Search","task_type":task_type,
                "plan":["Plan strategy","Search portals","Analyze market"],
                "answer":result,"mcts_variant":"r-mcts"}

    if task_type == "monitor":
        from mcts.planner import plan_monitor
        result = plan_monitor(query, urls if urls else None, simulations)
        return {"mode":"MCTS Planner → Monitor","task_type":task_type,
                "plan":["Plan monitoring","Check sources","Report changes"],
                "answer":result,"mcts_variant":"basic-mcts"}

    if task_type == "schedule":
        from mcts.planner import plan_schedule
        result = plan_schedule(query, simulations)
        return {"mode":"MCTS Planner → WM-MCTS Booking","task_type":task_type,
                "plan":["Identify type","Find platforms","Advise strategy"],
                "answer":result,"mcts_variant":"wm-mcts"}

    if task_type == "qa_test":
        from mcts.planner import plan_qa_test
        result = plan_qa_test(query, url, simulations)
        return {"mode":"MCTS Planner → QA Tester","task_type":task_type,
                "plan":["Plan tests","Run checks","Generate report"],
                "answer":result,"mcts_variant":"basic-mcts"}

    # ── Web Scraper ───────────────────────────────────────────────
    # Basic-MCTS plans what to extract and in what order before scraping.
    # High-scoring plans → extract tables + headings + links + emails
    # Low-scoring plans  → extract text + headings only
    if task_type == "scraper":
        if url:
            from mcts.planner import plan_general
            # MCTS plans the extraction strategy
            scrape_plan = plan_general(
                f"extract and summarize content from {url}",
                variant_key="basic-mcts",
                simulations=3
            )
            plan_steps = scrape_plan.get("plan", ["Extract Content", "Summarize"])
            result     = scrape_and_summarize(url)
            return {
                "mode":         "Basic-MCTS + Web Scraper",
                "task_type":    task_type,
                "plan":         plan_steps,
                "answer":       result,
                "mcts_variant": "basic-mcts",
                "mcts_score":   scrape_plan.get("score"),
                "mcts_time_ms": scrape_plan.get("time_ms"),
            }
        return {"mode":"Error","task_type":task_type,"plan":["Error"],
                "answer":"❌ Please provide a valid URL. Example: scrape https://example.com",
                "mcts_variant":None}

    # ── Email ─────────────────────────────────────────────────────
    if task_type == "mail":
        return {"mode":"Email Tool","task_type":task_type,
                "plan":["Email Tool"],
                "answer":"Please use the Email section in the extension.",
                "mcts_variant":None}

    # ── General: MCTS planning + LLM ─────────────────────────────
    # plan_general() auto-selects the best MCTS variant when "basic-mcts"
    # is passed in. This means even if the user didn't pick a variant,
    # the system picks the most suitable one based on query keywords.
    from mcts.planner import plan_general

    variant_key = (mcts_variant or "basic-mcts").lower()
    if   variant_key == "wm-mcts":  simulations = min(simulations, 3)
    elif variant_key == "rag-mcts": simulations = min(simulations, 4)
    else:                           simulations = min(simulations, 5)

    mcts_result = plan_general(query, variant_key, simulations)
    plan_steps  = mcts_result.get("plan", [])
    used_variant= mcts_result.get("variant", variant_key)
    auto_chosen = mcts_result.get("auto_selected", False)
    auto_reason = mcts_result.get("auto_reason", "")

    llm = get_llm()

    # Variant-specific LLM instruction — each variant shapes the answer differently
    variant_instructions = {
        "Basic-MCTS": "Use the plan steps as a direct answer outline. Be concise.",
        "R-MCTS":     "Use the plan steps to structure your answer. Emphasise current/live aspects.",
        "WM-MCTS":    "Use the plan as a strategic roadmap. Focus on step-by-step implementation.",
        "MCTS-RAG":   "Use the plan to structure a well-researched explanation with background context.",
    }
    variant_instruction = variant_instructions.get(used_variant, "Follow the plan steps.")

    final_answer = llm.invoke(f"""You are a helpful AI assistant. Context: India.
Use ₹ INR for currency. Be practical and specific.

Task: {query}

MCTS Variant Used: {used_variant}{' (auto-selected: ' + auto_reason + ')' if auto_chosen else ''}
{variant_instruction}

Execution Plan:
{chr(10).join(f'  {i+1}. {s}' for i,s in enumerate(plan_steps))}

Provide a clear, structured, actionable answer following this plan.""")

    mode_str = f"MCTS Planner + LLM ({used_variant})"
    if auto_chosen:
        mode_str += f" [auto]"

    return {
        "mode":         mode_str,
        "task_type":    task_type,
        "plan":         plan_steps,
        "answer":       final_answer,
        "mcts_variant": used_variant,
        "mcts_score":   mcts_result.get("score"),
        "mcts_time_ms": mcts_result.get("time_ms"),
        "auto_variant": auto_chosen,
        "auto_reason":  auto_reason,
    }