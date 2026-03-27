import json
import requests
import time
import re
import pandas as pd
import numpy as np

# Configuration
BASE_URL = "http://localhost:5000"

# Simple tokenizer (fallback if NLTK punkt unavailable)
def simple_tokenize(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    return set(text.split())

# Try to use NLTK's word_tokenize, fallback to simple
try:
    from nltk.tokenize import word_tokenize
    import nltk
    nltk.data.find('tokenizers/punkt')
    def tokenize(text):
        return set(word_tokenize(text.lower()))
except (ImportError, LookupError):
    def tokenize(text):
        return simple_tokenize(text)
    print("NLTK punkt not available, using simple tokenizer.")

# --- Test Dataset (add more entries for meaningful statistics) ---
TEST_DATA = [
    {
        "text": "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by animals including humans. Leading AI textbooks define the field as the study of 'intelligent agents': any system that perceives its environment and takes actions that maximize its chance of achieving its goals.",
        "media_analyses": [],
        "ground_truth": "AI is machine intelligence that studies intelligent agents which perceive their environment and act to achieve goals."
    },
    # Add more test cases here (see examples below)
]

def compute_metrics(reference, hypothesis):
    ref_tokens = tokenize(reference)
    hyp_tokens = tokenize(hypothesis)
    intersection = ref_tokens & hyp_tokens
    precision = len(intersection) / len(hyp_tokens) if hyp_tokens else 0
    recall = len(intersection) / len(ref_tokens) if ref_tokens else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision+recall) > 0 else 0
    accuracy = len(intersection) / len(ref_tokens | hyp_tokens) if (ref_tokens | hyp_tokens) else 0
    return precision, recall, f1, accuracy

def run_pipeline(variant, test_item):
    # Step 1: Run agents
    try:
        response = requests.post(f"{BASE_URL}/summarize_multimodal", 
                                 json={"text": test_item["text"], 
                                       "media_analyses": test_item["media_analyses"]},
                                 timeout=300)
        response.raise_for_status()
        agent_results = response.json()["agent_results"]
    except Exception as e:
        print(f"   Error in /summarize_multimodal: {e}")
        return None

    # Step 2: Set MCTS flags based on variant
    use_reflection = (variant == "reflective")
    use_rag = (variant == "rag")
    use_world = (variant == "world")
    # baseline = all false

    mcts_payload = {
        "agent_results": agent_results,
        "has_multimedia": len(test_item["media_analyses"]) > 0,
        "simulations": 50,
        "use_reflection": use_reflection,
        "use_rag": use_rag,
        "use_world": use_world,
        "original_text": test_item["text"],
        "media_analyses": test_item["media_analyses"]
    }

    try:
        response = requests.post(f"{BASE_URL}/mcts_optimize", json=mcts_payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get("winning_summary", "")
    except Exception as e:
        print(f"   Error in /mcts_optimize: {e}")
        return None

def evaluate_variant(variant, dataset):
    results = []
    for idx, item in enumerate(dataset):
        print(f"Evaluating {variant} on item {idx+1}: {item['text'][:50]}...")
        hypothesis = run_pipeline(variant, item)
        if hypothesis is None:
            print("   Skipping due to error.")
            continue
        p, r, f1, acc = compute_metrics(item["ground_truth"], hypothesis)
        results.append({
            "variant": variant,
            "precision": p,
            "recall": r,
            "f1": f1,
            "accuracy": acc
        })
        print(f"   F1: {f1:.3f}")
    return results

if __name__ == "__main__":
    # Make sure the server is reachable
    try:
        requests.get(f"{BASE_URL}/health", timeout=5)
        print("✅ Server is reachable.\n")
    except:
        print("❌ Cannot connect to Flask server. Make sure `python app.py` is running.")
        exit(1)

    variants = ["baseline", "reflective", "rag", "world"]
    all_results = []
    for var in variants:
        var_results = evaluate_variant(var, TEST_DATA)
        all_results.extend(var_results)

    if not all_results:
        print("No results collected. Check server and test data.")
        exit(1)

    df = pd.DataFrame(all_results)
    summary = df.groupby("variant").agg(["mean", "std"]).round(3)
    print("\n=== Evaluation Results ===")
    print(summary)

    # Save to CSV
    df.to_csv("mcts_evaluation.csv", index=False)
    print("\nResults saved to mcts_evaluation.csv")