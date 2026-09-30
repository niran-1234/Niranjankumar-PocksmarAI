async function api(url, options={}) {
  const response = await fetch(url, {credentials:"include", ...options});
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(data.detail || "Request failed");
  return data;
}

async function refreshNav() {
  const el = document.getElementById("nav-auth");
  if (!el) return;
  try {
    const data = await api("/api/session-info");
    el.textContent = "Logout";
    el.href = "#";
    el.onclick = async (e) => { e.preventDefault(); await api("/api/logout",{method:"POST"}); location.href="/"; };
  } catch (_) {
    el.textContent = "Login"; el.href="/login"; el.onclick=null;
  }
}
document.addEventListener("DOMContentLoaded", refreshNav);

function setupAuthForm(id, endpoint) {
  const form = document.getElementById(id);
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = document.getElementById("form-message");
    const body = Object.fromEntries(new FormData(form).entries());
    try {
      await api(endpoint, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
      location.href="/dashboard";
    } catch(err) { message.textContent = err.message; }
  });
}

function money(n){return "₹"+Number(n||0).toLocaleString("en-IN");}

function renderResult(data) {
  const result = document.getElementById("result");
  const cards = (data.recommendations||[]).map(x => `
    <article class="rec">
      <div><h3>${escapeHtml(x.name)}</h3><span class="pill">${escapeHtml(x.category)}</span> <span class="pill">${escapeHtml(x.platform)}</span>
      <p class="muted">${escapeHtml(x.reason)}</p></div>
      <div><strong>${money(x.estimated_price)}</strong><br><a href="${escapeAttr(x.search_url)}" target="_blank" rel="noopener">Search platform →</a></div>
    </article>`).join("");
  result.innerHTML = `
    <div class="card"><div class="result-head"><div><p class="eyebrow">${data.ai_powered?"GEMINI AI":"FALLBACK MODE"}</p><h2>${escapeHtml(data.title)}</h2><p>${escapeHtml(data.summary)}</p></div></div>
    <div class="metrics"><div class="metric">Budget<b>${money(data.budget)}</b></div><div class="metric">Estimated total<b>${money(data.estimated_total)}</b></div><div class="metric">Remaining<b>${money(data.remaining_budget)}</b></div></div>
    <h3>Recommendations</h3>${cards || "<p>No recommendation items were returned.</p>"}
    <p class="muted">${escapeHtml(data.disclaimer)}</p></div>`;
}

function escapeHtml(value){return String(value??"").replace(/[&<>"']/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));}
function escapeAttr(value){return escapeHtml(value).replace(/javascript:/gi,"");}

function setupPlanner(planner) {
  const form = document.querySelector(".planner-form");
  if (!form) return;
  form.addEventListener("submit", async e => {
    e.preventDefault();
    const result = document.getElementById("result");
    result.innerHTML = '<div class="card">Generating your plan...</div>';
    try {
      let data, options = {method:"POST"};
      const fd = new FormData(form);
      if (planner === "home") {
        const rooms = [...form.querySelector("[name=rooms]").selectedOptions].map(x=>x.value);
        data = {budget:Number(fd.get("budget")), rooms, style:fd.get("style"), notes:fd.get("notes"), quantities:{}};
        options.headers={"Content-Type":"application/json"}; options.body=JSON.stringify(data);
        data = await api("/api/generate-home",options);
      } else if (planner === "party") {
        data = {budget:Number(fd.get("budget")), event_type:fd.get("event_type"), guests:Number(fd.get("guests")), venue:fd.get("venue"), city:fd.get("city"), notes:fd.get("notes")};
        options.headers={"Content-Type":"application/json"}; options.body=JSON.stringify(data);
        data = await api("/api/generate-party",options);
      } else {
        data = await api("/api/generate-jewelry", {method:"POST", body:new FormData(form)});
      }
      renderResult(data);
    } catch(err) {
      if (planner === "jewelry") {
        try {
          const fd = new FormData(form);
          const data = await api("/api/generate-jewelry",{method:"POST",body:fd});
          renderResult(data); return;
        } catch(err2) { result.innerHTML=`<div class="card message">${escapeHtml(err2.message)}</div>`; return; }
      }
      result.innerHTML=`<div class="card message">${escapeHtml(err.message)}</div>`;
    }
  });
}

async function loadDashboard() {
  try {
    const session = await api("/api/session-info");
    document.getElementById("welcome").textContent = `Welcome, ${session.user.name}`;
    const rows = await api("/api/history");
    document.getElementById("recent-history").innerHTML = rows.slice(0,5).map(x=>`<p><a href="/history">#${x.id} · ${escapeHtml(x.planner)} · ${money(x.budget)}</a> <span class="muted">${new Date(x.created_at).toLocaleString()}</span></p>`).join("") || "<p>No plans yet.</p>";
  } catch (_) { location.href="/login"; }
}

async function loadHistory() {
  const list = document.getElementById("history-list");
  try {
    const rows = await api("/api/history");
    list.innerHTML = rows.length ? `<table><thead><tr><th>Planner</th><th>Budget</th><th>Date</th><th></th></tr></thead><tbody>${rows.map(x=>`<tr><td>${escapeHtml(x.planner)}</td><td>${money(x.budget)}</td><td>${new Date(x.created_at).toLocaleString()}</td><td><button class="button secondary" onclick="showHistory(${x.id})">View</button></td></tr>`).join("")}</tbody></table>` : "<p>No saved recommendations.</p>";
  } catch (_) { list.innerHTML="<p>Please log in to view history.</p>"; }
}

async function showHistory(id) {
  const detail = document.getElementById("history-detail");
  try { const data = await api(`/api/history/${id}`); detail.classList.remove("hidden"); renderHistoryDetail(data,detail); detail.scrollIntoView({behavior:"smooth"}); }
  catch(err){detail.classList.remove("hidden"); detail.textContent=err.message;}
}
function renderHistoryDetail(data,el){el.innerHTML=`<h2>${escapeHtml(data.title)}</h2><p>${escapeHtml(data.summary)}</p><div class="metrics"><div class="metric">Budget<b>${money(data.budget)}</b></div><div class="metric">Total<b>${money(data.estimated_total)}</b></div><div class="metric">Remaining<b>${money(data.remaining_budget)}</b></div></div><p class="muted">${escapeHtml(data.disclaimer)}</p>`;}
