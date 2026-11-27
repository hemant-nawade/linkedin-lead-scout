/* LinkedIn Lead Scout — dashboard SPA (no build step) */
(() => {
"use strict";

// ------------------------------------------------------------------ helpers
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const initials = (n) => (n || "?").replace(/^Sample · /, "").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase() || "?";
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
const fmtDate = (iso) => iso ? new Date(iso).toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
const timeAgo = (iso) => {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now"; if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago"; return Math.floor(s / 86400) + "d ago";
};

const ICONS = {
  home: '<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 7M18 14a6 6 0 0 1 3.5 6"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  bell: '<path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  ext: '<path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="M12 8v4M12 16h.01"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  check: '<path d="m5 12 5 5L20 7"/>',
  inbox: '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5h13L22 12v6a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-6z"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  trash: '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/>',
  download: '<path d="M12 3v12M7 10l5 5 5-5M5 21h14"/>',
  link: '<path d="M10 14a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1 1M14 10a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1-1"/>',
  bookmark: '<path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
  phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
  sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  copy: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>',
  webhook: '<path d="M18 16.98h-5.99c-1.1 0-1.95.94-2.48 1.9A4 4 0 0 1 2 17c.01-.7.2-1.4.57-2M6 17l3.13-5.78c.53-.97.1-2.18-.5-3.1a4 4 0 1 1 6.89-4.06M12 6l3.13 5.73C15.66 12.7 16.9 13 18 13a4 4 0 0 1 0 8"/>',
  terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/>',
};
const ic = (n, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ""}</svg>`;
const LI_LOGO = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13zM7.12 20.45H3.56V9h3.56v11.45zM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0z"/></svg>';

// ------------------------------------------------------------------ state & api
const S = { me: null, pub: null, settings: null, users: [], stats: null, notifs: { items: [], unread: 0 },
  filters: { q: "", keyword: "", lead_type: "", intent: "", owner: "", source: "" }, page: 1, lastUnreadTop: 0, integrations: null };

async function api(path, opts = {}) {
  const o = { method: opts.method || "GET", headers: { Accept: "application/json" }, credentials: "same-origin" };
  if (opts.body !== undefined) { o.headers["Content-Type"] = "application/json"; o.body = JSON.stringify(opts.body); }
  const r = await fetch(path, o);
  let data = null;
  try { data = await r.json(); } catch { /* empty */ }
  if (r.status === 401 && !opts.allow401) { S.me = null; go("#/login"); throw new Error("Please log in"); }
  if (!r.ok) {
    const err = new Error(detailMsg(data) || `Request failed (${r.status})`);
    err.status = r.status; err.data = data; throw err;
  }
  return data;
}
function detailMsg(d) {
  if (!d) return "";
  if (typeof d.detail === "string") return d.detail;
  if (Array.isArray(d.detail)) return d.detail.map((x) => `${(x.loc || []).slice(-1)[0]}: ${x.msg}`).join(", ");
  return "";
}

function toast(title, body = "", kind = "") {
  const el = document.createElement("div");
  el.className = "toast " + kind;
  el.innerHTML = `<b>${esc(title)}</b>${body ? `<div class="muted small">${esc(body)}</div>` : ""}`;
  $("#toasts").appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transition = ".3s"; setTimeout(() => el.remove(), 300); }, 4200);
}

function go(hash) { if (location.hash !== hash) location.hash = hash; else route(); }
function parseHash() {
  const h = location.hash.replace(/^#/, "") || "/";
  const [path, qs] = h.split("?");
  return { parts: path.split("/").filter(Boolean), params: new URLSearchParams(qs || "") };
}

// ------------------------------------------------------------------ modal / drawer
function closeOverlay() { $("#modal-root").innerHTML = ""; document.body.style.overflow = ""; }
function confirmBox(title, text, okLabel = "Confirm", danger = false) {
  return new Promise((res) => {
    $("#modal-root").innerHTML = `<div class="overlay" data-x></div><div class="modal" role="dialog">
      <h2>${esc(title)}</h2><p class="muted">${esc(text)}</p>
      <div class="row" style="justify-content:flex-end;margin-top:18px"><button class="btn ghost" data-no>Cancel</button>
      <button class="btn ${danger ? "danger" : "primary"}" data-yes>${esc(okLabel)}</button></div></div>`;
    const done = (v) => { closeOverlay(); res(v); };
    $("[data-yes]").onclick = () => done(true);
    $("[data-no]").onclick = () => done(false);
    $("[data-x]").onclick = () => done(false);
  });
}

// ------------------------------------------------------------------ boot
async function boot() {
  try { S.pub = await api("/api/config/public"); } catch { S.pub = { linkedin_enabled: false, first_run: false }; }
  try { const r = await api("/api/me", { allow401: true }); S.me = r.user; } catch { S.me = null; }
  window.addEventListener("hashchange", route);
  route();
  setInterval(pollNotifs, 30000);
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
}

async function loadCommon() {
  const [st, us, stats, integ] = await Promise.all([api("/api/settings"), api("/api/users"), api("/api/stats"), api("/api/integrations")]);
  S.settings = st; S.users = us.items; S.stats = stats; S.integrations = integ;
  await pollNotifs(true);
}

async function pollNotifs(silent) {
  if (!S.me || !S.me.approved) return;
  try {
    const n = await api("/api/notifications");
    const top = n.items[0]?.id || 0;
    if (!silent && S.lastUnreadTop && top > S.lastUnreadTop) {
      n.items.filter((x) => x.id > S.lastUnreadTop).reverse().forEach((x) => toast(x.title, x.body.split("\n")[0]));
      if ((parseHash().parts[0] === undefined || parseHash().parts[0] === "leads") && !$(".drawer")) { await refreshStats(); pageLeads($("#main"), currentTab); }
    }
    S.lastUnreadTop = Math.max(S.lastUnreadTop, top);
    S.notifs = n;
    const b = $("#bell-count");
    if (b) { b.textContent = n.unread > 9 ? "9+" : n.unread; b.classList.toggle("hidden", !n.unread); }
  } catch { /* ignore */ }
}

// ------------------------------------------------------------------ router
let shellReady = false;
async function route() {
  const { parts, params } = parseHash();
  const p0 = parts[0] || "";
  if (params.get("error")) setTimeout(() => toast("Sign-in problem", params.get("error"), "err"), 50);
  if (!S.me) {
    shellReady = false;
    if (p0 === "capture") sessionStorage.setItem("ls_capture", location.hash);
    return renderAuth(p0 === "signup" || (S.pub && S.pub.first_run) ? "signup" : "login");
  }
  if (!S.me.approved) { shellReady = false; return renderPending(); }
  if (p0 === "login" || p0 === "signup") return go("#/");
  const pending = sessionStorage.getItem("ls_capture");
  if (pending) { sessionStorage.removeItem("ls_capture"); return go(pending); }
  if (!shellReady) {
    try { await loadCommon(); } catch (e) { return; }
    renderShell(); shellReady = true;
  }
  closeOverlay();
  setActiveNav(p0);
  const main = $("#main");
  if (p0 === "" || p0 === "leads") return pageLeads(main, parts[1] || "new");
  if (p0 === "lead") { if (!$("#feed")) await pageLeads(main, "all"); return openLead(+parts[1]); }
  if (p0 === "add") return pageAdd(main, {});
  if (p0 === "capture") return pageAdd(main, {
    post_url: params.get("u") || "", post_text: params.get("t") || "", author_name: params.get("a") || "",
    author_headline: params.get("h") || "", post_age_text: params.get("g") || "", author_url: params.get("au") || "", source: "capture" });
  if (p0 === "insights") return pageInsights(main);
  if (p0 === "session") return pageSession(main);
  if (p0 === "team") return pageTeam(main);
  if (p0 === "settings") return pageSettings(main, parts[1] || "profile", params);
  go("#/");
}

// ------------------------------------------------------------------ auth screens
function renderAuth(mode) {
  const first = S.pub && S.pub.first_run;
  const li = S.pub && S.pub.linkedin_enabled;
  $("#app").innerHTML = `<div class="auth">
    <section class="auth-hero">
      <div class="brand"><div class="logo-mark">LS</div><div>Lead Scout<small>for LinkedIn</small></div></div>
      <div>
        <h1>Turn LinkedIn posts into a qualified lead pipeline.</h1>
        <p class="lead">Capture posts that mention your keywords, auto-tag intent and lead type, alert your team instantly and track every follow-up to Won.</p>
        <div class="hero-feats">
          <div class="hero-feat"><div class="ic">${ic("bookmark")}</div><div><b>1-click capture from LinkedIn</b><span>Save the post you're reading straight into your team's pipeline.</span></div></div>
          <div class="hero-feat"><div class="ic">${ic("sparkle")}</div><div><b>Auto-qualified</b><span>Keyword match, High-intent tag, lead type, payout model, GEO and contacts.</span></div></div>
          <div class="hero-feat"><div class="ic">${ic("bell")}</div><div><b>Instant team alerts</b><span>In-app, Telegram and Slack. Duplicates blocked automatically.</span></div></div>
        </div>
      </div>
      <div class="dim small">Uses official Sign In with LinkedIn. Your LinkedIn password is never asked for or stored.</div>
    </section>
    <section class="auth-form"><div class="auth-card">
      <div class="brand" style="margin-bottom:26px"><div class="logo-mark">LS</div><div>Lead Scout<small>for LinkedIn</small></div></div>
      <h2>${mode === "signup" ? (first ? "Create the admin account" : "Join your team") : "Welcome back"}</h2>
      <p class="muted" style="margin:0 0 20px">${mode === "signup" ? (first ? "You're the first one here — this account becomes the workspace admin." : "Use your company email. An admin will approve your access.") : "Sign in to your Lead Scout workspace."}</p>
      <div id="auth-err"></div>
      <a class="btn linkedin lg block" href="/auth/linkedin/start?mode=login" ${li ? "" : 'data-li-off="1"'}>${LI_LOGO} ${mode === "signup" ? "Sign up" : "Sign in"} with LinkedIn</a>
      ${li ? "" : '<div class="tiny dim" style="margin-top:6px;text-align:center">LinkedIn sign-in turns on once the admin adds the LinkedIn app keys.</div>'}
      <div class="divider">or with email</div>
      <form id="auth-form" class="stack">
        ${mode === "signup" ? '<div class="field"><label>Full name</label><input class="input" name="name" required minlength="2" autocomplete="name"></div>' : ""}
        <div class="field"><label>Work email</label><input class="input" name="email" type="email" required autocomplete="email"></div>
        <div class="field"><label>Password</label><input class="input" name="password" type="password" required minlength="${mode === "signup" ? 8 : 1}" autocomplete="${mode === "signup" ? "new-password" : "current-password"}">${mode === "signup" ? '<span class="hint">At least 8 characters</span>' : ""}</div>
        <button class="btn primary lg block" type="submit">${mode === "signup" ? "Create account" : "Sign in"}</button>
      </form>
      ${first ? "" : `<p class="muted small" style="text-align:center;margin-top:18px">${mode === "signup" ? 'Already have an account? <a href="#/login">Sign in</a>' : 'New to the team? <a href="#/signup">Create an account</a>'}</p>`}
    </div></section></div>`;
  const off = $("[data-li-off]");
  if (off) off.onclick = (e) => { e.preventDefault(); toast("LinkedIn sign-in not configured", "Admin: add LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET (see README).", "warn"); };
  $("#auth-form").onsubmit = async (e) => {
    e.preventDefault();
    const f = Object.fromEntries(new FormData(e.target));
    const btn = e.target.querySelector("button"); btn.disabled = true;
    try {
      const r = await api(mode === "signup" ? "/api/auth/signup" : "/api/auth/login", { method: "POST", body: f, allow401: true });
      S.me = r.user; S.pub.first_run = false; shellReady = false;
      go(sessionStorage.getItem("ls_capture") || "#/");
    } catch (err) {
      $("#auth-err").innerHTML = `<div class="alert err" style="margin-bottom:14px">${esc(err.message)}</div>`;
      btn.disabled = false;
    }
  };
}

function renderPending() {
  $("#app").innerHTML = `<div class="auth" style="grid-template-columns:1fr"><section class="auth-form"><div class="auth-card" style="text-align:center">
    <div class="empty"><div class="ic">${ic("clock")}</div></div>
    <h2>Waiting for approval</h2>
    <p class="muted">Hi ${esc(S.me.name)}, your account <b>${esc(S.me.email)}</b> was created. An admin needs to approve it before you can see leads.</p>
    <div class="row" style="justify-content:center;margin-top:20px"><button class="btn outline" id="recheck">Check again</button><button class="btn ghost" id="lo">${ic("logout")} Sign out</button></div>
  </div></section></div>`;
  $("#recheck").onclick = async () => { const r = await api("/api/me"); S.me = r.user; route(); if (!S.me.approved) toast("Still pending", "Ask your admin to approve you in Team."); };
  $("#lo").onclick = logout;
}

async function logout() { await api("/api/auth/logout", { method: "POST" }); S.me = null; shellReady = false; go("#/login"); }

// ------------------------------------------------------------------ shell
function avatar(u, cls = "") {
  if (!u) return `<div class="avatar ${cls}">?</div>`;
  const pic = u.picture || (u.linkedin && u.linkedin.picture);
  return `<div class="avatar ${cls}">${pic ? `<img src="${esc(pic)}" alt="" referrerpolicy="no-referrer">` : esc(initials(u.name))}</div>`;
}

function renderShell() {
  const admin = S.me.role === "admin";
  const t = S.stats.tabs;
  $("#app").innerHTML = `
  <header class="topbar">
    <a href="#/" class="brand" style="text-decoration:none;color:inherit"><div class="logo-mark">LS</div><div>Lead Scout<small>for LinkedIn</small></div></a>
    <div class="topsearch"><svg class="i" viewBox="0 0 24 24">${ICONS.search}</svg><input class="input" id="top-q" placeholder="Search posts, authors, notes…"></div>
    <div class="grow"></div>
    <a class="btn primary sm" href="#/add">${ic("plus")} Add lead</a>
    <div style="position:relative"><button class="icon-btn" id="bell" aria-label="Notifications">${ic("bell")}<span class="badge-count hidden" id="bell-count">0</span></button><div id="bell-dd"></div></div>
    <div style="position:relative"><button class="icon-btn" id="me-btn" aria-label="Account">${avatar(S.me)}</button><div id="me-dd"></div></div>
  </header>
  <div class="layout">
    <aside class="side">
      <div class="card me-card">
        ${avatar(S.me, "xl")}
        <div style="font-weight:700;font-size:15px">${esc(S.me.name)}</div>
        <div class="muted small">${admin ? "Admin" : "Member"} · ${esc(S.me.email)}</div>
        ${S.me.linkedin.connected ? `<span class="li-pill on">${LI_LOGO} LinkedIn connected</span>` : `<a class="li-pill off" href="#/settings/profile">${LI_LOGO} Connect LinkedIn</a>`}
      </div>
      <nav class="card nav" style="padding:8px">
        <a href="#/leads/new" data-nav="leads">${ic("home")} Leads <span class="count" id="nav-new">${t.new}</span></a>
        <a href="#/add" data-nav="add">${ic("plus")} Add lead</a>
        <a href="#/session" data-nav="session">${ic("terminal")} Scout session</a>
        <a href="#/insights" data-nav="insights">${ic("chart")} Insights</a>
        ${admin ? `<a href="#/team" data-nav="team">${ic("users")} Team ${S.users.filter((u) => !u.approved).length ? `<span class="count" style="background:#e0443e">${S.users.filter((u) => !u.approved).length}</span>` : ""}</a>` : ""}
        <a href="#/settings" data-nav="settings">${ic("gear")} Settings</a>
      </nav>
      <div class="card pad small">
        <div style="font-weight:600;margin-bottom:6px">Tracking keywords</div>
        <div class="row wrap" style="gap:6px">${S.settings.config.keywords.map((k) => `<span class="chip kw">${esc(k)}</span>`).join("")}</div>
        ${admin ? '<a href="#/settings/workspace" class="tiny" style="display:inline-block;margin-top:10px">Edit keywords →</a>' : ""}
      </div>
    </aside>
    <main class="main" id="main"></main>
  </div>
  <nav class="bottom-nav">
    <a href="#/leads/new" data-nav="leads">${ic("home")}Leads</a>
    <a href="#/session" data-nav="session">${ic("terminal")}Scout</a>
    <a href="#/add" data-nav="add" class="add">${ic("plus")}Add</a>
    ${admin ? `<a href="#/team" data-nav="team">${ic("users")}Team</a>` : `<a href="#/insights" data-nav="insights">${ic("chart")}Insights</a>`}
    <a href="#/settings" data-nav="settings">${ic("gear")}Settings</a>
  </nav>`;
  $("#top-q").addEventListener("keydown", (e) => { if (e.key === "Enter") { S.filters.q = e.target.value.trim(); S.page = 1; go("#/leads/all"); refreshLeads(); } });
  $("#bell").onclick = toggleBell;
  $("#me-btn").onclick = toggleMe;
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#bell") && !e.target.closest("#bell-dd")) { const d = $("#bell-dd"); if (d) d.innerHTML = ""; }
    if (!e.target.closest("#me-btn") && !e.target.closest("#me-dd")) { const d = $("#me-dd"); if (d) d.innerHTML = ""; }
  });
  pollNotifs(true);
}

function setActiveNav(p0) {
  const key = p0 === "" || p0 === "lead" ? "leads" : p0 === "capture" ? "add" : p0;
  $$("[data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === key));
}

function chanLabel(ch) {
  return Object.entries(ch || {}).map(([k, v]) => `${k === "in_app" ? "In-app" : k[0].toUpperCase() + k.slice(1)}: ${v}`).join(" · ");
}

async function toggleBell() {
  const dd = $("#bell-dd");
  if (dd.innerHTML) { dd.innerHTML = ""; return; }
  await pollNotifs(true);
  const items = S.notifs.items;
  dd.innerHTML = `<div class="dropdown"><div class="card-h" style="padding:12px 14px"><b>Notifications</b><span class="tiny muted">Latest 30</span></div>
    ${items.length ? items.map((n) => `<div class="item ${n.unread ? "unread" : ""}" data-lead="${n.lead_id || ""}">
      <div style="color:var(--blue-l);padding-top:2px">${ic(n.lead_id ? "bolt" : "users")}</div>
      <div class="grow"><div style="font-weight:600">${esc(n.title)}</div><div class="muted small" style="white-space:pre-line">${esc(n.body)}</div>
      <div class="tiny dim" style="margin-top:4px">${timeAgo(n.at)}${n.lead_id ? " · " + esc(chanLabel(n.channels)) : ""}</div></div></div>`).join("")
      : `<div class="empty small">No notifications yet</div>`}</div>`;
  $$("[data-lead]", dd).forEach((el) => el.onclick = () => { dd.innerHTML = ""; if (el.dataset.lead) go("#/lead/" + el.dataset.lead); else go("#/team"); });
  if (S.notifs.unread) { await api("/api/notifications/seen", { method: "POST" }); $("#bell-count").classList.add("hidden"); S.notifs.unread = 0; }
}

function toggleMe() {
  const dd = $("#me-dd");
  if (dd.innerHTML) { dd.innerHTML = ""; return; }
  dd.innerHTML = `<div class="dropdown menu" style="width:260px">
    <div class="row" style="padding:14px">${avatar(S.me, "lg")}<div class="grow"><b>${esc(S.me.name)}</b><div class="tiny muted">${esc(S.me.email)}</div></div></div>
    <a href="#/settings/profile">${ic("gear")} Profile & LinkedIn</a>
    <a href="#/leads/progress?owner=me" id="mine-link">${ic("inbox")} My leads</a>
    <button id="lo-btn">${ic("logout")} Sign out</button></div>`;
  $("#lo-btn").onclick = logout;
  $("#mine-link").onclick = (e) => { e.preventDefault(); dd.innerHTML = ""; S.filters.owner = "me"; go("#/leads/progress"); refreshLeads(); };
}

async function refreshStats() {
  S.stats = await api("/api/stats");
  const n = $("#nav-new"); if (n) n.textContent = S.stats.tabs.new;
}

// ------------------------------------------------------------------ leads page
const TABS = [["new", "New"], ["progress", "In progress"], ["old", "Old"], ["history", "History"], ["all", "All"]];
let currentTab = "new";

async function pageLeads(main, tab) {
  try { await refreshStats(); } catch { /* keep old */ }
  const p0 = parseHash().parts[0] || "";
  if (!["", "leads", "lead"].includes(p0)) return; // user navigated away meanwhile
  currentTab = TABS.some((t) => t[0] === tab) ? tab : "new";
  const st = S.stats; const cfg = S.settings.config;
  const f = S.filters;
  main.innerHTML = `
    <div class="page-h"><div><h1>Leads</h1><p class="muted">Posts matching your keywords. New = last ${cfg.active_days} days by post date.</p></div>
      <div class="row"><a class="btn sm ghost" href="/api/leads/export.csv?tab=${currentTab}">${ic("download")} Export CSV</a></div></div>
    <div id="disc-bar"></div>
    ${st.sample_count ? `<div class="sample-banner">${ic("sparkle")} <span><b>Sample data</b> is loaded for the demo (${st.sample_count} posts). Remove it in Settings → Data before real use.</span></div>` : ""}
    <div class="stats">
      <div class="card stat" data-go="#/leads/new"><div class="k" style="color:var(--blue-l)">${ic("inbox")} New</div><div class="v">${st.tabs.new}</div><div class="s">${st.captured_24h} captured in 24h</div></div>
      <div class="card stat" data-intent="High"><div class="k" style="color:var(--green)">${ic("bolt")} High intent</div><div class="v">${st.high_intent_new}</div><div class="s">in New</div></div>
      <div class="card stat" data-go="#/leads/progress"><div class="k" style="color:var(--amber)">${ic("users")} In progress</div><div class="v">${st.tabs.progress}</div><div class="s">${st.my_in_progress} owned by you</div></div>
      <div class="card stat" data-go="#/leads/old"><div class="k">${ic("clock")} Old, verify</div><div class="v">${st.tabs.old}</div><div class="s">untouched > ${cfg.active_days}d</div></div>
      <div class="card stat" data-go="#/leads/history"><div class="k" style="color:var(--green)">${ic("check")} Won</div><div class="v">${st.won}</div><div class="s">${st.win_rate === null ? "no closed leads yet" : st.win_rate + "% win rate"}</div></div>
    </div>
    <div class="card">
      <div class="tabs" style="padding:0 8px">${TABS.map(([k, l]) => `<a href="#/leads/${k}" class="${k === currentTab ? "active" : ""}">${l}${st.tabs[k] !== undefined ? ` <span class="n">${st.tabs[k]}</span>` : ""}</a>`).join("")}</div>
      <div class="filters">
        <input class="input search" id="f-q" placeholder="Search text, author, notes" value="${esc(f.q)}">
        <select class="input" id="f-keyword"><option value="">All keywords</option>${cfg.keywords.map((k) => `<option ${f.keyword === k ? "selected" : ""}>${esc(k)}</option>`).join("")}</select>
        <select class="input" id="f-type"><option value="">All lead types</option>${S.settings.lead_types.map((k) => `<option ${f.lead_type === k ? "selected" : ""}>${esc(k)}</option>`).join("")}</select>
        <select class="input" id="f-source"><option value="">All sources</option>${Object.entries(SOURCE_LABEL).map(([k, v]) => `<option value="${k}" ${f.source === k ? "selected" : ""}>${v}</option>`).join("")}</select>
        <select class="input" id="f-intent"><option value="">Any intent</option><option ${f.intent === "High" ? "selected" : ""}>High</option><option ${f.intent === "Normal" ? "selected" : ""}>Normal</option></select>
        <select class="input" id="f-owner"><option value="">Any owner</option><option value="me" ${f.owner === "me" ? "selected" : ""}>Mine</option>${S.users.filter((u) => u.approved !== false).map((u) => `<option value="${u.id}" ${f.owner == u.id ? "selected" : ""}>${esc(u.name)}</option>`).join("")}</select>
        ${Object.values(f).some(Boolean) ? '<button class="btn ghost sm" id="f-clear">Clear</button>' : ""}
      </div>
    </div>
    <div class="feed" id="feed"><div class="card empty">Loading…</div></div>
    <div class="pager" id="pager"></div>`;
  $$("[data-go]", main).forEach((el) => el.onclick = () => go(el.dataset.go));
  $$("[data-intent]", main).forEach((el) => el.onclick = () => { S.filters.intent = "High"; go("#/leads/new"); pageLeads(main, "new"); });
  const upd = () => { S.page = 1; refreshLeads(); };
  $("#f-q").addEventListener("input", debounce((e) => { S.filters.q = e.target.value.trim(); upd(); }, 300));
  $("#f-keyword").onchange = (e) => { S.filters.keyword = e.target.value; upd(); };
  $("#f-type").onchange = (e) => { S.filters.lead_type = e.target.value; upd(); };
  $("#f-intent").onchange = (e) => { S.filters.intent = e.target.value; upd(); };
  $("#f-source").onchange = (e) => { S.filters.source = e.target.value; upd(); };
  $("#f-owner").onchange = (e) => { S.filters.owner = e.target.value; upd(); };
  renderDiscoveryBar();
  const c = $("#f-clear"); if (c) c.onclick = () => { S.filters = { q: "", keyword: "", lead_type: "", intent: "", owner: "", source: "" }; pageLeads(main, currentTab); };
  await refreshLeads();
}

async function renderDiscoveryBar() {
  const el = $("#disc-bar"); if (!el) return;
  let d; try { d = await api("/api/discovery"); } catch { return; }
  const admin = S.me.role === "admin";
  if (!d.provider) {
    el.innerHTML = `<div class="disc off">${ic("search")}<div class="grow"><b>Auto-discover is off.</b> <span class="muted">Posts with your keywords will appear here automatically once a search API key is added.</span></div>${admin ? '<a class="btn sm outline" href="#/settings/integrations">Set up</a>' : ""}</div>`;
    return;
  }
  const last = d.last;
  const win = { d: "last 24h", w: "last 7 days", m: "last 30 days" }[d.window] || d.window;
  el.innerHTML = `<div class="disc"><span class="live ${d.enabled ? "" : "paused"}"></span><div class="grow">
      <b>Auto-discover ${d.enabled ? "on" : "paused"}</b> <span class="muted">· public LinkedIn posts from the ${win} · every ${d.interval_min} min</span>
      <div class="tiny dim">${d.running ? "Searching now…" : last ? `Last run ${timeAgo(last.finished_at || last.started_at)} · ${last.created} new · ${last.duplicates} already saved${last.errors && last.errors.length ? ` · <span style="color:var(--amber)">${esc(last.errors[0])}</span>` : ""}` : "First run starts shortly after the server starts."}</div></div>
      ${admin ? `<button class="btn sm primary" id="disc-run" ${d.running ? "disabled" : ""}>${ic("search")} Find posts now</button>` : ""}</div>`;
  const b = $("#disc-run");
  if (b) b.onclick = async () => {
    b.disabled = true; b.innerHTML = "Searching…";
    try { const r = await api("/api/discovery/run", { method: "POST" }); toast("Search finished", `${r.created} new posts · ${r.duplicates} already saved`, r.errors && r.errors.length ? "warn" : "ok"); await refreshStats(); return pageLeads($("#main"), currentTab); }
    catch (e) { toast("Search failed", e.message, "err"); }
    renderDiscoveryBar();
  };
}

function embedFrame(l, h = 520) {
  return l.embed_url ? `<div class="embed"><iframe src="${esc(l.embed_url)}" height="${h}" width="100%" frameborder="0" allowfullscreen loading="lazy" title="LinkedIn post preview"></iframe>
    <div class="tiny dim" style="padding:6px 2px">Preview by LinkedIn. Not loading? <a href="${esc(l.post_url)}" target="_blank" rel="noopener">Open the post on LinkedIn</a>.</div></div>` : "";
}

async function refreshLeads(quiet) {
  const feed = $("#feed"); if (!feed) return;
  const f = S.filters;
  const qs = new URLSearchParams({ tab: currentTab, page: S.page, per_page: 20, ...Object.fromEntries(Object.entries(f).filter(([, v]) => v)) });
  try {
    const r = await api("/api/leads?" + qs);
    if (!quiet) await refreshStats();
    if (!r.items.length) {
      feed.innerHTML = `<div class="card empty"><div class="ic">${ic("inbox")}</div>
        <h3 style="color:var(--text)">${Object.values(f).some(Boolean) ? "No leads match these filters" : { new: "No new leads right now", progress: "Nothing in progress", old: "No old untouched posts", history: "No closed leads yet", all: "No leads yet" }[currentTab]}</h3>
        <p>Capture a post from LinkedIn or paste one manually.</p>
        <div class="row" style="justify-content:center;margin-top:10px"><a class="btn primary" href="#/add">${ic("plus")} Add lead</a>
        ${S.me.role === "admin" && !S.stats.total ? '<button class="btn outline" id="load-sample">Load sample data</button>' : ""}</div></div>`;
      const ls = $("#load-sample"); if (ls) ls.onclick = loadSample;
    } else {
      window.__leads = Object.fromEntries(r.items.map((x) => [x.id, x]));
      feed.innerHTML = r.items.map(postCard).join("");
      bindPostCards(feed);
    }
    const pages = Math.ceil(r.total / r.per_page);
    $("#pager").innerHTML = pages > 1 ? `<button class="btn sm" ${S.page <= 1 ? "disabled" : ""} id="pg-prev">Previous</button><span class="muted small" style="align-self:center">Page ${S.page} of ${pages} · ${r.total} leads</span><button class="btn sm" ${S.page >= pages ? "disabled" : ""} id="pg-next">Next</button>` : r.total ? `<span class="muted small">${r.total} lead${r.total > 1 ? "s" : ""}</span>` : "";
    const pv = $("#pg-prev"), nx = $("#pg-next");
    if (pv) pv.onclick = () => { S.page--; refreshLeads(); window.scrollTo(0, 0); };
    if (nx) nx.onclick = () => { S.page++; refreshLeads(); window.scrollTo(0, 0); };
  } catch (e) { feed.innerHTML = `<div class="card empty">${esc(e.message)}</div>`; }
}

function highlight(text, kws) {
  let h = esc(text);
  const sorted = [...(kws || [])].sort((a, b) => b.length - a.length);
  for (const k of sorted) {
    const re = new RegExp("(?<![A-Za-z0-9])(" + esc(k).replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")(?![A-Za-z0-9])", "gi");
    h = h.replace(re, "<mark>$1</mark>");
  }
  return h.replace(/(^|[^&\w])(#[A-Za-z][A-Za-z0-9_]*)/g, '$1<span style="color:var(--blue-l);font-weight:600">$2</span>');
}

const SOURCE_LABEL = { manual: "Manual", capture: "1-click capture", webhook: "Vendor", sample: "Sample data", search: "Auto-discovered", session: "Scout session" };
const PAGE_LABEL = { person: "Person profile", company: "Company page", product: "Product listing", job: "Job", page: "Web page", search: "Search page" };
const SITE_LABEL = { indiamart: "IndiaMART", tradeindia: "TradeIndia", web: "Website", linkedin: "LinkedIn" };

function postCard(l) {
  const statusOpts = S.settings.statuses.map((s) => `<option ${s === l.status ? "selected" : ""}>${s}</option>`).join("");
  const c = l.contacts || {};
  const nContacts = (c.emails || []).length + (c.phones || []).length + (c.whatsapp || []).length;
  return `<article class="card post ${l.intent === "High" && l.status === "New" ? "high" : ""}" data-id="${l.id}">
    <div class="post-h">
      ${avatar({ name: l.author_name }, "lg")}
      <div class="who">
        <div class="name">${l.author_url ? `<a href="${esc(l.author_url)}" target="_blank" rel="noopener">${esc(l.author_name || "Unknown author")}</a>` : esc(l.author_name || "Unknown author")}
          ${l.is_sample ? '<span class="chip sample">Sample data</span>' : ""}</div>
        ${l.author_headline ? `<div class="headline">${esc(l.author_headline)}</div>` : ""}
        <div class="meta"><span title="${l.post_date ? "Post date ≈ " + esc(fmtDate(l.post_date)) : "Post date unknown"}">${esc(l.age_label)}</span> • <span>${esc(SOURCE_LABEL[l.source] || l.source)}</span>
          ${l.added_by ? ` • <span>added by ${esc(l.added_by.name)}</span>` : ""}</div>
      </div>
      <a class="icon-btn" href="${esc(l.post_url)}" target="_blank" rel="noopener" title="Open on LinkedIn">${ic("ext")}</a>
    </div>
    <div class="post-body clamp">${highlight(l.post_text, l.keywords)}</div>
    <button class="see-more" data-more>…see more</button>
    ${l.source === "search" ? '<div class="tiny dim" style="padding:0 16px 4px">Search snippet. Open the preview for the full post.</div>' : ""}
    <div class="embed-holder" data-embed></div>
    <div class="post-tags">
      ${l.intent === "High" ? `<span class="chip high" title="${esc((l.intent_words || []).join(", "))}">${ic("bolt")} High intent</span>` : ""}
      ${l.old_verify ? '<span class="chip">Old, verify</span>' : ""}
      ${l.age_label === "Date unknown" ? '<span class="chip">Date unknown</span>' : ""}
      ${l.page_type && l.page_type !== "post" ? `<span class="chip outline">${esc(PAGE_LABEL[l.page_type] || l.page_type)}</span>` : ""}
      ${l.site && l.site !== "linkedin" ? `<span class="chip outline">${esc(SITE_LABEL[l.site] || l.site)}</span>` : ""}
      ${l.tag ? `<span class="chip outline">#${esc(l.tag)}</span>` : ""}
      ${l.compliance_flag ? `<span class="chip warn" title="${esc(l.compliance_terms.join(", "))}">${ic("shield")} Compliance review</span>` : ""}
      ${(l.keywords || []).map((k) => `<span class="chip kw">${esc(k)}</span>`).join("")}
      ${(l.lead_types || []).map((t) => `<span class="chip violet">${esc(t)}</span>`).join("")}
      ${l.vertical ? `<span class="chip outline">${esc(l.vertical)}</span>` : ""}
      ${(l.campaign_models || []).map((m) => `<span class="chip outline">${esc(m)}</span>`).join("")}
      ${l.geo ? `<span class="chip outline">📍 ${esc(l.geo)}</span>` : ""}
      ${nContacts ? `<span class="chip outline">${ic("phone")} ${nContacts} contact${nContacts > 1 ? "s" : ""}</span>` : ""}
    </div>
    <div class="post-f">
      <select class="input st-${esc(l.status)}" data-status aria-label="Status">${statusOpts}</select>
      <span class="owner">${l.owner ? `${avatar(l.owner)} ${esc(l.owner.name)}` : "No owner"}</span>
      <span class="spacer"></span>
      ${!l.owner || l.owner.id !== S.me.id ? '<button class="btn ghost sm" data-claim>Assign to me</button>' : ""}
      ${l.embed_url ? '<button class="btn ghost sm" data-preview>Preview post</button>' : ""}
      <button class="btn outline sm" data-open>Details</button>
    </div>
  </article>`;
}

function bindPostCards(root) {
  $$(".post", root).forEach((card) => {
    const id = +card.dataset.id;
    const body = $(".post-body", card), more = $("[data-more]", card);
    requestAnimationFrame(() => { if (body.scrollHeight <= body.clientHeight + 2) more.classList.add("hidden"); });
    more.onclick = () => { body.classList.toggle("clamp"); more.textContent = body.classList.contains("clamp") ? "…see more" : "show less"; };
    $("[data-status]", card).onchange = async (e) => {
      try {
        await api(`/api/leads/${id}`, { method: "PATCH", body: { status: e.target.value } });
        toast("Status updated", `Moved to ${e.target.value}`, "ok"); refreshLeads();
      } catch (err) { toast("Couldn't update", err.message, "err"); }
    };
    const claim = $("[data-claim]", card);
    if (claim) claim.onclick = async () => { await api(`/api/leads/${id}`, { method: "PATCH", body: { owner_id: S.me.id } }); toast("Assigned to you", "", "ok"); refreshLeads(true); };
    $("[data-open]", card).onclick = () => go("#/lead/" + id);
    const pv = $("[data-preview]", card);
    if (pv) pv.onclick = () => {
      const h = $("[data-embed]", card);
      if (h.innerHTML) { h.innerHTML = ""; pv.textContent = "Preview post"; return; }
      const l = window.__leads && window.__leads[id];
      h.innerHTML = `<div style="padding:0 16px 12px">${embedFrame(l)}</div>`; pv.textContent = "Hide preview";
    };
  });
}

async function loadSample() {
  const r = await api("/api/admin/sample", { method: "POST" });
  toast("Sample data loaded", `${r.created} demo posts added`, "ok");
  await refreshStats(); route();
}

// ------------------------------------------------------------------ lead drawer
async function openLead(id) {
  let r;
  try { r = await api(`/api/leads/${id}`); } catch (e) { toast("Lead not found", e.message, "err"); return go("#/leads/" + currentTab); }
  const l = r.lead; const c = l.contacts || {};
  const canDelete = S.me.role === "admin" || (l.added_by && l.added_by.id === S.me.id);
  document.body.style.overflow = "hidden";
  $("#modal-root").innerHTML = `<div class="overlay" data-close></div>
  <aside class="drawer" role="dialog" aria-label="Lead details">
    <div class="drawer-h"><b class="grow">Lead #${l.id}</b>
      <a class="btn primary sm" href="${esc(l.post_url)}" target="_blank" rel="noopener">${LI_LOGO} Open post</a>
      <button class="icon-btn" data-close aria-label="Close">${ic("x")}</button></div>
    <div class="drawer-b">
      ${l.is_sample ? '<div class="sample-banner">Sample data — not a real post or person.</div>' : ""}
      ${l.compliance_flag ? `<div class="alert warn">${ic("shield")} <b>Compliance review:</b> mentions ${esc(l.compliance_terms.join(", "))}. Get company approval before contacting.</div>` : ""}
      ${l.old_verify ? `<div class="alert info"><b>Old, verify:</b> this post is older than ${S.settings.config.active_days} days. Confirm the requirement is still open.</div>` : ""}
      <div class="card">
        <div class="post-h" style="padding-bottom:4px">${avatar({ name: l.author_name }, "lg")}<div class="who">
          <div class="name">${l.author_url ? `<a href="${esc(l.author_url)}" target="_blank" rel="noopener">${esc(l.author_name || "Unknown author")}</a>` : esc(l.author_name || "Unknown author")}</div>
          <div class="headline">${esc(l.author_headline)}</div>
          <div class="meta">${esc(l.age_label)} • ${l.post_date ? "≈ " + esc(fmtDate(l.post_date)) : "Date unknown"}</div></div></div>
        <div class="post-body" style="padding-bottom:14px">${highlight(l.post_text, l.keywords)}</div>
      </div>
      ${l.embed_url && !l.is_sample ? `<div class="card card-b"><div class="row between" style="margin-bottom:10px"><h3>LinkedIn post preview</h3><span class="tiny dim">official LinkedIn embed</span></div>${embedFrame(l, 600)}</div>` : ""}
      <div class="grid2">
        <div class="field"><label>Status</label><select class="input" id="d-status">${S.settings.statuses.map((s) => `<option ${s === l.status ? "selected" : ""}>${s}</option>`).join("")}</select></div>
        <div class="field"><label>Owner</label><select class="input" id="d-owner"><option value="">— No owner —</option>${S.users.filter((u) => u.approved !== false).map((u) => `<option value="${u.id}" ${l.owner && l.owner.id === u.id ? "selected" : ""}>${esc(u.name)}</option>`).join("")}</select></div>
      </div>
      <div class="field"><label>Lead type <span class="dim">(auto-suggested — confirm)</span></label>
        <div class="row wrap" style="gap:8px" id="d-types">${S.settings.lead_types.map((t) => `<label class="check"><input type="checkbox" value="${esc(t)}" ${l.lead_types.includes(t) ? "checked" : ""}> ${esc(t)}</label>`).join("")}</div></div>
      <div class="grid2">
        <div class="field"><label>Vertical</label><select class="input" id="d-vertical"><option value="">—</option>${S.settings.verticals.map((v) => `<option ${v === l.vertical ? "selected" : ""}>${esc(v)}</option>`).join("")}${l.vertical && !S.settings.verticals.includes(l.vertical) ? `<option selected>${esc(l.vertical)}</option>` : ""}</select></div>
        <div class="field"><label>GEO</label><input class="input" id="d-geo" value="${esc(l.geo)}"></div>
      </div>
      <div class="field"><label>Campaign model</label><div class="row wrap" style="gap:8px" id="d-models">${S.settings.campaign_models.map((m) => `<label class="check"><input type="checkbox" value="${m}" ${l.campaign_models.includes(m) ? "checked" : ""}> ${m}</label>`).join("")}</div></div>
      <div class="field"><label>Notes</label><textarea class="input" id="d-notes" style="min-height:90px" placeholder="Follow-up notes, who you spoke to, next step…">${esc(l.notes)}</textarea></div>
      <div class="row"><button class="btn primary" id="d-save">${ic("check")} Save changes</button><span class="grow"></span>
        ${canDelete ? `<button class="btn danger sm" id="d-del">${ic("trash")} Delete</button>` : ""}</div>
      <div class="card card-b"><h3 style="margin-bottom:12px">Details</h3><dl class="kv">
        <dt>Keywords</dt><dd>${(l.keywords || []).map((k) => `<span class="chip kw">${esc(k)}</span>`).join(" ") || "—"}</dd>
        <dt>Intent</dt><dd>${l.intent === "High" ? `<span class="chip high">High</span> <span class="muted small">${esc(l.intent_words.join(", "))}</span>` : "Normal"}</dd>
        <dt>Emails</dt><dd>${(c.emails || []).map((e) => `<a href="mailto:${esc(e)}">${esc(e)}</a>`).join(", ") || "—"}</dd>
        <dt>Phones</dt><dd>${(c.phones || []).map((p) => `<a href="tel:${esc(p.replace(/\s/g, ""))}">${esc(p)}</a>`).join(", ") || "—"}</dd>
        <dt>WhatsApp</dt><dd>${(c.whatsapp || []).map((w) => `<a href="${esc(w.startsWith("http") ? w : "https://" + w)}" target="_blank" rel="noopener">${esc(w)}</a>`).join(", ") || "—"}</dd>
        <dt>Links in post</dt><dd>${(c.links || []).map((w) => `<a href="${esc(w)}" target="_blank" rel="noopener nofollow">${esc(w)}</a>`).join("<br>") || "—"}</dd>
        <dt>Source</dt><dd>${esc(SOURCE_LABEL[l.source] || l.source)}</dd>
        <dt>Added by</dt><dd>${l.added_by ? esc(l.added_by.name) : "System"} · ${esc(fmtDate(l.captured_at))}</dd>
        <dt>Post link</dt><dd><a href="${esc(l.post_url)}" target="_blank" rel="noopener">${esc(l.post_url)}</a></dd>
      </dl><p class="tiny dim" style="margin:12px 0 0">Contacts are for business follow-up only — no bulk WhatsApp or auto-email.</p></div>
      <div class="card card-b"><h3 style="margin-bottom:8px">Activity</h3><div class="timeline">
        ${r.activity.map((a) => `<div class="t"><div><b>${esc(a.user)}</b> <span class="muted">${esc(a.action)}</span><div class="tiny dim">${esc(fmtDate(a.at))}</div></div></div>`).join("")}</div></div>
    </div></aside>`;
  const close = () => { closeOverlay(); if (parseHash().parts[0] === "lead") history.replaceState(null, "", "#/leads/" + currentTab); refreshLeads(true); };
  $$("[data-close]").forEach((b) => b.onclick = close);
  document.onkeydown = (e) => { if (e.key === "Escape" && $(".drawer")) close(); };
  $("#d-save").onclick = async () => {
    const owner = $("#d-owner").value;
    const body = { status: $("#d-status").value, notes: $("#d-notes").value, geo: $("#d-geo").value, vertical: $("#d-vertical").value,
      lead_types: $$("#d-types input:checked").map((i) => i.value), campaign_models: $$("#d-models input:checked").map((i) => i.value) };
    if (owner) body.owner_id = +owner; else body.clear_owner = !!l.owner;
    try { await api(`/api/leads/${id}`, { method: "PATCH", body }); toast("Lead saved", "", "ok"); await refreshStats(); openLead(id); refreshLeads(true); }
    catch (e) { toast("Couldn't save", e.message, "err"); }
  };
  const del = $("#d-del");
  if (del) del.onclick = async () => {
    if (!(await confirmBox("Delete this lead?", "This removes the lead and its activity. This can't be undone.", "Delete", true))) return openLead(id);
    await api(`/api/leads/${id}`, { method: "DELETE" }); toast("Lead deleted", "", "ok"); closeOverlay(); go("#/leads/" + currentTab); refreshLeads();
  };
}

// ------------------------------------------------------------------ add lead
function bookmarkletCode() {
  const src = `(function(){var B=${JSON.stringify(location.origin)};var W=window.getSelection?window.getSelection():null;var s=W?String(W).trim():"";var n=W&&W.anchorNode;var e=n?(n.nodeType===1?n:n.parentElement):null;var Q='[data-urn*="activity:"],[data-urn*="ugcPost:"],[data-id*="activity:"],[data-id*="ugcPost:"]';var b=e&&e.closest?e.closest(Q):null;if(!b&&/\\/(posts|feed\\/update)\\//.test(location.pathname))b=document.querySelector(Q);function t(q){if(!b)return"";var x=b.querySelector(q);return x?x.innerText.trim():""}var urn=b?(b.getAttribute("data-urn")||b.getAttribute("data-id")):"";var u=urn?"https://www.linkedin.com/feed/update/"+urn+"/":location.href.split("?")[0];var txt=s||t(".update-components-text, .feed-shared-update-v2__description, .feed-shared-text");var a=t(".update-components-actor__title span[aria-hidden=true], .update-components-actor__name span[aria-hidden=true], .update-components-actor__title");var h=t(".update-components-actor__description span[aria-hidden=true], .update-components-actor__description");var g=t(".update-components-actor__sub-description span[aria-hidden=true], .update-components-actor__sub-description");var m=g.match(/(\\d+\\s?(?:mo|yr|m|h|d|w))\\b/);var al=b?b.querySelector("a.update-components-actor__meta-link, a.update-components-actor__image, a[href*='/in/'], a[href*='/company/']"):null;var p=new URLSearchParams({u:u,t:txt.slice(0,6000),a:a.split("\\n")[0],h:h.split("\\n")[0],g:m?m[1].replace(" ",""):"",au:al?al.href.split("?")[0]:""});window.open(B+"/#/capture?"+p.toString(),"leadscout","width=1180,height=880")})();`;
  return "javascript:" + encodeURIComponent(src);
}

function pageAdd(main, pre) {
  const fromCapture = pre.source === "capture";
  main.innerHTML = `
    <div class="page-h"><div><h1>${fromCapture ? "Review captured post" : "Add lead"}</h1>
      <p class="muted">${fromCapture ? "Captured from LinkedIn. Check the details, then save." : "Paste a LinkedIn post — keywords, intent, lead type and contacts are detected automatically."}</p></div></div>
    ${fromCapture ? `<div class="alert ok">${ic("check")} Post captured from LinkedIn. Fields LinkedIn didn't expose can be filled below.</div>` : ""}
    <div class="add-grid">
      <form class="card" id="add-form"><div class="card-h"><h3>Post details</h3><span class="tiny muted">* required</span></div>
        <div class="card-b stack">
          <div class="field"><label>LinkedIn post link *</label><input class="input" name="post_url" required placeholder="https://www.linkedin.com/posts/…  or  …/feed/update/urn:li:activity:…" value="${esc(pre.post_url || "")}">
            <span class="hint">Tip: on LinkedIn, click ••• on the post → "Copy link to post". The post date is read from the link automatically.</span></div>
          <div class="field"><label>Post text *</label><textarea class="input" name="post_text" required placeholder="Paste the full post text here…">${esc(pre.post_text || "")}</textarea></div>
          <div class="grid2">
            <div class="field"><label>Author name</label><input class="input" name="author_name" value="${esc(pre.author_name || "")}" placeholder="e.g. Riya Sharma"></div>
            <div class="field"><label>Post age on LinkedIn</label><input class="input" name="post_age_text" value="${esc(pre.post_age_text || "")}" placeholder="3h, 5d, 2w, 2mo"><span class="hint">Only needed if the link has no date</span></div>
          </div>
          <div class="field"><label>Author headline</label><input class="input" name="author_headline" value="${esc(pre.author_headline || "")}" placeholder="e.g. Affiliate Manager at …"></div>
          <input type="hidden" name="author_url" value="${esc(pre.author_url || "")}">
          <div class="field"><label>Lead type <span class="dim">(auto-selected — adjust if needed)</span></label>
            <div class="row wrap" style="gap:8px" id="a-types">${S.settings.lead_types.map((t) => `<label class="check"><input type="checkbox" value="${esc(t)}"> ${esc(t)}</label>`).join("")}</div></div>
          <div class="field"><label>Notes</label><input class="input" name="notes" placeholder="Optional"></div>
          <div id="add-msg"></div>
          <div class="row"><button class="btn primary lg" type="submit" id="add-submit">${ic("check")} Save lead</button>
            <span class="muted small">Team gets an alert instantly.</span></div>
        </div></form>
      <div class="stack">
        <div class="card"><div class="card-h"><h3>${ic("sparkle")} Auto-detected</h3><span class="tiny muted" id="det-status">Start typing…</span></div>
          <div class="card-b detect" id="detect"><div class="muted small">Paste a post to see keyword match, intent, lead type, campaign model, GEO and contacts.</div></div></div>
        <div class="card"><div class="card-h"><h3>${ic("bookmark")} 1-click capture from LinkedIn</h3></div>
          <div class="card-b stack">
            <div class="bm"><a class="bm-btn" id="bm" title="Drag me to your bookmarks bar">${ic("bookmark")} Save to Lead Scout</a><span class="muted small">← drag this to your browser's bookmarks bar (one time)</span></div>
            <ol class="steps">
              <li><span>Search your keyword on LinkedIn and pick the <b>Posts</b> filter.</span></li>
              <li><span>On a useful post, select its text (or open the post) and click <b>Save to Lead Scout</b> in your bookmarks bar.</span></li>
              <li><span>This page opens pre-filled with the link, text and author. Check it and save.</span></li>
            </ol>
            <p class="tiny dim" style="margin:0">Works in your own logged-in LinkedIn tab, one post per click. Lead Scout never asks for your LinkedIn password and doesn't run automated searches.</p>
          </div></div>
      </div>
    </div>`;
  $("#bm").setAttribute("href", bookmarkletCode());
  $("#bm").onclick = (e) => { e.preventDefault(); toast("Drag it, don't click it", "Drag the blue button onto your bookmarks bar, then use it on LinkedIn.", "warn"); };
  const form = $("#add-form");
  let last = null;
  const run = debounce(async () => {
    const fd = new FormData(form);
    const text = fd.get("post_text"), url = fd.get("post_url");
    if (!text && !url) return;
    $("#det-status").textContent = "Analyzing…";
    try {
      const a = await api("/api/leads/analyze", { method: "POST", body: { text, url, age_text: fd.get("post_age_text") } });
      last = a; renderDetect(a);
      // auto-check lead types the first time
      if (!form.dataset.typesTouched) $$("#a-types input").forEach((i) => { i.checked = a.lead_types.includes(i.value); });
      $("#det-status").textContent = "Updated";
    } catch (e) { $("#det-status").textContent = e.message; }
  }, 350);
  form.addEventListener("input", (e) => { if (e.target.closest("#a-types")) form.dataset.typesTouched = "1"; else run(); });
  if (pre.post_text || pre.post_url) run();

  form.onsubmit = async (e) => {
    e.preventDefault();
    await submitLead(form, pre.source || "manual", false);
  };
}

async function submitLead(form, source, allowNoKw) {
  const fd = Object.fromEntries(new FormData(form));
  const body = { ...fd, lead_types: $$("#a-types input:checked").map((i) => i.value), source, allow_no_keyword: allowNoKw };
  const btn = $("#add-submit"); btn.disabled = true;
  $("#add-msg").innerHTML = "";
  try {
    const r = await api("/api/leads", { method: "POST", body });
    toast("Lead saved & team notified", chanLabel(r.notification.channels), "ok");
    await refreshStats();
    if (window.opener && source === "capture") { setTimeout(() => window.close(), 900); }
    go("#/lead/" + r.lead.id);
  } catch (err) {
    btn.disabled = false;
    if (err.status === 409 && err.data && err.data.duplicate) {
      const d = err.data.duplicate;
      $("#add-msg").innerHTML = `<div class="alert warn"><b>Duplicate — already in Lead Scout.</b><br>Added by ${esc(d.added_by)} · ${esc(timeAgo(d.captured_at))} · status <b>${esc(d.status)}</b>${d.owner ? " · owner " + esc(d.owner) : ""}. <a href="#/lead/${d.lead_id}">Open existing lead →</a></div>`;
    } else if (err.status === 422 && /keyword/i.test(err.message)) {
      if (await confirmBox("No tracked keyword found", "This post doesn't mention any of your keywords. Save it anyway?", "Save anyway")) submitLead(form, source, true);
    } else {
      $("#add-msg").innerHTML = `<div class="alert err">${esc(err.message)}</div>`;
    }
  }
}

function renderDetect(a) {
  const c = a.contacts || {};
  const contacts = [...(c.emails || []).map((x) => "✉️ " + x), ...(c.phones || []).map((x) => "📞 " + x), ...(c.whatsapp || []).map((x) => "💬 " + x)];
  $("#detect").innerHTML = `
    ${a.duplicate ? `<div class="alert warn"><b>Duplicate:</b> ${esc(a.duplicate.message)}. <a href="#/lead/${a.duplicate.lead_id}">Open →</a></div>` : ""}
    ${a.is_linkedin === false ? '<div class="alert err">This is not a linkedin.com link.</div>' : ""}
    ${a.compliance_flag ? `<div class="alert warn">${ic("shield")} <b>Compliance review</b> — mentions ${esc(a.compliance_terms.join(", "))}. Get approval before contacting.</div>` : ""}
    <div class="rowk"><span>Keywords</span><span>${a.keywords.length ? a.keywords.map((k) => `<span class="chip kw">${esc(k)}</span>`).join(" ") : '<span class="chip red">No keyword match</span>'}</span></div>
    <div class="rowk"><span>Intent</span><span>${a.intent === "High" ? `<span class="chip high">${ic("bolt")} High</span> <span class="muted small">${esc(a.intent_words.join(", "))}</span>` : '<span class="chip">Normal</span>'}</span></div>
    <div class="rowk"><span>Lead type</span><span>${a.lead_types.map((t) => `<span class="chip violet">${esc(t)}</span>`).join(" ") || '<span class="dim">—</span>'}</span></div>
    <div class="rowk"><span>Vertical</span><span>${esc(a.vertical) || '<span class="dim">—</span>'}</span></div>
    <div class="rowk"><span>Campaign model</span><span>${a.campaign_models.map((m) => `<span class="chip outline">${m}</span>`).join(" ") || '<span class="dim">—</span>'}</span></div>
    <div class="rowk"><span>GEO</span><span>${esc(a.geo) || '<span class="dim">—</span>'}</span></div>
    <div class="rowk"><span>Post date</span><span>${a.post_date ? `${esc(fmtDate(a.post_date + "Z"))} <span class="muted small">(from ${a.post_date_source === "link" ? "post link" : "age " + esc(a.post_age_text)})</span>` : '<span class="chip">Date unknown</span>'}</span></div>
    <div class="rowk"><span>Contacts</span><span>${contacts.length ? contacts.map((x) => `<div class="small">${esc(x)}</div>`).join("") : '<span class="dim">—</span>'}</span></div>`;
}

// ------------------------------------------------------------------ scout session
async function pageSession(main) {
  const d = await api("/api/session/today");
  const server = location.origin;
  const bar = (site) => { const n = d.mine[site], c = d.caps[site]; return `<div class="bar"><span>${SITE_LABEL[site]}</span><div class="track"><div class="fill" style="width:${Math.min(100, (n / c) * 100)}%;${n >= c ? "background:var(--red)" : ""}"></div></div><span class="muted small">${n} / ${c}</span></div>`; };
  const upd = `Date: ${d.date} | Target: ${d.tags.join(", ") || "—"}\nCaptures: LI ${d.by_site.linkedin}, IM ${d.by_site.indiamart}, TI ${d.by_site.tradeindia}, Web ${d.by_site.web} | New leads: ${d.new_leads}\nTop 3: ${d.top.map((t) => `[${t.name}, ${t.intent === "High" ? "High" : "Normal"}]`).join(" ") || "—"} | Warnings: none`;
  main.innerHTML = `
    <div class="page-h"><div><h1>Scout session</h1><p class="muted">Human-driven Playwright session from the Parivestra guide. You browse; press Enter to send the page here as a lead.</p></div>
      <a class="btn sm outline" href="/scout/scout_session.py" download>${ic("download")} Download script</a></div>
    <div class="card"><div class="card-h"><h3>How it flows</h3></div><div class="card-b">
      <div class="flow">${["You search on LinkedIn / IndiaMART", "Open a profile, company or post", "Press Enter in the terminal", "Lead appears here, auto-tagged", "Team gets an alert"].map((t, i) => `<div class="fstep"><b>${i + 1}</b><span>${t}</span></div>`).join("")}</div></div></div>
    <div class="grid2" style="align-items:start">
      <div class="card"><div class="card-h"><h3>My captures today</h3><span class="tiny muted">limits reset at midnight IST</span></div><div class="card-b bars">${Object.keys(d.caps).map(bar).join("")}</div></div>
      <div class="card"><div class="card-h"><h3>Daily update</h3><button class="btn sm ghost" id="cp-upd">${ic("copy")} Copy</button></div><div class="card-b"><div class="code" id="upd">${esc(upd)}</div><p class="tiny dim" style="margin:8px 0 0">Paste in the group at the end of the day (guide section 10). Edit "Warnings" if LinkedIn showed any.</p></div></div>
    </div>
    <div class="card"><div class="card-h"><h3>Team today</h3></div>
      ${d.members.length ? `<div style="overflow-x:auto"><table class="table"><thead><tr><th>Member</th><th>LinkedIn</th><th>IndiaMART</th><th>TradeIndia</th><th>Web</th></tr></thead><tbody>${d.members.map((m) => `<tr><td><b>${esc(m.name)}</b></td><td>${m.linkedin}</td><td>${m.indiamart}</td><td>${m.tradeindia}</td><td>${m.web}</td></tr>`).join("")}</tbody></table></div>` : '<div class="card-b muted small">No session captures yet today.</div>'}</div>
    <div class="card"><div class="card-h"><h3>${ic("terminal")} Set up on your laptop (one time)</h3></div><div class="card-b stack">
      <ol class="steps">
        <li><span>Install Python 3.11+ (Windows: tick "Add python.exe to PATH").</span></li>
        <li><span>In PowerShell:<div class="code" style="margin-top:6px">mkdir smartscout-session; cd smartscout-session
python -m venv .venv; .venv\\Scripts\\Activate.ps1
pip install playwright requests
python -m playwright install chromium</div></span></li>
        <li><span>Click <b>Download script</b> (top right) and put <code>scout_session.py</code> in that folder.</span></li>
        <li><span>Connect it to your Lead Scout account:<div id="tok-box" style="margin-top:8px">${d.has_token ? '<div class="alert info">You already have a token. Generate a new one only if you lost it (the old one stops working).</div>' : ""}<button class="btn primary sm" id="gen-tok" style="margin-top:8px">${d.has_token ? "Generate new token" : "Generate my token"}</button></div></span></li>
        <li><span>Run a session:<div class="code" style="margin-top:6px">python scout_session.py --site linkedin --by "${esc(S.me.name.split(" ")[0].toLowerCase())}" --tag "affiliate-partners"</div>Log in to LinkedIn by hand in the window that opens. Open a post, profile or company page and press <b>Enter</b> in the terminal.</span></li>
      </ol></div></div>
    <div class="card"><div class="card-h"><h3>${ic("shield")} Rules</h3></div><div class="card-b grid2 small">
      <div><b style="color:var(--green)">Do</b><ul class="rules"><li>Use your own real account, log in by hand</li><li>Keep the browser visible, drive it yourself</li><li>Capture business information only</li><li>Stop the moment LinkedIn shows a warning</li></ul></div>
      <div><b style="color:var(--red)">Don't</b><ul class="rules"><li>Headless, stealth plugins, proxies or extra accounts</li><li>Auto-scroll, auto-click, auto-connect or auto-message</li><li>Solve or bypass CAPTCHAs</li><li>Share cookies, the profile folder, passwords or your token</li><li>Capture students or minors</li></ul></div>
      <div class="tiny dim" style="grid-column:1/-1">Limits: 60 LinkedIn captures and 25 searches a day (our own safety numbers, not official LinkedIn figures). India's DPDP Act applies to personal data: collect only what B2B outreach needs.</div></div></div>`;
  $("#cp-upd").onclick = () => { navigator.clipboard.writeText($("#upd").textContent); toast("Copied", "Paste it in the group", "ok"); };
  $("#gen-tok").onclick = async () => {
    if (d.has_token && !(await confirmBox("Generate a new token?", "Your old token will stop working on your laptop.", "Generate"))) return;
    const r = await api("/api/me/scout-token", { method: "POST" });
    $("#tok-box").innerHTML = `<div class="alert warn">Copy this now. It is shown only once. Don't share it.</div>
      <div class="code" style="margin-top:8px" id="tok-cmd">setx LEADSCOUT_URL "${esc(r.server || server)}"
setx LEADSCOUT_TOKEN "${esc(r.token)}"</div>
      <div class="row" style="margin-top:8px"><button class="btn sm outline" id="cp-tok">${ic("copy")} Copy commands</button><span class="tiny muted">Run in PowerShell, then open a new terminal.</span></div>`;
    $("#cp-tok").onclick = () => { navigator.clipboard.writeText($("#tok-cmd").textContent); toast("Copied", "Paste in PowerShell", "ok"); };
  };
}

// ------------------------------------------------------------------ insights
async function pageInsights(main) {
  await refreshStats();
  const st = S.stats;
  const maxKw = Math.max(1, ...st.keywords.map((k) => k.total));
  const maxT = Math.max(1, ...st.won_by_type.map((k) => k.won));
  main.innerHTML = `
    <div class="page-h"><div><h1>Insights</h1><p class="muted">Which keywords and lead types turn into wins.</p></div></div>
    <div class="stats">
      <div class="card stat"><div class="k">Total leads</div><div class="v">${st.total}</div></div>
      <div class="card stat"><div class="k">Won</div><div class="v" style="color:var(--green)">${st.won}</div></div>
      <div class="card stat"><div class="k">Lost</div><div class="v" style="color:var(--red)">${st.lost}</div></div>
      <div class="card stat"><div class="k">Win rate</div><div class="v">${st.win_rate === null ? "—" : st.win_rate + "%"}</div></div>
      <div class="card stat"><div class="k">Compliance open</div><div class="v" style="color:var(--amber)">${st.compliance_open}</div></div>
    </div>
    <div class="card"><div class="card-h"><h3>Leads by keyword</h3><span class="row small muted"><span class="dot" style="color:var(--blue2)"></span>Total <span class="dot" style="color:var(--green);margin-left:8px"></span>Won</span></div>
      <div class="card-b bars">${st.keywords.length ? st.keywords.map((k) => `<div class="bar"><span>${esc(k.keyword)}</span><div class="track"><div class="fill" style="width:${(k.total / maxKw) * 100}%"></div><div class="fill won" style="width:${(k.won / maxKw) * 100}%"></div></div><span class="muted small">${k.total} · ${k.won} won</span></div>`).join("") : '<div class="muted">No data yet</div>'}</div></div>
    <div class="card"><div class="card-h"><h3>Wins by lead type</h3></div>
      <div class="card-b bars">${st.won_by_type.length ? st.won_by_type.map((k) => `<div class="bar"><span>${esc(k.type)}</span><div class="track"><div class="fill won" style="position:static;width:${(k.won / maxT) * 100}%"></div></div><span class="muted small">${k.won}</span></div>`).join("") : '<div class="muted">Mark leads as Won to see what works best.</div>'}</div></div>
    <div class="card"><div class="card-h"><h3>Pipeline</h3></div><div class="card-b bars">
      ${[["New", st.tabs.new, "var(--blue2)"], ["In progress", st.tabs.progress, "var(--amber)"], ["Old, verify", st.tabs.old, "var(--dim)"], ["Closed", st.tabs.history, "var(--green)"]].map(([l, v, col]) => `<div class="bar"><span>${l}</span><div class="track"><div class="fill" style="background:${col};width:${(v / Math.max(1, st.total)) * 100}%"></div></div><span class="muted small">${v}</span></div>`).join("")}
    </div></div>`;
}

// ------------------------------------------------------------------ team
async function pageTeam(main) {
  if (S.me.role !== "admin") return go("#/");
  const r = await api("/api/users"); S.users = r.items;
  const pending = r.items.filter((u) => !u.approved);
  main.innerHTML = `
    <div class="page-h"><div><h1>Team</h1><p class="muted">Approve members, set roles. Every lead shows who added it and who owns it.</p></div></div>
    ${pending.length ? `<div class="alert warn">${pending.length} member${pending.length > 1 ? "s" : ""} waiting for approval.</div>` : ""}
    <div class="card" style="overflow-x:auto"><table class="table"><thead><tr><th>Member</th><th>LinkedIn</th><th>Role</th><th>Status</th><th>Last login</th><th></th></tr></thead><tbody>
    ${r.items.map((u) => `<tr data-u="${u.id}">
      <td><div class="row">${avatar(u)}<div><b>${esc(u.name)}</b>${u.id === S.me.id ? ' <span class="chip">You</span>' : ""}<div class="tiny muted">${esc(u.email)}</div></div></div></td>
      <td>${u.linkedin.connected ? `<span class="li-pill on" style="margin:0">${LI_LOGO} ${esc(u.linkedin.name || "Connected")}</span>` : '<span class="muted small">Not connected</span>'}</td>
      <td><select class="input" style="width:auto;min-height:32px;height:32px;padding:4px 28px 4px 10px" data-role ${u.id === S.me.id ? "disabled" : ""}><option value="member" ${u.role === "member" ? "selected" : ""}>Member</option><option value="admin" ${u.role === "admin" ? "selected" : ""}>Admin</option></select></td>
      <td>${!u.active ? '<span class="chip red">Deactivated</span>' : u.approved ? '<span class="chip high">Active</span>' : '<span class="chip warn">Pending</span>'}</td>
      <td class="muted small">${u.last_login_at ? timeAgo(u.last_login_at) : "—"}</td>
      <td style="text-align:right;white-space:nowrap">${u.id === S.me.id ? "" : !u.approved ? '<button class="btn primary sm" data-approve>Approve</button> <button class="btn ghost sm" data-reject>Reject</button>' : u.active ? '<button class="btn ghost sm" data-deact>Deactivate</button>' : '<button class="btn outline sm" data-react>Reactivate</button>'}</td>
    </tr>`).join("")}</tbody></table></div>
    <div class="card card-b small muted">Allowed signup domains and auto-approval are in <a href="#/settings/workspace">Settings → Workspace</a>. Members can also join with "Sign in with LinkedIn" — they still need approval here.</div>`;
  const patch = async (id, body, msg) => { try { await api(`/api/users/${id}`, { method: "PATCH", body }); toast(msg, "", "ok"); shellReady = false; route(); } catch (e) { toast("Failed", e.message, "err"); } };
  $$("tr[data-u]", main).forEach((tr) => {
    const id = +tr.dataset.u;
    const on = (sel, fn) => { const el = $(sel, tr); if (el) el.onclick = fn; };
    on("[data-approve]", () => patch(id, { approved: true }, "Member approved"));
    on("[data-reject]", () => patch(id, { active: false }, "Request rejected"));
    on("[data-deact]", async () => { if (await confirmBox("Deactivate member?", "They won't be able to sign in. Their leads stay.", "Deactivate", true)) patch(id, { active: false }, "Member deactivated"); });
    on("[data-react]", () => patch(id, { active: true, approved: true }, "Member reactivated"));
    const role = $("[data-role]", tr); if (role) role.onchange = () => patch(id, { role: role.value }, "Role updated");
  });
}

// ------------------------------------------------------------------ settings
function tagInput(id, values) {
  return `<div class="tag-input" id="${id}">${values.map((v) => `<span class="chip kw" data-v="${esc(v)}">${esc(v)}<button type="button" aria-label="Remove">${ic("x")}</button></span>`).join("")}<input placeholder="Type and press Enter"></div>`;
}
function bindTagInput(id) {
  const box = $("#" + id), input = $("input", box);
  box.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) b.parentElement.remove(); else input.focus(); });
  input.addEventListener("keydown", (e) => {
    if ((e.key === "Enter" || e.key === ",") && input.value.trim()) {
      e.preventDefault();
      const v = input.value.trim();
      const s = document.createElement("span"); s.className = "chip kw"; s.dataset.v = v;
      s.innerHTML = `${esc(v)}<button type="button" aria-label="Remove">${ic("x")}</button>`;
      box.insertBefore(s, input); input.value = "";
    } else if (e.key === "Backspace" && !input.value) { const chips = $$(".chip", box); if (chips.length) chips[chips.length - 1].remove(); }
  });
}
const tagValues = (id) => $$(`#${id} .chip`).map((c) => c.dataset.v);

async function pageSettings(main, section, params) {
  const admin = S.me.role === "admin";
  const secs = [["profile", "Profile & LinkedIn"], ...(admin ? [["workspace", "Workspace"], ["integrations", "Alerts & integrations"], ["data", "Data"]] : [])];
  if (!secs.some((s) => s[0] === section)) section = "profile";
  main.innerHTML = `<div class="page-h"><div><h1>Settings</h1></div></div>
    <div class="settings-nav">${secs.map(([k, l]) => `<a href="#/settings/${k}" class="${k === section ? "active" : ""}">${l}</a>`).join("")}</div>
    <div id="set-body" class="stack"></div>`;
  const body = $("#set-body");
  if (section === "profile") return setProfile(body, params);
  if (section === "workspace") return setWorkspace(body);
  if (section === "integrations") return setIntegrations(body);
  if (section === "data") return setData(body);
}

async function setProfile(body, params) {
  const r = await api("/api/me"); S.me = r.user;
  const li = S.me.linkedin;
  if (params.get("connected")) setTimeout(() => toast("LinkedIn connected", li.name || "", "ok"), 50);
  body.innerHTML = `
    <div class="card"><div class="card-h"><h3>${LI_LOGO} LinkedIn account</h3>${li.connected ? '<span class="chip high">Connected</span>' : '<span class="chip">Not connected</span>'}</div>
      <div class="card-b">
      ${li.connected ? `<div class="row">${avatar({ name: li.name, picture: li.picture }, "xl")}<div class="grow"><div style="font-weight:700;font-size:16px">${esc(li.name || "")}</div><div class="muted">${esc(li.email || "")}</div><div class="tiny dim">Connected ${esc(fmtDate(li.connected_at))}</div></div>
          <button class="btn danger sm" id="li-disc">Disconnect</button></div>`
        : `<p class="muted" style="margin-top:0">Connect your LinkedIn so the team sees who you are on every lead you add, and so you can sign in with one click.</p>
          <a class="btn primary" href="/auth/linkedin/start?mode=connect" id="li-conn">${LI_LOGO} Connect LinkedIn</a>
          ${S.pub.linkedin_enabled ? "" : '<div class="alert info" style="margin-top:12px">LinkedIn sign-in isn\'t configured on this server yet. Admin: see README → "Sign In with LinkedIn".</div>'}`}
        <p class="tiny dim" style="margin:14px 0 0">Uses LinkedIn's official OpenID Connect sign-in (name, photo, email only). Lead Scout never sees your LinkedIn password, never stores a session cookie and can't read your feed or messages.</p>
      </div></div>
    <div class="card"><div class="card-h"><h3>${S.me.has_password ? "Change password" : "Set a password"}</h3></div>
      <form class="card-b stack" id="pw-form" style="max-width:420px">
        ${S.me.has_password ? '<div class="field"><label>Current password</label><input class="input" type="password" name="current_password" required autocomplete="current-password"></div>' : ""}
        <div class="field"><label>New password</label><input class="input" type="password" name="new_password" minlength="8" required autocomplete="new-password"></div>
        <div><button class="btn primary">Save password</button></div></form></div>`;
  const conn = $("#li-conn");
  if (conn && !S.pub.linkedin_enabled) conn.onclick = (e) => { e.preventDefault(); toast("Not configured yet", "Admin needs to add LinkedIn app keys.", "warn"); };
  const disc = $("#li-disc");
  if (disc) disc.onclick = async () => { try { await api("/api/me/linkedin", { method: "DELETE" }); toast("LinkedIn disconnected", "", "ok"); shellReady = false; route(); } catch (e) { toast("Couldn't disconnect", e.message, "err"); } };
  $("#pw-form").onsubmit = async (e) => {
    e.preventDefault();
    try { await api("/api/me/password", { method: "POST", body: Object.fromEntries(new FormData(e.target)) }); toast("Password saved", "", "ok"); e.target.reset(); }
    catch (err) { toast("Couldn't save", err.message, "err"); }
  };
}

function setWorkspace(body) {
  const c = S.settings.config;
  body.innerHTML = `
    <form class="card" id="ws-form"><div class="card-h"><h3>Lead rules</h3></div><div class="card-b stack">
      <div class="field"><label>Keywords to track</label>${tagInput("t-kw", c.keywords)}<span class="hint">A lead is saved only if the post mentions one of these (case-insensitive, whole words).</span></div>
      <div class="field"><label>What does "RTDS" mean?</label><input class="input" name="rtds_meaning" value="${esc(c.rtds_meaning || "")}" placeholder="Confirm with the requirement owner"></div>
      <div class="field"><label>High-intent words</label>${tagInput("t-int", c.intent_words)}<span class="hint">Any of these → "High intent". Hiring posts can be jobs, so a person still verifies.</span></div>
      <div class="field" style="max-width:240px"><label>"New" window (days)</label><input class="input" type="number" min="1" max="365" name="active_days" value="${c.active_days}"><span class="hint">Older untouched posts move to "Old, verify".</span></div>
    </div></form>
    <div class="card"><div class="card-h"><h3>${ic("sparkle")} Suggested keywords</h3><span class="tiny muted">click + to track</span></div>
      <div class="card-b"><div class="row wrap" style="gap:8px" id="sugg"><span class="muted small">Loading…</span></div>
      <p class="tiny dim" style="margin:10px 0 0">Mixed from phrases that keep appearing in your captured posts and common terms in affiliate/performance-marketing posts. Remember to save.</p></div></div>
    <div class="card"><div class="card-h"><h3>${ic("search")} Auto-discover</h3></div><div class="card-b stack">
      <label class="row" style="gap:10px;cursor:pointer"><input type="checkbox" id="d-en" ${c.discovery_enabled ? "checked" : ""} style="accent-color:var(--blue2);width:18px;height:18px"> Automatically find new public LinkedIn posts for every keyword</label>
      <div class="grid2">
        <div class="field"><label>Check every</label><select class="input" id="d-int">${[15, 30, 60, 120, 240, 720, 1440].map((m) => `<option value="${m}" ${c.discovery_interval_min == m ? "selected" : ""}>${m < 60 ? m + " minutes" : m / 60 + (m === 60 ? " hour" : " hours")}</option>`).join("")}</select><span class="hint">Each check = 1 search per keyword (uses API credits).</span></div>
        <div class="field"><label>Posts from</label><select class="input" id="d-win"><option value="d" ${c.discovery_window === "d" ? "selected" : ""}>Last 24 hours</option><option value="w" ${c.discovery_window === "w" ? "selected" : ""}>Last 7 days</option><option value="m" ${c.discovery_window === "m" ? "selected" : ""}>Last 30 days</option></select></div>
        <div class="field"><label>Search region</label><select class="input" id="d-cty">${[["in", "India"], ["us", "United States"], ["gb", "United Kingdom"], ["ae", "UAE"], ["sg", "Singapore"]].map(([k, v]) => `<option value="${k}" ${c.discovery_country === k ? "selected" : ""}>${v}</option>`).join("")}</select></div>
        <div class="field"><label>Ignore posts older than (days)</label><input class="input" type="number" min="1" max="365" id="d-age" value="${c.discovery_max_age_days || 30}"></div>
      </div></div></div>
    <div class="card"><div class="card-h"><h3>Team access</h3></div><div class="card-b stack">
      <div class="field"><label>Allowed email domains</label>${tagInput("t-dom", c.allowed_domains)}<span class="hint">e.g. yourcompany.com — empty means anyone can request access (admin still approves).</span></div>
      <label class="row" style="gap:10px;cursor:pointer"><input type="checkbox" id="auto-ap" ${c.auto_approve_domains ? "checked" : ""} style="accent-color:var(--blue2);width:18px;height:18px"> Auto-approve email signups from allowed domains</label>
    </div></div>
    <div><button class="btn primary lg" id="ws-save">${ic("check")} Save workspace settings</button></div>`;
  ["t-kw", "t-int", "t-dom"].forEach(bindTagInput);
  api("/api/keywords/suggestions").then((r) => {
    const box = $("#sugg"); if (!box) return;
    box.innerHTML = r.items.length ? r.items.map((x) => `<button type="button" class="chip outline" style="cursor:pointer;height:30px" data-sug="${esc(x.keyword)}" title="${x.source === "from your leads" ? "Seen in " + x.count + " of your posts" : "Common in this kind of post"}">+ ${esc(x.keyword)}${x.source === "from your leads" ? ` <span class="dim">· ${x.count}</span>` : ""}</button>`).join("") : '<span class="muted small">No suggestions right now.</span>';
    $$("[data-sug]", box).forEach((b) => b.onclick = () => {
      const tb = $("#t-kw"), inp = $("input", tb), v = b.dataset.sug;
      if (tagValues("t-kw").some((k) => k.toLowerCase() === v.toLowerCase())) return b.remove();
      const sp = document.createElement("span"); sp.className = "chip kw"; sp.dataset.v = v;
      sp.innerHTML = `${esc(v)}<button type="button" aria-label="Remove">${ic("x")}</button>`; tb.insertBefore(sp, inp); b.remove();
      toast("Keyword added", v + " — click Save to apply", "ok");
    });
  }).catch(() => {});
  $("#ws-save").onclick = async () => {
    const body = { keywords: tagValues("t-kw"), intent_words: tagValues("t-int"), allowed_domains: tagValues("t-dom"),
      active_days: +$("[name=active_days]").value || 7, auto_approve_domains: $("#auto-ap").checked, rtds_meaning: $("[name=rtds_meaning]").value,
      discovery_enabled: $("#d-en").checked, discovery_interval_min: +$("#d-int").value, discovery_window: $("#d-win").value,
      discovery_country: $("#d-cty").value, discovery_max_age_days: +$("#d-age").value || 30 };
    try { const r = await api("/api/settings", { method: "PUT", body }); S.settings.config = r.config; toast("Settings saved", "", "ok"); shellReady = false; route(); }
    catch (e) { toast("Couldn't save", e.message, "err"); }
  };
}

async function setIntegrations(body) {
  const i = await api("/api/integrations"); S.integrations = i;
  const pill = (on) => on ? '<span class="chip high">Connected</span>' : '<span class="chip">Not set</span>';
  body.innerHTML = `
    <div class="card"><div class="card-h"><h3>${ic("search")} Auto-discover (search API)</h3>${pill(i.search.enabled)}</div><div class="card-b stack small">
      <div class="muted">Finds new <b>public</b> LinkedIn posts for each keyword through Google search results. Nobody logs in to LinkedIn and LinkedIn isn't scraped. Posts are previewed with LinkedIn's official embed.</div>
      ${i.search.enabled ? `<div class="alert ok">Connected via <b>${esc(i.search.provider)}</b>. Schedule and filters: <a href="#/settings/workspace">Settings → Workspace</a>.</div>` : `<ol class="steps">
        <li><span>Create a free account at <a href="https://serper.dev" target="_blank" rel="noopener">serper.dev</a> (2,500 free searches, no card) and copy the API key.</span></li>
        <li><span>On the server, set <code>SERPER_API_KEY</code> (or <code>SERPAPI_API_KEY</code> for SerpAPI) and restart.</span></li>
        <li><span>Click <b>Find posts now</b> on the Leads page, or wait for the schedule.</span></li></ol>`}
      <div class="tiny dim">Coverage = what Google has indexed. Very new or non-public posts may not appear, so the 1-click capture is still useful.</div></div></div>
    <div class="card"><div class="card-h"><h3>New-lead alerts</h3></div><div class="card-b stack">
      <div class="int-card"><div class="lg" style="background:var(--blue-bg);color:var(--blue-l)">${ic("bell")}</div><div class="grow"><b>In-app notifications</b> <span class="chip high">Always on</span><div class="muted small">Bell icon + pop-up for everyone in the workspace.</div></div></div>
      <div class="int-card"><div class="lg" style="background:#229ED9;color:#fff">TG</div><div class="grow"><div class="row between"><b>Telegram</b>${pill(i.telegram.enabled)}</div><div class="muted small">Set <code>TELEGRAM_BOT_TOKEN</code> and <code>TELEGRAM_CHAT_ID</code> on the server. Tokens are never stored in code or the database.</div>
        <button class="btn sm outline" style="margin-top:10px" data-test="telegram" ${i.telegram.enabled ? "" : "disabled"}>Send test alert</button></div></div>
      <div class="int-card"><div class="lg" style="background:#4A154B;color:#fff">SL</div><div class="grow"><div class="row between"><b>Slack</b>${pill(i.slack.enabled)}</div><div class="muted small">Set <code>SLACK_WEBHOOK_URL</code> (Incoming Webhook) on the server.</div>
        <button class="btn sm outline" style="margin-top:10px" data-test="slack" ${i.slack.enabled ? "" : "disabled"}>Send test alert</button></div></div>
    </div></div>
    <div class="card"><div class="card-h"><h3>${LI_LOGO} Sign In with LinkedIn</h3>${pill(i.linkedin.enabled)}</div><div class="card-b stack small">
      <div class="muted">Create an app at <a href="https://www.linkedin.com/developers/apps" target="_blank" rel="noopener">LinkedIn Developer Portal</a> → Products → add <b>Sign In with LinkedIn using OpenID Connect</b> → Auth → add this redirect URL:</div>
      <div class="row"><div class="code grow" id="redir">${esc(i.linkedin.redirect_uri)}</div><button class="icon-btn" data-copy="redir" title="Copy">${ic("copy")}</button></div>
      <div class="muted">Then set <code>LINKEDIN_CLIENT_ID</code> and <code>LINKEDIN_CLIENT_SECRET</code> on the server and restart.</div></div></div>
    <div class="card"><div class="card-h"><h3>${ic("webhook")} Vendor webhook (automatic posts)</h3>${pill(i.webhook.enabled)}</div><div class="card-b stack small">
      <div class="muted">Connect an approved social-listening vendor (e.g. Octolens). It posts matching LinkedIn posts here; keyword match, duplicate check, intent tag and alerts run automatically.</div>
      <div class="row"><div class="code grow" id="wh">${esc(i.webhook.url)}</div><button class="icon-btn" data-copy="wh" title="Copy">${ic("copy")}</button></div>
      <div class="code">curl -X POST ${esc(i.webhook.url)} \\
  -H "Content-Type: application/json" \\
  -H "X-Webhook-Secret: $WEBHOOK_SECRET" \\
  -d '{"url":"https://www.linkedin.com/feed/update/urn:li:activity:7300000000000000000/","text":"Looking for performance marketing agency…","author":{"name":"Jane Doe"},"posted_at":"2026-11-25T08:00:00Z"}'</div>
      <div class="muted">Accepts one object, a list, or <code>{"items":[…]}</code>. Fields: url / post_url / link, text / content, author / author.name, posted_at. Set <code>WEBHOOK_SECRET</code> on the server to enable.</div>
      <div class="alert info">Before buying a vendor, get its data source and LinkedIn compliance in writing and take company approval.</div></div></div>`;
  $$("[data-test]", body).forEach((b) => b.onclick = async () => { b.disabled = true; const r = await api("/api/integrations/test", { method: "POST", body: { channel: b.dataset.test } }); toast("Test: " + b.dataset.test, r.result, r.result === "sent" ? "ok" : "err"); b.disabled = false; });
  $$("[data-copy]", body).forEach((b) => b.onclick = () => { navigator.clipboard.writeText($("#" + b.dataset.copy).textContent); toast("Copied", "", "ok"); });
}

function setData(body) {
  body.innerHTML = `
    <div class="card"><div class="card-h"><h3>Demo sample data</h3>${S.stats.sample_count ? `<span class="chip sample">${S.stats.sample_count} sample posts</span>` : ""}</div><div class="card-b stack">
      <div class="muted small">Loads 8 realistic demo posts (fake names, labelled "Sample data") covering every lead type, a compliance case and old posts.</div>
      <div class="row"><button class="btn outline" id="s-add">Load sample data</button><button class="btn danger" id="s-del" ${S.stats.sample_count ? "" : "disabled"}>Remove sample data</button></div></div></div>
    <div class="card"><div class="card-h"><h3>Export</h3></div><div class="card-b row wrap">
      <a class="btn" href="/api/leads/export.csv?tab=all">${ic("download")} All leads (CSV)</a>
      <a class="btn" href="/api/leads/export.csv?tab=history">${ic("download")} Won / Lost (CSV)</a></div></div>
    <div class="card card-b small muted">Privacy: keep only what's needed for business follow-up, keep access to your team, and delete leads you don't need (Delete is in each lead's details). Do a privacy/legal check before real use.</div>`;
  $("#s-add").onclick = async () => { await loadSample(); go("#/leads/new"); };
  $("#s-del").onclick = async () => {
    if (!(await confirmBox("Remove sample data?", "All leads marked Sample data will be deleted.", "Remove", true))) return;
    const r = await api("/api/admin/sample", { method: "DELETE" }); toast("Sample data removed", `${r.deleted} leads deleted`, "ok"); await refreshStats(); shellReady = false; route();
  };
}

boot();
})();
