/**
 * NORTH Master Controller - Backend-Matched Sync
 * Matched to EvaluateRequest: prompt, model, provider, model_name, api_base, api_key, session_id, parent_branch_id, n_reads.
 */

const DEFAULT_API = "https://north-backend-kdgq.onrender.com"; 

function getApiBase() {
  const url = new URL(window.location.href);
  return (url.searchParams.get("api") || DEFAULT_API).replace(/\/$/, "");
}

const el = (id) => document.getElementById(id);
const setVisible = (id, show) => { if(el(id)) el(id).classList.toggle("hidden", !show); };

// --- UI STATE ---
let selectedModel = "default";

function setStatus(status, ms, modelUsed){
  const row = el("statusRow");
  if(row) { row.classList.remove("hidden"); row.classList.add("flex"); }
  if(el("statusText")) el("statusText").textContent = status || "—";
  if(el("timingText")) el("timingText").textContent = ms ? `· ${Math.round(ms)}ms${modelUsed ? ` · model: ${modelUsed}` : ""}` : "";

  const dot = el("statusDot");
  if(dot) {
    dot.className = "h-2 w-2 rounded-full " + 
      (status === "ADMISSIBLE" ? "bg-white" : status === "REFUSAL" ? "bg-red-500" : "bg-zinc-600");
  }
}

function setGuide(data){
  // Triadic Scores
  const scores = ["scoreI", "scoreR", "scoreSem", "scoreL", "scoreTau", "scoreRho", "scoreRhoCrit"];
  scores.forEach(id => { if(el(id)) el(id).textContent = data.scores?.[id.replace("score","").toLowerCase()] ?? data.scores?.[id.replace("score","")] ?? "—"; });

  // Branch & Diagnostics
  if(el("branchId")) el("branchId").textContent = data.branch?.branch_id ?? "—";
  if(el("parentBranchId")) el("parentBranchId").textContent = data.branch?.parent_branch_id ?? "—";
  if(el("nReads")) el("nReads").textContent = data.diagnostics?.reads ?? "—";

  // Lineage
  const lineage = el("lineage");
  if(lineage) {
    lineage.innerHTML = "";
    const items = [data.chord?.tonic, ...(data.chord?.ballasts || [])];
    items.forEach((item, i) => {
      if(item?.meta) {
        lineage.innerHTML += `
          <div class="rounded-xl border border-zinc-900 bg-black/40 p-3">
            <div class="text-xs text-zinc-400">${i === 0 ? 'Tonic' : 'Ballast ' + i}</div>
            <div class="mt-1 text-sm text-zinc-100">${item.meta.Framework_Name || "—"}</div>
            <div class="mt-1 text-xs text-zinc-500">${item.meta.Macro_Region || "—"} · ${item.meta.Lineage_Cluster || "—"}</div>
          </div>`;
      }
    });
  }
}

// --- CORE ACTION ---

async function evaluatePrompt() {
  const prompt = el("prompt")?.value.trim();
  if(!prompt) return;

  el("btnEvaluate").disabled = true;
  setVisible("outputCard", false);
  setVisible("errorBox", false);
  setStatus("EVALUATING...", 0);

  const t0 = performance.now();
  try {
    const api = getApiBase();
    const payload = {
      prompt: prompt,
      model: selectedModel,
      provider: selectedModel === "mistral" ? "mistral" : null,
      model_name: selectedModel === "mistral" ? (el("mistralModel")?.value?.trim() || null) : null,
      api_key: selectedModel === "mistral" ? (el("mistralKey")?.value?.trim() || null) : null,
      api_base: null, // Placeholder for future custom endpoints
      session_id: localStorage.getItem("north_session_id"),
      parent_branch_id: el("linkLineage")?.checked ? localStorage.getItem("north_last_branch_id") : null,
      n_reads: parseInt(el("apertureReads")?.value || "1", 10)
    };

    const res = await fetch(`${api}/evaluate`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });

    const ms = performance.now() - t0;
    const data = await res.json();

    if(!res.ok) throw new Error(data.detail || "Gate Error");

    if(data.branch?.branch_id) localStorage.setItem("north_last_branch_id", data.branch.branch_id);

    setStatus(data.status, ms, data.model_used);
    if(el("fmo")) el("fmo").textContent = data.fused_meaning_object || data.raw_text || "—";
    setGuide(data);
    setVisible("outputCard", true);

  } catch(e) {
    if(el("errorBox")) el("errorBox").textContent = `CONNECTION FAILED: ${e.message}`;
    setVisible("errorBox", true);
    setStatus("ERROR", 0);
  } finally {
    el("btnEvaluate").disabled = false;
  }
}

//
