// popup.js
const API_URL = "http://localhost:8000";

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────
let selectedVariant = "basic-mcts";
let attachmentData  = null;   // base64 string
let attachmentName  = null;   // original filename

const VARIANT_INFO = {
  "basic-mcts": {
    desc:  "Standard MCTS — UCB1 selection, random rollout, heuristic scoring. Baseline variant — no retrieval or LLM.",
    color: "#f7c94f",
  },
  "r-mcts": {
    desc:  "Retrieval MCTS — live web retrieval per node during expansion. Action selection grounded in freshly fetched content.",
    color: "#4f8ef7",
  },
  "wm-mcts": {
    desc:  "World-Model MCTS — heuristic world model guides expansion. Fast and accurate planning.",
    color: "#7c5cfc",
  },
  "rag-mcts": {
    desc:  "MCTS-RAG — seeds context from Wikipedia before search. Context-aware planning with retrieval bonus.",
    color: "#00d4aa",
  },
};

const VARIANT_CSS = {
  "Basic-MCTS": "basic-mcts",
  "R-MCTS":     "r-mcts",
  "WM-MCTS":    "wm-mcts",
  "MCTS-RAG":   "rag-mcts",
};

const VARIANT_NAME_CSS = {
  "Basic-MCTS": "v-basic",
  "R-MCTS":     "v-r",
  "WM-MCTS":    "v-wm",
  "MCTS-RAG":   "v-rag",
};

// ─────────────────────────────────────────────
// Variant pills
// ─────────────────────────────────────────────
document.querySelectorAll(".variant-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".variant-pill").forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");
    selectedVariant = pill.dataset.variant;
    const info   = VARIANT_INFO[selectedVariant];
    const descEl = document.getElementById("variant-desc");
    descEl.textContent           = info.desc;
    descEl.style.borderLeftColor = info.color;
  });
});

// ─────────────────────────────────────────────
// Simulations slider
// ─────────────────────────────────────────────
const simSlider  = document.getElementById("simulations");
const simDisplay = document.getElementById("sim-display");
simSlider.addEventListener("input", () => { simDisplay.textContent = simSlider.value; });

// ─────────────────────────────────────────────
// File attachment handler
// ─────────────────────────────────────────────
const attachInput  = document.getElementById("attachment-input");
const fileInfoDiv  = document.getElementById("file-selected-info");
const fileNameSpan = document.getElementById("file-selected-name");
const fileClearBtn = document.getElementById("file-clear-btn");
const uploadPrompt = document.getElementById("upload-prompt");

if (attachInput) {
  attachInput.addEventListener("change", () => {
    const file = attachInput.files[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      alert("File too large. Maximum attachment size is 10 MB.");
      attachInput.value = "";
      return;
    }

    attachmentName = file.name;
    const reader   = new FileReader();
    reader.onload  = (e) => {
      attachmentData           = e.target.result.split(",")[1];
      fileNameSpan.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      fileInfoDiv.classList.add("visible");
      uploadPrompt.textContent = "File attached ✓";
    };
    reader.readAsDataURL(file);
  });

  fileClearBtn.addEventListener("click", () => {
    attachmentData = null;
    attachmentName = null;
    attachInput.value = "";
    fileInfoDiv.classList.remove("visible");
    uploadPrompt.textContent = "Click to attach a file (PDF, image, doc, zip, etc.)";
  });
}

// ─────────────────────────────────────────────
// Action selector — show/hide sections
// ─────────────────────────────────────────────
document.getElementById("action-type").addEventListener("change", (e) => {
  document.querySelectorAll(".action-section").forEach((s) => s.classList.remove("active"));
  const map = {
    "chat":          "chat-section",
    "price-compare": "price-compare-section",
    "scrape-data":   "scrape-data-section",
    "send-email":    "send-email-section",
    "fetch-email":   "fetch-email-section",
  };
  const sid = map[e.target.value];
  if (sid) document.getElementById(sid).classList.add("active");
  hideResultPanel();
});

// ─────────────────────────────────────────────
// Result panel tabs
// ─────────────────────────────────────────────
document.querySelectorAll(".result-tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".result-tab").forEach((t)  => t.classList.remove("active"));
    document.querySelectorAll(".result-pane").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    document.getElementById(`pane-${tab.dataset.tab}`).classList.add("active");
  });
});

function showResultPanel(tab = "output") {
  document.getElementById("result-panel").style.display = "block";
  document.querySelectorAll(".result-tab").forEach((t) => {
    t.classList.toggle("active", t.dataset.tab === tab);
  });
  document.querySelectorAll(".result-pane").forEach((p) => {
    p.classList.toggle("active", p.id === `pane-${tab}`);
  });
}

function hideResultPanel() {
  document.getElementById("result-panel").style.display = "none";
}

// ─────────────────────────────────────────────
// Connection check
// ─────────────────────────────────────────────
async function checkConnection() {
  const el = document.getElementById("status");
  try {
    const res = await fetch(`${API_URL}/health`);
    if (res.ok) {
      el.textContent = "Connected";
      el.className   = "status-badge connected";
    } else {
      el.textContent = "Backend Error";
      el.className   = "status-badge disconnected";
    }
  } catch {
    el.textContent = "Offline";
    el.className   = "status-badge disconnected";
  }
}
checkConnection();
setInterval(checkConnection, 10000);

// ─────────────────────────────────────────────
// Execute button
// ─────────────────────────────────────────────
document.getElementById("execute-btn").addEventListener("click", async () => {
  const actionType = document.getElementById("action-type").value;
  const resultDiv  = document.getElementById("result");
  const execBtn    = document.getElementById("execute-btn");
  const analBtn    = document.getElementById("analyse-btn");

  execBtn.disabled    = true;
  execBtn.textContent = "Processing...";
  analBtn.disabled    = true;

  resultDiv.textContent = "Working...";
  showResultPanel("output");

  try {
    if      (actionType === "chat")          await handleChatQuery(resultDiv);
    else if (actionType === "price-compare") await handlePriceCompare(resultDiv);
    else if (actionType === "scrape-data")   await handleScrapeData(resultDiv);
    else if (actionType === "send-email")    await handleSendEmail(resultDiv);
    else if (actionType === "fetch-email")   await handleFetchEmails(resultDiv);
  } catch (err) {
    resultDiv.textContent = `Error: ${err.message}`;
  } finally {
    execBtn.disabled    = false;
    execBtn.textContent = "▶ Execute";
    analBtn.disabled    = false;
  }
});

// ─────────────────────────────────────────────
// Analyse button
// Runs all 4 MCTS variants on the chat query,
// shows TSR accuracy, speed, step efficiency.
//
// Accuracy: Task Success Rate (TSR)
//   TSR (%) = (plan_score / 10.0) × 100
//   Standard metric — AgentBench / WebArena /
//   ALFWorld agentic task benchmarks.
// ─────────────────────────────────────────────
document.getElementById("analyse-btn").addEventListener("click", async () => {

  // ── Collect inputs for the CURRENT action ─────────────────────
  const actionType = document.getElementById("action-type").value;
  let   actionInputs = {};
  let   validationError = null;

  if (actionType === "chat") {
    const task = document.getElementById("task").value.trim();
    if (!task) validationError = "Please enter a query in the chat box first.";
    else actionInputs = { query: task };

  } else if (actionType === "price-compare") {
    const product = document.getElementById("price-product").value.trim();
    if (!product) validationError = "Please enter a product name in the Price Compare section.";
    else actionInputs = {
      product:      product,
      official_url: document.getElementById("price-official-url").value.trim() || "",
    };

  } else if (actionType === "scrape-data") {
    const url = document.getElementById("scrape-url").value.trim();
    if (!url) validationError = "Please enter a URL in the Data Scraping section.";
    else actionInputs = { url };

  } else if (actionType === "send-email") {
    const recipient = document.getElementById("recipient").value.trim();
    const subject   = document.getElementById("subject").value.trim();
    if (!recipient || !subject) validationError = "Please enter recipient and subject in the Email section.";
    else actionInputs = {
      recipient,
      subject,
      body: document.getElementById("body").value.trim() || "",
    };

  } else if (actionType === "fetch-email") {
    actionInputs = {};  // no inputs needed
  }

  if (validationError) {
    alert(validationError);
    return;
  }

  const analBtn = document.getElementById("analyse-btn");
  const execBtn = document.getElementById("execute-btn");
  const analDiv = document.getElementById("analysis-result");

  analBtn.disabled    = true;
  analBtn.textContent = "Analysing...";
  execBtn.disabled    = true;

  const actionLabels = {
    "chat":          "General Query Planning",
    "price-compare": "Price Comparison Strategy",
    "scrape-data":   "Web Scraping Plan",
    "send-email":    "Email Composition Plan",
    "fetch-email":   "Email Retrieval Plan",
  };
  const label = actionLabels[actionType] || actionType;

  analDiv.innerHTML = `
    <div style="color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:11px;padding:10px;line-height:1.7;">
      ⚡ Benchmarking: <span style="color:var(--accent)">${label}</span><br>
      Running all 4 variants: Basic-MCTS → R-MCTS → WM-MCTS → MCTS-RAG<br>
      <span style="color:var(--text-muted);font-size:10px;">This may take 10–20 seconds...</span>
    </div>`;
  showResultPanel("analysis");

  try {
    const sims = parseInt(simSlider.value);
    const res  = await fetch(`${API_URL}/mcts/benchmark-action`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({
        action_type:  actionType,
        inputs:       actionInputs,
        simulations:  sims,
      }),
    });
    const data = await res.json();
    renderAnalysisTable(data, analDiv);
  } catch (err) {
    analDiv.innerHTML = `<div style="color:var(--danger);font-size:11px;padding:10px;">Analysis failed: ${err.message}</div>`;
  } finally {
    analBtn.disabled    = false;
    analBtn.textContent = "⚡ Analyse All 4";
    execBtn.disabled    = false;
  }
});

// ─────────────────────────────────────────────
// Render Analysis Table
// ─────────────────────────────────────────────
function getCSSClass(name) { return VARIANT_CSS[name]      || "basic-mcts"; }
function getNameCSS(name)  { return VARIANT_NAME_CSS[name] || "v-basic"; }

function renderAnalysisTable(data, container) {
  const results = data.results  || [];
  const summary = data.summary  || {};

  if (!results.length) {
    container.innerHTML = `<div style="color:var(--danger);padding:10px;">No results returned.</div>`;
    return;
  }

  const maxTime = Math.max(...results.map(r => r.time_ms      || 0), 1);
  const maxTSR  = Math.max(...results.map(r => r.tsr_accuracy || 0), 1);

  // Action label + planning query
  const actionLabel    = data.action_label   || "Planning";
  const actionDesc     = data.action_desc    || "";
  const planningQuery  = data.planning_query || "";

  // Metric info box
  let html = `
  <div class="analysis-meta">
    <b style="color:var(--accent3)">${actionLabel}</b><br>
    <span style="color:var(--text-muted);font-size:9px;">${actionDesc}</span><br>
    <b style="color:var(--accent)">Planning query:</b> <span style="color:var(--text)">${planningQuery.slice(0, 80)}${planningQuery.length > 80 ? '...' : ''}</span><br>
    <b style="color:var(--accent)">Accuracy (TSR):</b> (Score/10)×100% — AgentBench/WebArena standard &nbsp;|&nbsp;
    <b style="color:var(--accent)">Baseline:</b> Basic-MCTS (TSR = ${summary.baseline_tsr ?? "—"}%)
  </div>`;

  // Analysis table
  html += `
  <table class="analysis-table">
    <thead>
      <tr>
        <th>#</th>
        <th>Variant</th>
        <th>Speed</th>
        <th>PQS/10</th>
        <th>TSR %</th>
        <th>Step Eff.</th>
        <th>vs Baseline</th>
        <th>Plan Steps</th>
      </tr>
    </thead>
    <tbody>`;

  results.forEach((r) => {
    const css     = getCSSClass(r.variant);
    const nameCss = getNameCSS(r.variant);
    const rank    = r.rank || 4;

    const isFastest = r.variant === summary.fastest;
    const isSlowest = r.time_ms === Math.max(...results.map(x => x.time_ms || 0));
    const speedCss  = isFastest ? "speed-fast" : isSlowest ? "speed-slow" : "";

    const tsrPct = ((r.tsr_accuracy || 0) / maxTSR * 100).toFixed(0);

    let impHtml = `<span class="imp-pill imp-base">Baseline</span>`;
    if (r.variant !== "Basic-MCTS" && r.improvement_vs_baseline != null) {
      const v   = r.improvement_vs_baseline;
      impHtml   = `<span class="imp-pill ${v >= 0 ? 'imp-pos' : 'imp-neg'}">${v >= 0 ? "+" : ""}${v}%</span>`;
    }

    const planSteps = (r.plan || []).length > 0
      ? r.plan.map(s => `<span>${s}</span>`).join(" ")
      : `<span style="color:var(--text-muted)">—</span>`;

    html += `
    <tr>
      <td><span class="rank-badge rank-${rank}">${rank}</span></td>
      <td><span class="${nameCss}">${r.variant}</span></td>
      <td class="speed-cell ${speedCss}">${(r.time_ms || 0).toFixed(0)}ms</td>
      <td>${r.plan_score != null ? r.plan_score.toFixed(1) : "—"}</td>
      <td class="tsr-cell">
        <div class="tsr-bar-wrap">
          <div class="tsr-bar-track">
            <div class="tsr-bar-fill ${css}" style="width:${tsrPct}%"></div>
          </div>
          <span class="tsr-val">${r.tsr_accuracy != null ? r.tsr_accuracy : "—"}%</span>
        </div>
      </td>
      <td>${r.step_efficiency != null ? r.step_efficiency.toFixed(2) : "—"}</td>
      <td>${impHtml}</td>
      <td class="plan-steps">${planSteps}</td>
    </tr>`;
  });

  html += `</tbody></table>`;

  html += `
  <div class="analysis-summary">
    <b>Fastest:</b> ${summary.fastest || "N/A"} &nbsp;&nbsp;
    <b>Most Accurate (TSR):</b> ${summary.most_accurate || "N/A"} &nbsp;&nbsp;
    <b>Most Efficient:</b> ${summary.most_efficient || "N/A"} &nbsp;&nbsp;
    <b>Best Overall:</b> ${summary.best_overall || "N/A"}
  </div>`;

  container.innerHTML = html;
}

// ─────────────────────────────────────────────
// handleChatQuery
// ─────────────────────────────────────────────
async function handleChatQuery(resultDiv) {
  const task = document.getElementById("task").value.trim();
  if (!task) { resultDiv.textContent = "Please enter a query."; return; }

  resultDiv.textContent = `Processing with ${selectedVariant.toUpperCase()}...`;

  const sims = parseInt(simSlider.value);
  const res  = await fetch(`${API_URL}/ask`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ query: task, variant: selectedVariant, simulations: sims }),
  });

  const data = await res.json();

  let out = "";
  if (data.mcts_variant)         out += `[${data.mcts_variant}] `;
  if (data.mcts_score != null)   out += `Score: ${data.mcts_score}/10 | `;
  if (data.mcts_time_ms != null) out += `Time: ${data.mcts_time_ms.toFixed(0)}ms\n\n`;
  if (data.plan && data.plan.length > 0 && data.plan[0] !== "Direct LLM Response") {
    out += `Plan: ${data.plan.join(" → ")}\n\n`;
  }
  out += data.answer || JSON.stringify(data);
  resultDiv.textContent = out;
}

// ─────────────────────────────────────────────
// handlePriceCompare — Amazon, Flipkart, Myntra
// + official site (if URL provided)
// ─────────────────────────────────────────────
async function handlePriceCompare(resultDiv) {
  const product     = document.getElementById("price-product").value.trim();
  const officialUrl = document.getElementById("price-official-url").value.trim();

  if (!product) {
    resultDiv.textContent = "Please enter a product name.";
    return;
  }

  const query = officialUrl
    ? `compare ${product} prices on various platforms ${officialUrl}`
    : `compare ${product} prices on various platforms`;

  resultDiv.textContent =
    `🔍 Scraping live prices for "${product}"...\n` +
    `⏳ Amazon.in → Flipkart → Myntra` +
    (officialUrl ? ` → Official Site` : "") + `\n` +
    `⚠️  Bing snippet fallback if platforms block\n` +
    `⏱️  Please wait 15–30 seconds...`;

  try {
    const res  = await fetch(`${API_URL}/ask`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ query, variant: "basic-mcts", simulations: 5 }),
    });
    const data = await res.json();
    resultDiv.textContent = data.answer || JSON.stringify(data);
  } catch (err) {
    resultDiv.textContent = `Error: ${err.message}`;
  }
}

// ─────────────────────────────────────────────
// handleScrapeData
// ─────────────────────────────────────────────
async function handleScrapeData(resultDiv) {
  const url = document.getElementById("scrape-url").value.trim();
  if (!url) { resultDiv.textContent = "Please enter a URL."; return; }

  resultDiv.textContent = "Scraping...";
  const res  = await fetch(`${API_URL}/ask`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({ query: `scrape ${url}` }),
  });
  const data = await res.json();
  resultDiv.textContent = data.answer || JSON.stringify(data);
}

// ─────────────────────────────────────────────
// handleSendEmail — with optional attachment
// ─────────────────────────────────────────────
async function handleSendEmail(resultDiv) {
  const recipient = document.getElementById("recipient").value.trim();
  const subject   = document.getElementById("subject").value.trim();
  const body      = document.getElementById("body").value.trim();

  if (!recipient || !subject) {
    resultDiv.textContent = "Recipient and subject are required.";
    return;
  }

  resultDiv.textContent = attachmentName
    ? `Sending email with attachment: ${attachmentName}...`
    : "Sending email...";

  const res  = await fetch(`${API_URL}/send-email`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
    body:    JSON.stringify({
      recipient,
      subject,
      body,
      attachment_data: attachmentData || null,
      attachment_name: attachmentName || null,
    }),
  });
  const data = await res.json();
  resultDiv.textContent = data.message;

  // Clear attachment state on success
  if (data.message && data.message.includes("sent successfully")) {
    attachmentData = null;
    attachmentName = null;
    if (attachInput)   attachInput.value = "";
    if (fileInfoDiv)   fileInfoDiv.classList.remove("visible");
    if (uploadPrompt)  uploadPrompt.textContent = "Click to attach a file (PDF, image, doc, zip, etc.)";
  }
}

// ─────────────────────────────────────────────
// handleFetchEmails
// ─────────────────────────────────────────────
async function handleFetchEmails(resultDiv) {
  resultDiv.textContent = "Fetching emails...";
  const res  = await fetch(`${API_URL}/fetch-emails`, {
    method:  "POST",
    headers: { "Content-Type": "application/json" },
  });
  const data = await res.json();
  resultDiv.textContent = data.message;
}
//////////////////////////////////////////////////////////////////////////////

// // popup.js
// const API_URL = "http://localhost:8000";

// // ─────────────────────────────────────────────
// // State
// // ─────────────────────────────────────────────
// let selectedVariant = "basic-mcts";
// let attachmentData  = null;   // base64 string
// let attachmentName  = null;   // original filename

// const VARIANT_INFO = {
//   "basic-mcts": {
//     desc:  "Standard MCTS — UCB1 selection, random rollout, heuristic scoring. Baseline variant — no retrieval or LLM.",
//     color: "#f7c94f",
//   },
//   "r-mcts": {
//     desc:  "Retrieval MCTS — live web retrieval per node during expansion. Action selection grounded in freshly fetched content.",
//     color: "#4f8ef7",
//   },
//   "wm-mcts": {
//     desc:  "World-Model MCTS — heuristic world model guides expansion. Fast and accurate planning.",
//     color: "#7c5cfc",
//   },
//   "rag-mcts": {
//     desc:  "MCTS-RAG — seeds context from Wikipedia before search. Context-aware planning with retrieval bonus.",
//     color: "#00d4aa",
//   },
// };

// const VARIANT_CSS = {
//   "Basic-MCTS": "basic-mcts",
//   "R-MCTS":     "r-mcts",
//   "WM-MCTS":    "wm-mcts",
//   "MCTS-RAG":   "rag-mcts",
// };

// const VARIANT_NAME_CSS = {
//   "Basic-MCTS": "v-basic",
//   "R-MCTS":     "v-r",
//   "WM-MCTS":    "v-wm",
//   "MCTS-RAG":   "v-rag",
// };

// // ─────────────────────────────────────────────
// // Variant pills
// // ─────────────────────────────────────────────
// document.querySelectorAll(".variant-pill").forEach((pill) => {
//   pill.addEventListener("click", () => {
//     document.querySelectorAll(".variant-pill").forEach((p) => p.classList.remove("active"));
//     pill.classList.add("active");
//     selectedVariant = pill.dataset.variant;
//     const info   = VARIANT_INFO[selectedVariant];
//     const descEl = document.getElementById("variant-desc");
//     descEl.textContent           = info.desc;
//     descEl.style.borderLeftColor = info.color;
//   });
// });

// // ─────────────────────────────────────────────
// // Simulations slider
// // ─────────────────────────────────────────────
// const simSlider  = document.getElementById("simulations");
// const simDisplay = document.getElementById("sim-display");
// simSlider.addEventListener("input", () => { simDisplay.textContent = simSlider.value; });

// // ─────────────────────────────────────────────
// // File attachment handler
// // ─────────────────────────────────────────────
// const attachInput  = document.getElementById("attachment-input");
// const fileInfoDiv  = document.getElementById("file-selected-info");
// const fileNameSpan = document.getElementById("file-selected-name");
// const fileClearBtn = document.getElementById("file-clear-btn");
// const uploadPrompt = document.getElementById("upload-prompt");

// if (attachInput) {
//   attachInput.addEventListener("change", () => {
//     const file = attachInput.files[0];
//     if (!file) return;

//     if (file.size > 10 * 1024 * 1024) {
//       alert("File too large. Maximum attachment size is 10 MB.");
//       attachInput.value = "";
//       return;
//     }

//     attachmentName = file.name;
//     const reader   = new FileReader();
//     reader.onload  = (e) => {
//       attachmentData           = e.target.result.split(",")[1];
//       fileNameSpan.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
//       fileInfoDiv.classList.add("visible");
//       uploadPrompt.textContent = "File attached ✓";
//     };
//     reader.readAsDataURL(file);
//   });

//   fileClearBtn.addEventListener("click", () => {
//     attachmentData = null;
//     attachmentName = null;
//     attachInput.value = "";
//     fileInfoDiv.classList.remove("visible");
//     uploadPrompt.textContent = "Click to attach a file (PDF, image, doc, zip, etc.)";
//   });
// }

// // ─────────────────────────────────────────────
// // Action selector — show/hide sections
// // ─────────────────────────────────────────────
// document.getElementById("action-type").addEventListener("change", (e) => {
//   document.querySelectorAll(".action-section").forEach((s) => s.classList.remove("active"));
//   const map = {
//     "chat":          "chat-section",
//     "price-compare": "price-compare-section",
//     "scrape-data":   "scrape-data-section",
//     "send-email":    "send-email-section",
//     "fetch-email":   "fetch-email-section",
//   };
//   const sid = map[e.target.value];
//   if (sid) document.getElementById(sid).classList.add("active");
//   hideResultPanel();
// });

// // ─────────────────────────────────────────────
// // Result panel tabs
// // ─────────────────────────────────────────────
// document.querySelectorAll(".result-tab").forEach((tab) => {
//   tab.addEventListener("click", () => {
//     document.querySelectorAll(".result-tab").forEach((t)  => t.classList.remove("active"));
//     document.querySelectorAll(".result-pane").forEach((p) => p.classList.remove("active"));
//     tab.classList.add("active");
//     document.getElementById(`pane-${tab.dataset.tab}`).classList.add("active");
//   });
// });

// function showResultPanel(tab = "output") {
//   document.getElementById("result-panel").style.display = "block";
//   document.querySelectorAll(".result-tab").forEach((t) => {
//     t.classList.toggle("active", t.dataset.tab === tab);
//   });
//   document.querySelectorAll(".result-pane").forEach((p) => {
//     p.classList.toggle("active", p.id === `pane-${tab}`);
//   });
// }

// function hideResultPanel() {
//   document.getElementById("result-panel").style.display = "none";
// }

// // ─────────────────────────────────────────────
// // Connection check
// // ─────────────────────────────────────────────
// async function checkConnection() {
//   const el = document.getElementById("status");
//   try {
//     const res = await fetch(`${API_URL}/health`);
//     if (res.ok) {
//       el.textContent = "Connected";
//       el.className   = "status-badge connected";
//     } else {
//       el.textContent = "Backend Error";
//       el.className   = "status-badge disconnected";
//     }
//   } catch {
//     el.textContent = "Offline";
//     el.className   = "status-badge disconnected";
//   }
// }
// checkConnection();
// setInterval(checkConnection, 10000);

// // ─────────────────────────────────────────────
// // Execute button
// // ─────────────────────────────────────────────
// document.getElementById("execute-btn").addEventListener("click", async () => {
//   const actionType = document.getElementById("action-type").value;
//   const resultDiv  = document.getElementById("result");
//   const execBtn    = document.getElementById("execute-btn");
//   const analBtn    = document.getElementById("analyse-btn");

//   execBtn.disabled    = true;
//   execBtn.textContent = "Processing...";
//   analBtn.disabled    = true;

//   resultDiv.textContent = "Working...";
//   showResultPanel("output");

//   try {
//     if      (actionType === "chat")          await handleChatQuery(resultDiv);
//     else if (actionType === "price-compare") await handlePriceCompare(resultDiv);
//     else if (actionType === "scrape-data")   await handleScrapeData(resultDiv);
//     else if (actionType === "send-email")    await handleSendEmail(resultDiv);
//     else if (actionType === "fetch-email")   await handleFetchEmails(resultDiv);
//   } catch (err) {
//     resultDiv.textContent = `Error: ${err.message}`;
//   } finally {
//     execBtn.disabled    = false;
//     execBtn.textContent = "▶ Execute";
//     analBtn.disabled    = false;
//   }
// });

// // ─────────────────────────────────────────────
// // Analyse button
// // Runs all 4 MCTS variants on the chat query,
// // shows TSR accuracy, speed, step efficiency.
// //
// // Accuracy: Task Success Rate (TSR)
// //   TSR (%) = (plan_score / 10.0) × 100
// //   Standard metric — AgentBench / WebArena /
// //   ALFWorld agentic task benchmarks.
// // ─────────────────────────────────────────────
// document.getElementById("analyse-btn").addEventListener("click", async () => {
//   const task = document.getElementById("task").value.trim();
//   if (!task) {
//     alert("Enter a query in the chat box first, then click Analyse All 4.");
//     return;
//   }

//   const analBtn = document.getElementById("analyse-btn");
//   const execBtn = document.getElementById("execute-btn");
//   const analDiv = document.getElementById("analysis-result");

//   analBtn.disabled    = true;
//   analBtn.textContent = "Analysing...";
//   execBtn.disabled    = true;

//   analDiv.innerHTML = `<div style="color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:11px;padding:10px;">
//     ⚡ Running all 4 MCTS variants...<br>Basic-MCTS → R-MCTS → WM-MCTS → MCTS-RAG
//   </div>`;
//   showResultPanel("analysis");

//   try {
//     const sims = parseInt(simSlider.value);
//     const res  = await fetch(`${API_URL}/mcts/benchmark`, {
//       method:  "POST",
//       headers: { "Content-Type": "application/json" },
//       body:    JSON.stringify({ query: task, simulations: sims }),
//     });
//     const data = await res.json();
//     renderAnalysisTable(data, analDiv);
//   } catch (err) {
//     analDiv.innerHTML = `<div style="color:var(--danger);font-size:11px;">Analysis failed: ${err.message}</div>`;
//   } finally {
//     analBtn.disabled    = false;
//     analBtn.textContent = "⚡ Analyse All 4";
//     execBtn.disabled    = false;
//   }
// });

// // ─────────────────────────────────────────────
// // Render Analysis Table
// // ─────────────────────────────────────────────
// function getCSSClass(name) { return VARIANT_CSS[name]      || "basic-mcts"; }
// function getNameCSS(name)  { return VARIANT_NAME_CSS[name] || "v-basic"; }

// function renderAnalysisTable(data, container) {
//   const results = data.results  || [];
//   const summary = data.summary  || {};

//   if (!results.length) {
//     container.innerHTML = `<div style="color:var(--danger);padding:10px;">No results returned.</div>`;
//     return;
//   }

//   const maxTime = Math.max(...results.map(r => r.time_ms      || 0), 1);
//   const maxTSR  = Math.max(...results.map(r => r.tsr_accuracy || 0), 1);

//   // Metric info box
//   let html = `
//   <div class="analysis-meta">
//     <b style="color:var(--accent)">Accuracy (TSR):</b> (Plan Score / 10) × 100% — AgentBench / WebArena standard &nbsp;|&nbsp;
//     <b style="color:var(--accent)">Step Eff.:</b> Score per step &nbsp;|&nbsp;
//     <b style="color:var(--accent)">Baseline:</b> Basic-MCTS (TSR = ${summary.baseline_tsr ?? "—"}%)
//   </div>`;

//   // Analysis table
//   html += `
//   <table class="analysis-table">
//     <thead>
//       <tr>
//         <th>#</th>
//         <th>Variant</th>
//         <th>Speed</th>
//         <th>PQS/10</th>
//         <th>TSR %</th>
//         <th>Step Eff.</th>
//         <th>vs Baseline</th>
//         <th>Plan Steps</th>
//       </tr>
//     </thead>
//     <tbody>`;

//   results.forEach((r) => {
//     const css     = getCSSClass(r.variant);
//     const nameCss = getNameCSS(r.variant);
//     const rank    = r.rank || 4;

//     const isFastest = r.variant === summary.fastest;
//     const isSlowest = r.time_ms === Math.max(...results.map(x => x.time_ms || 0));
//     const speedCss  = isFastest ? "speed-fast" : isSlowest ? "speed-slow" : "";

//     const tsrPct = ((r.tsr_accuracy || 0) / maxTSR * 100).toFixed(0);

//     let impHtml = `<span class="imp-pill imp-base">Baseline</span>`;
//     if (r.variant !== "Basic-MCTS" && r.improvement_vs_baseline != null) {
//       const v   = r.improvement_vs_baseline;
//       impHtml   = `<span class="imp-pill ${v >= 0 ? 'imp-pos' : 'imp-neg'}">${v >= 0 ? "+" : ""}${v}%</span>`;
//     }

//     const planSteps = (r.plan || []).length > 0
//       ? r.plan.map(s => `<span>${s}</span>`).join(" ")
//       : `<span style="color:var(--text-muted)">—</span>`;

//     html += `
//     <tr>
//       <td><span class="rank-badge rank-${rank}">${rank}</span></td>
//       <td><span class="${nameCss}">${r.variant}</span></td>
//       <td class="speed-cell ${speedCss}">${(r.time_ms || 0).toFixed(0)}ms</td>
//       <td>${r.plan_score != null ? r.plan_score.toFixed(1) : "—"}</td>
//       <td class="tsr-cell">
//         <div class="tsr-bar-wrap">
//           <div class="tsr-bar-track">
//             <div class="tsr-bar-fill ${css}" style="width:${tsrPct}%"></div>
//           </div>
//           <span class="tsr-val">${r.tsr_accuracy != null ? r.tsr_accuracy : "—"}%</span>
//         </div>
//       </td>
//       <td>${r.step_efficiency != null ? r.step_efficiency.toFixed(2) : "—"}</td>
//       <td>${impHtml}</td>
//       <td class="plan-steps">${planSteps}</td>
//     </tr>`;
//   });

//   html += `</tbody></table>`;

//   html += `
//   <div class="analysis-summary">
//     <b>Fastest:</b> ${summary.fastest || "N/A"} &nbsp;&nbsp;
//     <b>Most Accurate (TSR):</b> ${summary.most_accurate || "N/A"} &nbsp;&nbsp;
//     <b>Most Efficient:</b> ${summary.most_efficient || "N/A"} &nbsp;&nbsp;
//     <b>Best Overall:</b> ${summary.best_overall || "N/A"}
//   </div>`;

//   container.innerHTML = html;
// }

// // ─────────────────────────────────────────────
// // handleChatQuery
// // ─────────────────────────────────────────────
// async function handleChatQuery(resultDiv) {
//   const task = document.getElementById("task").value.trim();
//   if (!task) { resultDiv.textContent = "Please enter a query."; return; }

//   resultDiv.textContent = `Processing with ${selectedVariant.toUpperCase()}...`;

//   const sims = parseInt(simSlider.value);
//   const res  = await fetch(`${API_URL}/ask`, {
//     method:  "POST",
//     headers: { "Content-Type": "application/json" },
//     body:    JSON.stringify({ query: task, variant: selectedVariant, simulations: sims }),
//   });

//   const data = await res.json();

//   let out = "";
//   if (data.mcts_variant)         out += `[${data.mcts_variant}] `;
//   if (data.mcts_score != null)   out += `Score: ${data.mcts_score}/10 | `;
//   if (data.mcts_time_ms != null) out += `Time: ${data.mcts_time_ms.toFixed(0)}ms\n\n`;
//   if (data.plan && data.plan.length > 0 && data.plan[0] !== "Direct LLM Response") {
//     out += `Plan: ${data.plan.join(" → ")}\n\n`;
//   }
//   out += data.answer || JSON.stringify(data);
//   resultDiv.textContent = out;
// }

// // ─────────────────────────────────────────────
// // handlePriceCompare — Amazon, Flipkart, Myntra
// // + official site (if URL provided)
// // ─────────────────────────────────────────────
// async function handlePriceCompare(resultDiv) {
//   const product     = document.getElementById("price-product").value.trim();
//   const officialUrl = document.getElementById("price-official-url").value.trim();

//   if (!product) {
//     resultDiv.textContent = "Please enter a product name.";
//     return;
//   }

//   const query = officialUrl
//     ? `compare ${product} prices on various platforms ${officialUrl}`
//     : `compare ${product} prices on various platforms`;

//   resultDiv.textContent =
//     `🔍 Scraping live prices for "${product}"...\n` +
//     `⏳ Amazon.in → Flipkart → Myntra` +
//     (officialUrl ? ` → Official Site` : "") + `\n` +
//     `⚠️  Bing snippet fallback if platforms block\n` +
//     `⏱️  Please wait 15–30 seconds...`;

//   try {
//     const res  = await fetch(`${API_URL}/ask`, {
//       method:  "POST",
//       headers: { "Content-Type": "application/json" },
//       body:    JSON.stringify({ query, variant: "basic-mcts", simulations: 5 }),
//     });
//     const data = await res.json();
//     resultDiv.textContent = data.answer || JSON.stringify(data);
//   } catch (err) {
//     resultDiv.textContent = `Error: ${err.message}`;
//   }
// }

// // ─────────────────────────────────────────────
// // handleScrapeData
// // ─────────────────────────────────────────────
// async function handleScrapeData(resultDiv) {
//   const url = document.getElementById("scrape-url").value.trim();
//   if (!url) { resultDiv.textContent = "Please enter a URL."; return; }

//   resultDiv.textContent = "Scraping...";
//   const res  = await fetch(`${API_URL}/ask`, {
//     method:  "POST",
//     headers: { "Content-Type": "application/json" },
//     body:    JSON.stringify({ query: `scrape ${url}` }),
//   });
//   const data = await res.json();
//   resultDiv.textContent = data.answer || JSON.stringify(data);
// }

// // ─────────────────────────────────────────────
// // handleSendEmail — with optional attachment
// // ─────────────────────────────────────────────
// async function handleSendEmail(resultDiv) {
//   const recipient = document.getElementById("recipient").value.trim();
//   const subject   = document.getElementById("subject").value.trim();
//   const body      = document.getElementById("body").value.trim();

//   if (!recipient || !subject) {
//     resultDiv.textContent = "Recipient and subject are required.";
//     return;
//   }

//   resultDiv.textContent = attachmentName
//     ? `Sending email with attachment: ${attachmentName}...`
//     : "Sending email...";

//   const res  = await fetch(`${API_URL}/send-email`, {
//     method:  "POST",
//     headers: { "Content-Type": "application/json" },
//     body:    JSON.stringify({
//       recipient,
//       subject,
//       body,
//       attachment_data: attachmentData || null,
//       attachment_name: attachmentName || null,
//     }),
//   });
//   const data = await res.json();
//   resultDiv.textContent = data.message;

//   // Clear attachment state on success
//   if (data.message && data.message.includes("sent successfully")) {
//     attachmentData = null;
//     attachmentName = null;
//     if (attachInput)   attachInput.value = "";
//     if (fileInfoDiv)   fileInfoDiv.classList.remove("visible");
//     if (uploadPrompt)  uploadPrompt.textContent = "Click to attach a file (PDF, image, doc, zip, etc.)";
//   }
// }

// // ─────────────────────────────────────────────
// // handleFetchEmails
// // ─────────────────────────────────────────────
// async function handleFetchEmails(resultDiv) {
//   resultDiv.textContent = "Fetching emails...";
//   const res  = await fetch(`${API_URL}/fetch-emails`, {
//     method:  "POST",
//     headers: { "Content-Type": "application/json" },
//   });
//   const data = await res.json();
//   resultDiv.textContent = data.message;
// }