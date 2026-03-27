"""
MCTS Variants: R-MCTS, MCTS-RAG, World-Guided MCTS
Helper functions to be used by the MCTS optimizer.
"""

import re
import requests
from config import OLLAMA_URL, TEXT_MODEL, SIMULATED_KNOWLEDGE_BASE, WORLD_KNOWLEDGE_GRAPH

def reflect_on_summary(summary, original_text, media_analyses):
    """
    R-MCTS: Use the LLM to self-evaluate the summary for factual consistency.
    Returns a reflection score between 0 and 1 (higher = more factual).
    """
    if not summary or summary.startswith("Error"):
        return 0.0

    context = f"Original text: {original_text}\n"
    if media_analyses:
        context += "Media descriptions:\n" + "\n".join(media_analyses)

    prompt = f"""{context}

Summary to evaluate:
{summary}

Please evaluate the factual consistency of the summary with the original content.
Identify any statements in the summary that are not supported by the original text or media descriptions (hallucinations).
Rate the summary on a scale from 0 to 1, where 0 means completely hallucinated and 1 means perfectly factual.
Output only the numeric score (e.g., 0.85)."""

    try:
        payload = {
            "model": TEXT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 10, "temperature": 0.1}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        score_text = response.json().get("response", "").strip()
        match = re.search(r"0\.\d+|1\.0|1|0", score_text)
        if match:
            score = float(match.group())
            return max(0.0, min(1.0, score))
    except Exception as e:
        print(f"Reflection error: {e}")
    return 0.5  # neutral if reflection fails


def retrieve_relevant_knowledge(summary, original_text):
    """
    MCTS-RAG: Retrieve relevant passages from a knowledge base.
    Returns a score (0-1) indicating how well the summary is grounded in retrieved knowledge.
    """
    if not summary:
        return 0.0

    # Simple keyword-based retrieval from simulated knowledge base
    keywords = set(summary.lower().split())
    retrieved_scores = []
    for topic, fact in SIMULATED_KNOWLEDGE_BASE.items():
        topic_words = set(topic.lower().split())
        if keywords & topic_words:  # overlap
            # Check if summary aligns with fact (simple substring match)
            if fact.lower() in summary.lower() or any(word in fact.lower() for word in keywords):
                retrieved_scores.append(1.0)
            else:
                retrieved_scores.append(0.3)  # topic relevant but fact not mentioned
    if retrieved_scores:
        return sum(retrieved_scores) / len(retrieved_scores)
    return 0.0


def check_world_knowledge(summary):
    """
    World-Guided MCTS: Check if the summary contains statements consistent with a world knowledge graph.
    Returns a score (0-1) representing consistency.
    """
    if not summary:
        return 0.0

    consistency_score = 0.0
    matches = 0
    for subj, rel, obj in WORLD_KNOWLEDGE_GRAPH:
        if subj.lower() in summary.lower() and obj.lower() in summary.lower():
            matches += 1
            if rel.replace("_", " ") in summary.lower():
                consistency_score += 1.0
            else:
                consistency_score += 0.5
    if matches > 0:
        return consistency_score / matches
    return 0.0