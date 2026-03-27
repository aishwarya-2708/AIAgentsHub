import sys
import os
import time
import random
import math
import json
import cv2
import numpy as np
from PIL import Image
import io
import base64
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template
import requests
from datetime import datetime
import re

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "llava:7b"
TEXT_MODEL = "llama3.2:1b"#llama3.2:latest
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mkv'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = 'multimodal-mcts-secret'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------- Helper functions ----------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_session_directory():
    session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
    session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
    os.makedirs(session_dir, exist_ok=True)
    return session_dir, session_id

def image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            max_size = 512
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            buffered = io.BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        print(f"Error converting image to base64: {e}")
        return None

def analyze_image_with_vision(image_path):
    try:
        img_base64 = image_to_base64(image_path)
        if not img_base64:
            return "Unable to process image"
        prompt = """Describe this image in detail. Include:
1. Main objects and subjects
2. Colors and visual elements
3. Any text visible in the image
4. Overall scene and context

Provide a comprehensive description:"""
        payload = {
            "model": VISION_MODEL,
            "prompt": prompt,
            "stream": False,
            "images": [img_base64]
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        description = response.json().get("response", "").strip()
        with Image.open(image_path) as img:
            basic_info = f"Image: {img.format} format, {img.size[0]}x{img.size[1]} pixels"
        return f"{basic_info}\n\nImage Content Analysis:\n{description}"
    except Exception as e:
        print(f"Error analyzing image with vision model: {e}")
        try:
            with Image.open(image_path) as img:
                return f"Image: {img.format} format, {img.size[0]}x{img.size[1]} pixels. Note: Detailed analysis failed."
        except:
            return "Image analysis failed"

def analyze_video_content(video_path):
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return "Cannot open video file"
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0

        key_frames = []
        frame_positions = [0, frame_count//2, frame_count-1] if frame_count > 2 else [0]
        for pos in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if ret:
                frame_path = f"temp_frame_{pos}.jpg"
                cv2.imwrite(frame_path, frame)
                frame_description = analyze_image_with_vision(frame_path)
                key_frames.append(f"Frame at {pos/fps:.1f}s: {frame_description}")
                if os.path.exists(frame_path):
                    os.remove(frame_path)
        cap.release()
        video_info = f"Video: {duration:.1f} seconds, {frame_count} frames, {width}x{height} resolution, {fps:.1f} fps"
        if key_frames:
            frames_desc = "\n".join(key_frames[:3])
            return f"{video_info}\n\nKey Frames Analysis:\n{frames_desc}"
        else:
            return video_info
    except Exception as e:
        print(f"Error analyzing video: {e}")
        return f"Video analysis failed: {str(e)}"

# ---------- Agent definitions ----------
class BaseAgent:
    def __init__(self, agent_id, name, description):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.agent_icon = "🤖"

    def build_multimodal_prompt(self, text, media_analyses):
        prompt_parts = []
        if text and text.strip():
            prompt_parts.append(f"TEXT CONTENT:\n{text}")
        if media_analyses:
            prompt_parts.append("MEDIA CONTENT ANALYSIS:")
            for i, analysis in enumerate(media_analyses, 1):
                prompt_parts.append(f"\n--- Media Item {i} ---\n{analysis}")
        agent_instruction = self.get_instruction()
        if media_analyses:
            agent_instruction += "\n\nPlease analyze BOTH the text content AND the media content described above."
        return f"{agent_instruction}\n\n{'='*50}\n" + "\n\n".join(prompt_parts) + f"\n{'='*50}\n\n{self.get_response_format()}"

    def get_instruction(self):
        raise NotImplementedError

    def get_response_format(self):
        return "Please provide your summary:"

    def get_system_prompt(self):
        return None

    def get_temperature(self):
        return 0.7

    def get_max_tokens(self):
        return 300

    def generate_summary(self, text, media_analyses=None):
        if not text and not media_analyses:
            return "No content provided for summarization"
        prompt = self.build_multimodal_prompt(text, media_analyses or [])
        system_prompt = self.get_system_prompt()

        print(f"   [Agent {self.agent_id}] Sending request to Ollama (model {TEXT_MODEL})...", flush=True)
        print(f"   Prompt preview: {prompt[:150]}...", flush=True)

        try:
            payload = {
                "model": TEXT_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": self.get_max_tokens(),
                    "temperature": self.get_temperature(),
                    "top_p": 0.9
                }
            }
            if system_prompt:
                payload["system"] = system_prompt
            response = requests.post(OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            result = result.replace("Summary:", "").replace("TL;DR:", "").replace("Key points:", "").strip()
            return result
        except requests.exceptions.Timeout:
            return "Error: Request timeout - the model took too long to respond"
        except requests.exceptions.ConnectionError:
            return "Error: Cannot connect to Ollama server. Make sure Ollama is running with llama3.2:1b model."
        except Exception as e:
            return f"Error: {str(e)}"

class ExtractiveAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id=1, name="📄 Extractive Agent", description="Extracts key information from all content types")
        self.agent_icon = "📄"
    def get_system_prompt(self):
        return """You are an expert extractive summarization agent for multimodal content. Your task is to extract the most important factual information from both text and media descriptions. Focus on concrete facts, key details, and specific information."""
    def get_instruction(self):
        return """Extract the 4-5 most important pieces of information from the provided content."""
    def get_response_format(self):
        return "Please list the extracted information as numbered points:"
    def get_temperature(self):
        return 0.3

class AbstractiveAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id=2, name="✨ Abstractive Agent", description="Summarizes content in own words concisely")
        self.agent_icon = "✨"
    def get_system_prompt(self):
        return """You are an expert abstractive summarization agent for multimodal content. Your task is to synthesize information from text and media descriptions, then rewrite it concisely in your own words while preserving all key information."""
    def get_instruction(self):
        return """Synthesize and summarize the provided content in your own words."""
    def get_response_format(self):
        return "Please provide a concise 2-3 sentence summary:"

class BulletAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id=3, name="📋 Bullet Points Agent", description="Creates key points as bullet points")
        self.agent_icon = "📋"
    def get_system_prompt(self):
        return """You are an expert at creating structured bullet point summaries from multimodal content. Your task is to extract key points from both text and media descriptions and present them as clear, organized bullet points."""
    def get_instruction(self):
        return """Extract the key points from the provided content."""
    def get_response_format(self):
        return "Please provide key points as bullet points (•):"
    def get_temperature(self):
        return 0.5

class TLDRAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id=4, name="⚡ TL;DR Agent", description="Creates extremely concise TL;DR summaries")
        self.agent_icon = "⚡"
    def get_system_prompt(self):
        return """You are a TL;DR (Too Long; Didn't Read) summarization expert for multimodal content. Your task is to create extremely concise summaries that capture the absolute essence from both text and media descriptions."""
    def get_instruction(self):
        return """Create a TL;DR summary of the provided content."""
    def get_response_format(self):
        return "TL;DR:"
    def get_max_tokens(self):
        return 150

class DetailedAgent(BaseAgent):
    def __init__(self):
        super().__init__(agent_id=5, name="📚 Detailed Agent", description="Creates comprehensive detailed summaries")
        self.agent_icon = "📚"
    def get_system_prompt(self):
        return """You are a comprehensive summarization agent for multimodal content. Your task is to create detailed summaries that cover all important aspects from both text and media descriptions."""
    def get_instruction(self):
        return """Create a comprehensive summary of the provided content."""
    def get_response_format(self):
        return "Comprehensive Summary:"
    def get_max_tokens(self):
        return 400

# ---------- Agent Registry ----------
class AgentRegistry:
    def __init__(self):
        self.agents = {}
        self.register_agents()
    def register_agents(self):
        agents = [ExtractiveAgent(), AbstractiveAgent(), BulletAgent(), TLDRAgent(), DetailedAgent()]
        for agent in agents:
            self.agents[agent.agent_id] = agent
    def get_agent(self, agent_id):
        return self.agents.get(agent_id)
    def get_all_agents(self):
        return list(self.agents.values())

agent_registry = AgentRegistry()

# ---------- Base MCTS Optimizer (with logging) ----------
class MCTSNode:
    def __init__(self, agent_id=None, parent=None):
        self.agent_id = agent_id
        self.parent = parent
        self.children = []
        self.visits = 0
        self.total_value = 0.0
        self.untried_agents = []

    @property
    def value(self):
        return self.total_value / self.visits if self.visits > 0 else 0.0

    def is_fully_expanded(self):
        return len(self.untried_agents) == 0

    def best_child(self, exploration_weight=1.414):
        best_score = -float('inf')
        best_child = None
        for child in self.children:
            if child.visits == 0:
                uct_score = float('inf')
            else:
                exploitation = child.value
                exploration = exploration_weight * math.sqrt(math.log(self.visits) / child.visits)
                uct_score = exploitation + exploration
            if uct_score > best_score:
                best_score = uct_score
                best_child = child
        return best_child

    def add_child(self, agent_id):
        child = MCTSNode(agent_id=agent_id, parent=self)
        self.children.append(child)
        return child

    def update(self, value):
        self.visits += 1
        self.total_value += value

class MCTSOptimizer:
    def __init__(self, agent_results, has_multimedia=False):
        self.agent_results = agent_results
        self.has_multimedia = has_multimedia
        self.root = MCTSNode()
        self.root.untried_agents = [r["agent_id"] for r in agent_results]
        self.evaluation_cache = {}

    def evaluate_summary(self, agent_id, summary):
        cache_key = f"{agent_id}:{hash(summary[:200])}"
        if cache_key in self.evaluation_cache:
            return self.evaluation_cache[cache_key]

        word_count = len(summary.split())
        base_scores = {1: 0.6, 2: 0.7, 3: 0.65, 4: 0.5, 5: 0.75}
        score = base_scores.get(agent_id, 0.6)

        if self.has_multimedia:
            if agent_id in [2, 5]:
                score += 0.2
            elif agent_id in [3]:
                score += 0.1

        if word_count < 15:
            score *= 0.7
        elif 40 <= word_count <= 200:
            score *= 1.2
        elif word_count > 300:
            score *= 0.8

        if self.has_multimedia:
            summary_lower = summary.lower()
            media_keywords = ['image', 'picture', 'photo', 'video', 'visual', 'graphic', 'screenshot']
            if any(keyword in summary_lower for keyword in media_keywords):
                score += 0.15

        score += random.uniform(-0.03, 0.03)
        score = max(0.1, min(0.95, score))
        self.evaluation_cache[cache_key] = score
        return score

    def search(self, iterations=50):
        print(f"\n🔍 Starting MCTS Search ({iterations} iterations)", flush=True)
        for i in range(iterations):
            node = self.root
            while not node.is_fully_expanded() and node.children:
                node = node.best_child()
            if node.untried_agents:
                agent_id = node.untried_agents.pop(random.randrange(len(node.untried_agents)))
                node = node.add_child(agent_id)
            if node.agent_id is None and node.untried_agents:
                agent_id = random.choice(node.untried_agents)
            else:
                agent_id = node.agent_id
            agent_result = next((r for r in self.agent_results if r["agent_id"] == agent_id), None)
            value = self.evaluate_summary(agent_id, agent_result["summary"]) if agent_result else 0.0
            current = node
            while current:
                current.update(value)
                current = current.parent

        if not self.root.children:
            return None, 0.0, {}
        best_child = max(self.root.children, key=lambda c: c.value if c.visits > 0 else 0)
        confidence = best_child.value
        agent_scores = {child.agent_id: round(child.value, 3) for child in self.root.children if child.visits > 0}
        return best_child.agent_id, confidence, agent_scores

    def search_with_log(self, iterations=50):
        log = []
        agent_name_map = {r["agent_id"]: r["agent_name"] for r in self.agent_results}
        print(f"\n🔍 Starting MCTS Search with logging ({iterations} iterations)", flush=True)
        for i in range(iterations):
            node = self.root
            # Selection: descend while node is fully expanded and has children
            while node.is_fully_expanded() and node.children:
                node = node.best_child()
            # Expansion: if node has untried agents, expand one
            if node.untried_agents:
                agent_id = node.untried_agents.pop(random.randrange(len(node.untried_agents)))
                node = node.add_child(agent_id)
            # Simulation: evaluate the agent at the current node
            agent_id = node.agent_id
            agent_result = next((r for r in self.agent_results if r["agent_id"] == agent_id), None)
            value = self.evaluate_summary(agent_id, agent_result["summary"]) if agent_result else 0.0
            agent_name = agent_name_map.get(agent_id, f"Agent {agent_id}")
            print(f"   [Step {i+1}] Agent '{agent_name}' evaluated. Reward: {value:.3f}", flush=True)
            log.append({"agent_id": agent_id, "value": value})
            # Backpropagation
            current = node
            while current:
                current.update(value)
                current = current.parent

        if not self.root.children:
            return None, 0.0, {}, log
        best_child = max(self.root.children, key=lambda c: c.value if c.visits > 0 else 0)
        confidence = best_child.value
        agent_scores = {child.agent_id: round(child.value, 3) for child in self.root.children if child.visits > 0}
        return best_child.agent_id, confidence, agent_scores, log

    def get_tree_structure(self):
        def node_to_dict(node):
            return {
                "agent_id": node.agent_id,
                "visits": node.visits,
                "value": round(node.value, 3) if node.visits > 0 else 0.0,
                "total_value": round(node.total_value, 3),
                "children": [node_to_dict(child) for child in node.children]
            }
        return node_to_dict(self.root)

# ---------- R-MCTS (Reflective) ----------
class ReflectiveMCTS(MCTSOptimizer):
    def __init__(self, agent_results, has_multimedia=False, source_text="", media_analyses=None):
        super().__init__(agent_results, has_multimedia)
        self.source_text = source_text
        self.media_analyses = media_analyses or []
        self.reflection_model = TEXT_MODEL

    def reflect_on_summary(self, summary):
        prompt = f"""You are a reflection agent. Compare the following summary with the original content.
Rate the summary on a scale 0.0 to 1.0 for:
- Faithfulness (does not contain information not in the source)
- Coherence
- Conciseness

Source text: {self.source_text[:500]}...
Media analyses: {self.media_analyses if self.media_analyses else 'None'}
Summary: {summary}

Return only a number between 0.0 and 1.0 representing the overall quality."""
        try:
            response = requests.post(OLLAMA_URL, json={
                "model": self.reflection_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 10}
            })
            score = float(response.json().get("response", "0.5").strip())
            return max(0.0, min(1.0, score))
        except:
            return 0.5

    def evaluate_summary(self, agent_id, summary):
        base_score = super().evaluate_summary(agent_id, summary)
        if self.has_multimedia:
            reflection_score = self.reflect_on_summary(summary)
            return (base_score + reflection_score) / 2
        return base_score

# ---------- MCTS-RAG (Retrieval-Augmented) ----------
try:
    from sentence_transformers import SentenceTransformer, util
    _encoder_available = True
except ImportError:
    _encoder_available = False
    # Suppress warning – uncomment the next line if you want to see it
    # print("Warning: sentence-transformers not installed. RAG will use fallback.")

class RAGMCTS(MCTSOptimizer):
    def __init__(self, agent_results, has_multimedia=False, knowledge_base=None):
        super().__init__(agent_results, has_multimedia)
        self.knowledge_base = knowledge_base or [
            "Artificial intelligence is the simulation of human intelligence in machines.",
            "Machine learning is a subset of AI that enables systems to learn from data.",
            "Deep learning uses neural networks with many layers.",
            "Natural language processing deals with interactions between computers and human language."
        ]
        if _encoder_available:
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
            self.kb_embeddings = self.encoder.encode(self.knowledge_base, convert_to_tensor=True)
        else:
            self.encoder = None

    def retrieve_relevance(self, summary):
        if self.encoder is None:
            summary_lower = summary.lower()
            matches = sum(1 for doc in self.knowledge_base if any(word in summary_lower for word in doc.lower().split()))
            return min(1.0, matches / len(self.knowledge_base))
        summary_emb = self.encoder.encode(summary, convert_to_tensor=True)
        scores = util.cos_sim(summary_emb, self.kb_embeddings)[0]
        return float(scores.max())

    def evaluate_summary(self, agent_id, summary):
        base_score = super().evaluate_summary(agent_id, summary)
        if self.has_multimedia:
            rag_score = self.retrieve_relevance(summary)
            return 0.7 * base_score + 0.3 * rag_score
        return base_score

# ---------- World-Guided MCTS ----------
class WorldGuidedMCTS(MCTSOptimizer):
    def __init__(self, agent_results, has_multimedia=False, world_knowledge=None):
        super().__init__(agent_results, has_multimedia)
        self.world_knowledge = world_knowledge or ["AI", "machine learning", "data", "neural network", "algorithm"]

    def world_alignment_score(self, summary):
        summary_lower = summary.lower()
        matches = sum(1 for term in self.world_knowledge if term.lower() in summary_lower)
        return min(1.0, matches / len(self.world_knowledge))

    def evaluate_summary(self, agent_id, summary):
        base_score = super().evaluate_summary(agent_id, summary)
        if self.has_multimedia:
            world_score = self.world_alignment_score(summary)
            return 0.8 * base_score + 0.2 * world_score
        return base_score

# ---------- Metric functions (for evaluation) ----------
def tokenize(text):
    text = re.sub(r'[^\w\s]', '', text.lower())
    return set(text.split())

def compute_metrics(reference, hypothesis):
    ref_tokens = tokenize(reference)
    hyp_tokens = tokenize(hypothesis)
    intersection = ref_tokens & hyp_tokens
    precision = len(intersection) / len(hyp_tokens) if hyp_tokens else 0
    recall = len(intersection) / len(ref_tokens) if ref_tokens else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision+recall) > 0 else 0
    accuracy = len(intersection) / len(ref_tokens | hyp_tokens) if (ref_tokens | hyp_tokens) else 0
    return precision, recall, f1, accuracy

# ---------- Flask Routes ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/explore")
def explore():
    return render_template("explore.html")

@app.route("/health")
def health():
    try:
        response = requests.get("http://localhost:11435/api/tags", timeout=5)
        ollama_status = "connected" if response.status_code == 200 else "error"
        models_response = requests.get("http://localhost:11435/api/tags", timeout=5)
        models_text = models_response.text if models_response.status_code == 200 else ""
        has_llama = TEXT_MODEL in models_text
        has_llava = VISION_MODEL in models_text
    except:
        ollama_status = "not_connected"
        has_llama = False
        has_llava = False
    agents = agent_registry.get_all_agents()
    return jsonify({
        "status": "ok",
        "ollama": ollama_status,
        "text_model_available": has_llama,
        "vision_model_available": has_llava,
        "text_model": TEXT_MODEL,
        "vision_model": VISION_MODEL,
        "agents_count": len(agents),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/upload", methods=["POST"])
def upload_files():
    text = request.form.get("text", "")
    session_dir, session_id = create_session_directory()
    video_analysis = None
    image_analyses = []
    if 'video' in request.files:
        video_file = request.files['video']
        if video_file and video_file.filename != '' and allowed_file(video_file.filename):
            video_filename = secure_filename(f"video_{session_id}_{video_file.filename}")
            video_path = os.path.join(session_dir, video_filename)
            video_file.save(video_path)
            video_analysis = analyze_video_content(video_path)
    if 'images' in request.files:
        image_files = request.files.getlist('images')
        for i, img_file in enumerate(image_files):
            if img_file and img_file.filename != '' and allowed_file(img_file.filename):
                img_filename = secure_filename(f"image_{session_id}_{i}_{img_file.filename}")
                img_path = os.path.join(session_dir, img_filename)
                img_file.save(img_path)
                img_analysis = analyze_image_with_vision(img_path)
                image_analyses.append(img_analysis)
    media_analyses = []
    if video_analysis:
        media_analyses.append(video_analysis)
    media_analyses.extend(image_analyses)
    return jsonify({
        "success": True,
        "session_id": session_id,
        "session_dir": session_dir,
        "text": text,
        "media_analyses": media_analyses,
        "has_video": video_analysis is not None,
        "has_images": len(image_analyses) > 0,
        "total_media": len(media_analyses),
        "message": f"Upload complete. Processed {len(text)} chars of text and {len(media_analyses)} media items."
    })

@app.route("/summarize_multimodal", methods=["POST"])
def summarize_multimodal():
    data = request.json
    text = data.get("text", "")
    media_analyses = data.get("media_analyses", [])
    agent_results = []
    agents = agent_registry.get_all_agents()
    has_multimedia = len(media_analyses) > 0
    for agent in agents:
        print(f"\n🤖 Running {agent.name} (ID: {agent.agent_id})...", flush=True)
        start_time = time.time()
        try:
            summary = agent.generate_summary(text, media_analyses)
            duration = round((time.time() - start_time) * 1000)
            word_count = len(summary.split())
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "agent_icon": agent.agent_icon,
                "summary": summary,
                "duration": duration,
                "has_multimedia": has_multimedia,
                "word_count": word_count,
                "char_count": len(summary),
                "words_per_second": round(word_count / (duration / 1000), 1) if duration > 0 else 0
            })
            print(f"   ✅ Agent {agent.agent_id} complete:", flush=True)
            print(f"      Summary: {word_count} words, {len(summary)} chars", flush=True)
            print(f"      Duration: {duration}ms ({agent_results[-1]['words_per_second']} words/sec)", flush=True)
            print(f"      Preview: {summary[:100]}..." if len(summary) > 100 else f"      Summary: {summary}", flush=True)
        except Exception as e:
            print(f"   ❌ Agent {agent.agent_id} failed: {str(e)}", flush=True)
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": f"Error: {str(e)}",
                "duration": 0,
                "error": True,
                "has_multimedia": has_multimedia
            })
    successful = len([r for r in agent_results if not r.get("error", False)])
    return jsonify({
        "agent_results": agent_results,
        "has_multimedia": has_multimedia,
        "total_agents": len(agents),
        "successful_agents": successful,
        "total_media_items": len(media_analyses)
    })

@app.route("/summarize_simple", methods=["POST"])
def summarize_simple():
    """Run all agents, evaluate each summary, and return the best one (no MCTS tree search)."""
    print("\n>>> SIMPLE SUMMARIZATION CALLED (running all agents, scoring each)", flush=True)
    data = request.json
    text = data.get("text", "")
    media_analyses = data.get("media_analyses", [])
    has_multimedia = len(media_analyses) > 0

    agents = agent_registry.get_all_agents()
    agent_results = []

    def evaluate_summary(agent_id, summary):
        word_count = len(summary.split())
        base_scores = {1: 0.6, 2: 0.7, 3: 0.65, 4: 0.5, 5: 0.75}
        score = base_scores.get(agent_id, 0.6)

        if has_multimedia:
            if agent_id in [2, 5]:
                score += 0.2
            elif agent_id in [3]:
                score += 0.1

        if word_count < 15:
            score *= 0.7
        elif 40 <= word_count <= 200:
            score *= 1.2
        elif word_count > 300:
            score *= 0.8

        if has_multimedia:
            summary_lower = summary.lower()
            media_keywords = ['image', 'picture', 'photo', 'video', 'visual', 'graphic', 'screenshot']
            if any(keyword in summary_lower for keyword in media_keywords):
                score += 0.15

        score += random.uniform(-0.03, 0.03)
        score = max(0.1, min(0.95, score))
        return score

    for agent in agents:
        print(f"\n🤖 Running {agent.name} (ID: {agent.agent_id})...", flush=True)
        start_time = time.time()
        try:
            summary = agent.generate_summary(text, media_analyses)
            duration = round((time.time() - start_time) * 1000)
            word_count = len(summary.split())
            score = evaluate_summary(agent.agent_id, summary)
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": summary,
                "duration": duration,
                "word_count": word_count,
                "char_count": len(summary),
                "score": score,
                "success": True
            })
            print(f"   ✅ Agent {agent.agent_id} complete:", flush=True)
            print(f"      Summary: {word_count} words, {len(summary)} chars", flush=True)
            print(f"      Score: {score:.3f}", flush=True)
            print(f"      Duration: {duration}ms", flush=True)
            print(f"      Preview: {summary[:100]}..." if len(summary) > 100 else f"      Summary: {summary}", flush=True)
        except Exception as e:
            print(f"   ❌ Agent {agent.agent_id} failed: {str(e)}", flush=True)
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": f"Error: {str(e)}",
                "success": False,
                "error": str(e)
            })

    successful = [r for r in agent_results if r.get("success")]
    if not successful:
        return jsonify({
            "summary": "All agents failed to generate a summary.",
            "agent_name": "None",
            "confidence": 0,
            "agent_id": None
        })

    best = max(successful, key=lambda r: r["score"])
    confidence_pct = round(best["score"] * 100)

    print(f"\n🏆 Best agent: {best['agent_name']} with score {best['score']:.3f} ({confidence_pct}%)", flush=True)

    return jsonify({
        "summary": best["summary"],
        "agent_name": best["agent_name"],
        "confidence": confidence_pct,
        "agent_id": best["agent_id"]
    })

@app.route("/mcts_optimize", methods=["POST"])
def mcts_optimize():
    data = request.json
    agent_results = data.get("agent_results", [])
    has_multimedia = data.get("has_multimedia", False)
    simulations = data.get("simulations", 50)
    use_reflection = data.get("use_reflection", False)
    use_rag = data.get("use_rag", False)
    use_world = data.get("use_world", False)
    original_text = data.get("original_text", "")
    media_analyses = data.get("media_analyses", [])

    valid_results = [r for r in agent_results if not r.get("error", False)]
    if not valid_results:
        return jsonify({
            "error": "No valid agent results to optimize",
            "winning_agent": None,
            "winning_summary": "All agents failed to generate summaries",
            "confidence": 0.0,
            "agent_scores": {},
            "simulations_run": 0
        })

    if use_reflection:
        mcts = ReflectiveMCTS(valid_results, has_multimedia, original_text, media_analyses)
    elif use_rag:
        knowledge_base = [
            "Artificial intelligence is the simulation of human intelligence in machines.",
            "Machine learning is a subset of AI that enables systems to learn from data.",
            "Deep learning uses neural networks with many layers.",
            "Natural language processing deals with interactions between computers and human language."
        ]
        mcts = RAGMCTS(valid_results, has_multimedia, knowledge_base)
    elif use_world:
        world_knowledge = ["AI", "machine learning", "data", "neural network", "algorithm", "computer vision"]
        mcts = WorldGuidedMCTS(valid_results, has_multimedia, world_knowledge)
    else:
        mcts = MCTSOptimizer(valid_results, has_multimedia)

    winning_agent, confidence, agent_scores = mcts.search(iterations=simulations)
    tree_structure = mcts.get_tree_structure()
    winning_summary = None
    for result in valid_results:
        if result["agent_id"] == winning_agent:
            winning_summary = result["summary"]
            break

    return jsonify({
        "winning_agent": winning_agent,
        "winning_summary": winning_summary,
        "confidence": confidence,
        "agent_scores": agent_scores,
        "tree_structure": tree_structure,
        "simulations_run": simulations,
        "has_multimedia": has_multimedia
    })

@app.route("/compare_variants", methods=["POST"])
def compare_variants():
    data = request.json
    text = data.get("text", "")
    media_analyses = data.get("media_analyses", [])
    simulations = data.get("simulations", 50)

    agents = agent_registry.get_all_agents()
    agent_results = []
    has_multimedia = len(media_analyses) > 0
    for agent in agents:
        try:
            summary = agent.generate_summary(text, media_analyses)
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": summary,
                "has_multimedia": has_multimedia
            })
        except Exception as e:
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": f"Error: {str(e)}",
                "error": True,
                "has_multimedia": has_multimedia
            })

    valid_results = [r for r in agent_results if not r.get("error", False)]

    variants = [
        ("Baseline", False, False, False),
        ("Reflective", True, False, False),
        ("RAG", False, True, False),
        ("World-Guided", False, False, True)
    ]

    comparison_results = []
    for name, refl, rag, world in variants:
        if refl:
            mcts = ReflectiveMCTS(valid_results, has_multimedia, text, media_analyses)
        elif rag:
            kb = [
                "Artificial intelligence is the simulation of human intelligence in machines.",
                "Machine learning is a subset of AI that enables systems to learn from data.",
                "Deep learning uses neural networks with many layers.",
                "Natural language processing deals with interactions between computers and human language."
            ]
            mcts = RAGMCTS(valid_results, has_multimedia, kb)
        elif world:
            wk = ["AI", "machine learning", "data", "neural network", "algorithm", "computer vision"]
            mcts = WorldGuidedMCTS(valid_results, has_multimedia, wk)
        else:
            mcts = MCTSOptimizer(valid_results, has_multimedia)

        win_agent, conf, scores = mcts.search(iterations=simulations)
        win_summary = next((r["summary"] for r in valid_results if r["agent_id"] == win_agent), "")
        comparison_results.append({
            "variant": name,
            "winning_agent": win_agent,
            "confidence": round(conf, 3),
            "winning_summary": win_summary[:200] + "..." if len(win_summary) > 200 else win_summary
        })

    return jsonify(comparison_results)

@app.route("/reasoning_explore", methods=["POST"])
def reasoning_explore():
    data = request.json
    question = data.get("question", "")
    media_analyses = data.get("media_analyses", [])
    iterations = data.get("iterations", 10)
    variant = data.get("variant", "baseline")

    combined_text = question
    if media_analyses:
        combined_text += "\n\nAdditional context:\n" + "\n".join(media_analyses)

    agents = agent_registry.get_all_agents()
    agent_results = []
    for agent in agents:
        try:
            summary = agent.generate_summary(combined_text, media_analyses)
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": summary
            })
        except Exception as e:
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": f"Error: {str(e)}",
                "error": True
            })

    valid_results = [r for r in agent_results if not r.get("error", False)]

    has_multimedia = len(media_analyses) > 0

    print("\n📊 Initial agent scores (heuristic):")
    temp_mcts = MCTSOptimizer(valid_results, has_multimedia)
    for res in valid_results:
        score = temp_mcts.evaluate_summary(res["agent_id"], res["summary"])
        print(f"   {res['agent_name']}: {score:.3f}")

    if variant == "reflective":
        mcts = ReflectiveMCTS(valid_results, has_multimedia, question, media_analyses)
    elif variant == "rag":
        kb = [
            "Artificial intelligence is the simulation of human intelligence in machines.",
            "Machine learning is a subset of AI that enables systems to learn from data.",
            "Deep learning uses neural networks with many layers.",
            "Natural language processing deals with interactions between computers and human language."
        ]
        mcts = RAGMCTS(valid_results, has_multimedia, kb)
    elif variant == "world":
        wk = ["AI", "machine learning", "data", "neural network", "algorithm", "computer vision"]
        mcts = WorldGuidedMCTS(valid_results, has_multimedia, wk)
    else:
        mcts = MCTSOptimizer(valid_results, has_multimedia)

    winning_agent, confidence, agent_scores, log = mcts.search_with_log(iterations)

    tree = mcts.get_tree_structure()
    nodes = count_nodes(tree)
    depth = max_depth(tree)
    tree_value = tree.get("value", 0.0)

    winning_summary = next((r["summary"] for r in valid_results if r["agent_id"] == winning_agent), "")

    agent_name_map = {r["agent_id"]: r["agent_name"] for r in valid_results}
    optimal_path_ids = extract_path(tree, winning_agent)
    optimal_path = [agent_name_map.get(aid, f"Agent {aid}") for aid in optimal_path_ids if aid is not None]

    reasoning_log = []
    for i, step in enumerate(log):
        agent_name = agent_name_map.get(step["agent_id"], f"Agent {step['agent_id']}")
        reasoning_log.append({
            "step": i+1,
            "agent_name": agent_name,
            "reward": step["value"]
        })

    winning_agent_name = agent_name_map.get(winning_agent, f"Agent {winning_agent}")
    confidence_pct = int(confidence * 100)
    print(f"\n🏆 Best agent: {winning_agent_name} with score {confidence:.3f} ({confidence_pct}%)", flush=True)

    return jsonify({
        "iterations": iterations,
        "nodes": nodes,
        "depth": depth,
        "tree_value": tree_value,
        "reasoning_log": reasoning_log,
        "optimal_path": optimal_path,
        "final_answer": winning_summary,
        "confidence": confidence
    })

@app.route("/evaluate_with_reference", methods=["POST"])
def evaluate_with_reference():
    data = request.json
    text = data.get("text", "")
    media_analyses = data.get("media_analyses", [])
    simulations = data.get("simulations", 50)
    reference = data.get("reference", "").strip()

    if not reference:
        return jsonify({"error": "Reference summary is required"}), 400

    agents = agent_registry.get_all_agents()
    agent_results = []
    has_multimedia = len(media_analyses) > 0
    for agent in agents:
        try:
            summary = agent.generate_summary(text, media_analyses)
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": summary,
                "has_multimedia": has_multimedia
            })
        except Exception as e:
            agent_results.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.name,
                "summary": f"Error: {str(e)}",
                "error": True,
                "has_multimedia": has_multimedia
            })

    valid_results = [r for r in agent_results if not r.get("error", False)]

    variants = [
        ("Baseline", False, False, False),
        ("Reflective", True, False, False),
        ("RAG", False, True, False),
        ("World-Guided", False, False, True)
    ]

    print("\n" + "="*60)
    print("📊 EVALUATION WITH REFERENCE")
    print("="*60)
    print(f"Input text: {text[:100]}...")
    print(f"Reference: {reference}")
    print(f"Simulations: {simulations}")
    print("-"*60)

    for name, refl, rag, world in variants:
        if refl:
            mcts = ReflectiveMCTS(valid_results, has_multimedia, text, media_analyses)
        elif rag:
            kb = [
                "Artificial intelligence is the simulation of human intelligence in machines.",
                "Machine learning is a subset of AI that enables systems to learn from data.",
                "Deep learning uses neural networks with many layers.",
                "Natural language processing deals with interactions between computers and human language."
            ]
            mcts = RAGMCTS(valid_results, has_multimedia, kb)
        elif world:
            wk = ["AI", "machine learning", "data", "neural network", "algorithm", "computer vision"]
            mcts = WorldGuidedMCTS(valid_results, has_multimedia, wk)
        else:
            mcts = MCTSOptimizer(valid_results, has_multimedia)

        win_agent, conf, _ = mcts.search(iterations=simulations)
        win_summary = next((r["summary"] for r in valid_results if r["agent_id"] == win_agent), "")

        prec, rec, f1, acc = compute_metrics(reference, win_summary)

        print(f"\n🔹 {name}")
        print(f"   Winning Agent: {win_agent}")
        print(f"   Confidence: {conf:.3f}")
        print(f"   Precision: {prec:.3f}")
        print(f"   Recall: {rec:.3f}")
        print(f"   F1: {f1:.3f}")
        print(f"   Accuracy: {acc:.3f}")
        print(f"   Summary: {win_summary[:150]}...")

    print("="*60 + "\n")

    return jsonify({"status": "ok", "message": "Metrics printed in terminal"})

@app.route("/cleanup_session", methods=["POST"])
def cleanup_session():
    data = request.json
    session_id = data.get("session_id")
    if session_id:
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], session_id)
        if os.path.exists(session_dir):
            try:
                import shutil
                shutil.rmtree(session_dir)
                return jsonify({"success": True, "message": f"Session {session_id} cleaned up"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)})
    return jsonify({"success": False, "error": "No session ID provided"})

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "message": str(e)}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error", "message": str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large", "message": "Maximum file size is 50MB"}), 413

def count_nodes(node):
    if not node:
        return 0
    cnt = 1
    for child in node.get("children", []):
        cnt += count_nodes(child)
    return cnt

def max_depth(node):
    if not node or not node.get("children"):
        return 0
    return 1 + max((max_depth(child) for child in node["children"]), default=0)

def extract_path(node, target_agent):
    if node.get("agent_id") == target_agent:
        return [target_agent]
    for child in node.get("children", []):
        path = extract_path(child, target_agent)
        if path:
            return [node["agent_id"]] + path if node["agent_id"] else path
    return []

if __name__ == "__main__":
    # Minimal startup message
    print("============================================================")
    print("🚀 Server starting on http://localhost:5007")
    print("============================================================")
    # Disable debug mode to avoid auto‑reloader and debugger messages
    app.run(host="0.0.0.0", port=5007, debug=False)