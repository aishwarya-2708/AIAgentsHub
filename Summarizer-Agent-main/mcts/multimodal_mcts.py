import random
import math
import json
from typing import List, Dict, Tuple, Optional, Any
from .mcts_node import MCTSNode
import cv2
import numpy as np
from PIL import Image
import os
from mcts_variants import reflect_on_summary, retrieve_relevant_knowledge, check_world_knowledge
from config import USE_REFLECTION, USE_RAG, USE_WORLD_GUIDANCE

class MultimodalMCTSSearch:
    """Multimodal Monte Carlo Tree Search for summary selection with variants"""

    def __init__(self, agent_results: List[Dict], media_data: Dict,
                 exploration_weight: float = 1.414,
                 use_reflection: bool = USE_REFLECTION,
                 use_rag: bool = USE_RAG,
                 use_world: bool = USE_WORLD_GUIDANCE,
                 original_text: str = "",
                 media_analyses: List[str] = None):
        """
        Initialize multimodal MCTS search with variant flags

        Args:
            agent_results: List of dictionaries with 'agent_id' and 'summary'
            media_data: Dictionary containing text, video, and image data
            exploration_weight: Weight for exploration in UCT formula
            use_reflection: Enable R-MCTS (reflection)
            use_rag: Enable MCTS-RAG (retrieval)
            use_world: Enable World-Guided MCTS
            original_text: The original input text (for reflection/retrieval)
            media_analyses: List of media descriptions (for reflection)
        """
        self.agent_results = agent_results
        self.media_data = media_data
        self.exploration_weight = exploration_weight
        self.use_reflection = use_reflection
        self.use_rag = use_rag
        self.use_world = use_world
        self.original_text = original_text
        self.media_analyses = media_analyses or []
        self.root = MCTSNode()

        # Initialize untried agents at root
        self.root.untried_agents = [r["agent_id"] for r in agent_results if not r.get("error", False)]

        # Cache for multimodal evaluations
        self.evaluation_cache: Dict[Tuple[int, str], float] = {}

        # Extract media features for evaluation (unchanged)
        self.text_features = self.extract_text_features(media_data.get('text', ''))
        self.video_features = self.extract_video_features(media_data.get('video_path'))
        self.image_features = self.extract_image_features(media_data.get('images', []))
        self.media_type = self.determine_media_type()

        print(f"   Media Type: {self.media_type}")
        print(f"   Text features: {self.text_features.get('word_count', 0)} words")
        print(f"   Video features: {'Yes' if self.video_features else 'No'}")
        print(f"   Image features: {len(self.image_features)} images")
        print(f"   MCTS Variants: Reflection={use_reflection}, RAG={use_rag}, World={use_world}")

    # ... (keep all existing helper methods: determine_media_type, extract_text_features,
    #      extract_video_features, extract_image_features, extract_keywords,
    #      selection, expansion, simulation, backpropagation, etc.)

    def evaluate_multimodal_summary(self, agent_id: int, summary: str) -> float:
        """
        Evaluate a multimodal summary based on various criteria and variant scores
        """
        cache_key = (agent_id, hash(summary[:200]))

        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        # Base metrics
        word_count = len(summary.split())
        char_count = len(summary)

        # Initialize evaluation scores
        scores = {
            'content_coverage': 0.5,
            'conciseness': 0.5,
            'relevance': 0.5,
            'coherence': 0.5,
            'multimodal_integration': 0.3,
            'structure': 0.5
        }

        # Agent-specific strengths
        agent_strengths = {
            1: {'content_coverage': 0.7, 'relevance': 0.6, 'conciseness': 0.4},  # Extractive
            2: {'coherence': 0.8, 'conciseness': 0.7, 'multimodal_integration': 0.6},  # Abstractive
            3: {'structure': 0.9, 'content_coverage': 0.7, 'conciseness': 0.6},  # Bullet
            4: {'conciseness': 0.9, 'structure': 0.7, 'relevance': 0.6},  # TL;DR
            5: {'content_coverage': 0.9, 'relevance': 0.8, 'multimodal_integration': 0.7}  # Detailed
        }

        # Apply agent-specific strengths
        if agent_id in agent_strengths:
            for key, value in agent_strengths[agent_id].items():
                scores[key] = value

        # Adjust based on media type (unchanged)
        if self.media_type == "full_multimodal":
            if agent_id in [2, 5]:
                scores['multimodal_integration'] += 0.2
                scores['content_coverage'] += 0.1
        elif self.media_type == "video_text":
            if agent_id in [3, 5]:
                scores['structure'] += 0.15
                scores['content_coverage'] += 0.1
        elif self.media_type == "image_text":
            if agent_id in [2, 3]:
                scores['multimodal_integration'] += 0.15
        elif self.media_type == "video_only":
            if agent_id in [2, 5]:
                scores['content_coverage'] += 0.2
        elif self.media_type == "images_only":
            if agent_id in [3, 5]:
                scores['structure'] += 0.2

        # Quality checks
        if word_count < 10:
            scores['content_coverage'] *= 0.7
        elif word_count > 200:
            scores['conciseness'] *= 0.7

        # Check for multimodal references
        summary_lower = summary.lower()
        has_video_ref = any(word in summary_lower for word in ['video', 'film', 'clip', 'footage', 'recording'])
        has_image_ref = any(word in summary_lower for word in ['image', 'picture', 'photo', 'graphic', 'visual'])

        if self.media_data.get('video_path') and has_video_ref:
            scores['multimodal_integration'] += 0.1
        if self.media_data.get('images') and has_image_ref:
            scores['multimodal_integration'] += 0.1

        # Calculate final weighted base score
        weights = {
            'content_coverage': 0.25,
            'conciseness': 0.20,
            'relevance': 0.15,
            'coherence': 0.15,
            'multimodal_integration': 0.15,
            'structure': 0.10
        }
        base_score = sum(scores[k] * weights[k] for k in scores)

        # ----- Apply MCTS variants -----
        variant_scores = []
        if self.use_reflection:
            refl_score = reflect_on_summary(summary, self.original_text, self.media_analyses)
            variant_scores.append(("reflection", refl_score))

        if self.use_rag:
            rag_score = retrieve_relevant_knowledge(summary, self.original_text)
            variant_scores.append(("rag", rag_score))

        if self.use_world:
            world_score = check_world_knowledge(summary)
            variant_scores.append(("world", world_score))

        # Combine variant scores with base score
        if variant_scores:
            # Weights for each variant (can be tuned)
            weights_map = {"reflection": 0.3, "rag": 0.3, "world": 0.2}
            total_weight = sum(weights_map.get(name, 0.2) for name, _ in variant_scores)
            variant_avg = sum(weights_map.get(name, 0.2) * s for name, s in variant_scores) / total_weight
            final_score = 0.7 * base_score + 0.3 * variant_avg
        else:
            final_score = base_score

        # Add small random variation
        final_score += random.uniform(-0.03, 0.03)

        # Normalize to [0.1, 0.95]
        final_score = max(0.1, min(0.95, final_score))

        # Cache the result
        self.evaluation_cache[cache_key] = final_score

        # Debug logging
        if random.random() < 0.1:
            print(f"   Agent {agent_id}: Score={final_score:.3f}, Words={word_count}")

        return final_score

    # The rest of the methods (selection, expansion, simulation, backpropagation, search, etc.) remain unchanged.
    # Make sure to update simulation() to use the new evaluate_multimodal_summary.
    def simulation(self, node: MCTSNode) -> float:
        """Simulation phase: random rollout using the enhanced evaluation"""
        if node.agent_id is None and node.untried_agents:
            agent_id = random.choice(node.untried_agents)
        else:
            agent_id = node.agent_id

        agent_result = next((r for r in self.agent_results if r["agent_id"] == agent_id), None)
        if not agent_result:
            return 0.0

        return self.evaluate_multimodal_summary(agent_id, agent_result["summary"])

    # Keep all other methods (search, get_tree_structure, get_media_analysis, etc.) exactly as in original.