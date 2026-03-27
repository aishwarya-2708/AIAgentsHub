import os, shutil, json, math, random, time, sys
from flask import Flask, render_template, request, Response, stream_with_context

print("Starting app...")
print("Initializing models...")

# --- Windows Compatibility Patch ---
if sys.platform == "win32":
    import types
    sys.modules['pwd'] = types.ModuleType('pwd')
    sys.modules['pwd'].getpwuid = lambda x: types.SimpleNamespace(pw_name='user')

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama, OllamaEmbeddings

app = Flask(__name__)
app.secret_key = "mcts_research_secret_2026"

# --- Paths ---
TEMP_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "homework_helper")
PDF_PATH = os.path.join(TEMP_DIR, "notes.pdf")
DB_PATH = os.path.join(TEMP_DIR, "faiss_db")
os.makedirs(TEMP_DIR, exist_ok=True)

# --- Model Initialization ---
try:
    llm = ChatOllama(model="llama3.2:1b", temperature=0)
    embeddings_model = OllamaEmbeddings(model="llama3.2:1b")#nomic-embed-text
except Exception as e:
    print(f"Model Error: {e}")
    sys.exit(1)

# --- RAG Logic ---
def load_notes(pdf_file_path):
    from pypdf import PdfReader
    reader = PdfReader(pdf_file_path)
    full_text = "".join([p.extract_text() or "" for p in reader.pages])
    chunks = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=120).split_documents(
        [Document(page_content=full_text)]
    )
    if os.path.exists(DB_PATH): shutil.rmtree(DB_PATH)
    db = FAISS.from_documents(chunks, embeddings_model)
    db.save_local(DB_PATH)

def get_retriever():
    if os.path.exists(DB_PATH):
        return FAISS.load_local(DB_PATH, embeddings_model, allow_dangerous_deserialization=True).as_retriever()
    return None

def homework_helper(query, retriever=None):
    context = ""
    if retriever:
        docs = retriever.invoke(query)
        context = "\n---\n".join([d.page_content for d in docs])
    prompt = f"Context: {context}\n\nQuestion: {query}\nAnswer professionally:"
    return llm.invoke(prompt).content

# --- MCTS Node ---
class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state, self.parent, self.action = state, parent, action
        self.children, self.visits, self.value = [], 0, 0.0
        self.untried_actions = ["PDF Lookup", "Logic Check", "Summarize Evidence", "Simplify Concept", "Cross-Reference"]

    def ucb1(self):
        if self.visits == 0: return float('inf')
        return (self.value / self.visits) + 1.414 * math.sqrt(math.log(self.parent.visits) / self.visits)

# --- MCTS Tree ---
class MCTSTree:
    def __init__(self, question, retriever=None, variation="Standard"):
        self.root = MCTSNode(question)
        self.question = question
        self.retriever = retriever
        self.variation = variation
        self.total_nodes = 1

    def select(self):
        """Select node to expand using UCB1"""
        node = self.root
        while node.children:
            if node.untried_actions:
                # Some actions still untried at this node
                return node
            # Choose child with max UCB1
            node = max(node.children, key=lambda c: c.ucb1())
        return node

    def compute_reward(self, answer, node_action):
        """Compute dynamic reward with optional tiny randomness"""
        reward = 0.1
        content = answer.lower()
        keywords = [w for w in self.question.lower().split() if len(w) > 3]
        matches = sum(1 for k in keywords if k in content)

        if node_action == "PDF Lookup":
            reward = 0.3 + matches * 0.05
        elif node_action == "Logic Check":
            logic_words = ["because", "therefore", "however", "instead", "consequently", "difference"]
            logic_matches = sum(1 for w in logic_words if w in content)
            reward = 0.2 + 0.1 * logic_matches
        elif node_action == "Summarize Evidence":
            reward = 0.1 + len(content)/2000
        elif node_action == "Cross-Reference":
            reward = 0.4 if matches > 2 else 0.1

        # Add tiny random noise for exploration (can remove if not needed)
        reward += random.uniform(-0.02, 0.02)

        # Clamp to 0-1
        return min(max(round(reward, 2), 0.0), 1.0)

    def expand(self, node):
        """Expand by randomly picking an untried action"""
        if not node.untried_actions:
            return node
        action = random.choice(node.untried_actions)
        node.untried_actions.remove(action)
        child = MCTSNode(f"{node.state} -> {action}", parent=node, action=action)
        node.children.append(child)
        self.total_nodes += 1
        return child

    def search(self):
        # --- Selection ---
        node = self.select()

        # --- Expansion ---
        node = self.expand(node)

        # --- Answer generation ---
        retriever_context = ""
        if self.retriever:
            docs = self.retriever.invoke(f"{self.question} {node.action}")
            retriever_context = "\n---\n".join([d.page_content for d in docs])
        prompt = f"Context: {retriever_context}\n\nQuestion: {self.question}\nUse strategy: {node.action}\nAnswer:"
        answer = llm.invoke(prompt).content

        # --- Reward ---
        reward = self.compute_reward(answer, node.action)
        thought = f"Strategy '{node.action}' evaluated. Reward: {reward}"

        # --- Reflexive step for R-MCTS ---
        if self.variation == "R-MCTS":
            reflex_prompt = f"Review the previous answer and improve it if needed:\n{answer}"
            improved_answer = llm.invoke(reflex_prompt).content
            reward = max(reward, self.compute_reward(improved_answer, node.action))
            answer = improved_answer
            thought += " | Reflexive evaluation done"

        # --- World Guided MCTS could add ground-truth overlap here if needed ---
        # (currently optional; can be plugged in)

        # --- Backpropagation ---
        curr = node
        while curr:
            curr.visits += 1
            curr.value += reward
            curr = curr.parent

        return thought, answer

    def get_best_path(self):
        path, curr = [], self.root
        while curr.children:
            curr = max(curr.children, key=lambda c: c.visits)
            path.append(curr.action)
        return path

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    question = request.form.get("question")
    pdf_file = request.files.get("notes")
    if pdf_file and pdf_file.filename:
        pdf_file.save(PDF_PATH)
        load_notes(PDF_PATH)
    retriever = get_retriever()
    ans = homework_helper(question, retriever)
    return render_template("index.html", question=question, answer=ans)

@app.route("/mcts", methods=["GET"])
def mcts_ui():
    return render_template("mcts.html")

@app.route("/mcts/explore", methods=["POST"])
def mcts_explore():
    data = request.get_json()
    question = data.get("question")
    max_iters = int(data.get("max_iterations", 15))
    variation = data.get("variation", "Standard")
    retriever = get_retriever()

    def generate():
        tree = MCTSTree(question, retriever, variation=variation)
        for i in range(max_iters):
            thought, ans = tree.search()
            yield f"data: {json.dumps({
                'iteration': i + 1,
                'thought': thought,
                'nodes_explored': tree.total_nodes,
                'tree_depth': min(i, 4),
                'root_value': tree.root.value / (i + 1)
            })}\n\n"
            time.sleep(0.15)

        best_path = tree.get_best_path()
        final_ans = ans
        yield f"data: {json.dumps({
            'done': True,
            'summary': final_ans,
            'best_solution_path': best_path
        })}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True)