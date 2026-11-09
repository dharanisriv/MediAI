/*
 * MediAI shared script - loaded by every page (after i18n.js).
 * It builds the navigation, handles the language selector, and offers helper functions
 * (api, esc, renderEmergency ...) that the page scripts use.
 * SECURITY NOTE: everything that comes from the AI or the user is passed through esc()
 * before it is put into the page, so it can never run as code.
 */

/* ---------- icons (small inline SVGs, no internet needed) ---------- */
const ICONS = {
  pulse: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
  thermo: '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>',
  pill: '<path d="M10.5 20.5l10-10a4.95 4.95 0 0 0-7-7l-10 10a4.95 4.95 0 0 0 7 7z"/><line x1="8.5" y1="8.5" x2="15.5" y2="15.5"/>',
  clipboard: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
  alert: '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  menu: '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  search: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  globe: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
  phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
  sparkle: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>',
};

function icon(name) {
  return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">${ICONS[name] || ""}</svg>`;
}

/* ---------- small helpers ---------- */
function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
function listHtml(items) {
  if (!items || !items.length) return "";
  return `<ul class="list">${items.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`;
}
function section(title, bodyHtml, badgeHtml) {
  if (!bodyHtml) return "";
  return `<section class="result-section"><h3>${esc(title)} ${badgeHtml || ""}</h3>${bodyHtml}</section>`;
}
function badge(kind, text) { return `<span class="badge badge-${kind}">${esc(text)}</span>`; }
function aiLine() { return `<div class="ai-line">${icon("sparkle")}<span>${esc(t("ai_badge"))}</span></div>`; }
function disclaimerHtml(text) { return `<div class="alert alert-info">${icon("shield")}<p class="small">${esc(text)}</p></div>`; }

/* ---------- talking to the backend ---------- */
class ApiError extends Error {}

async function api(path, options) {
  options = options || {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs || 95000);
  try {
    const init = { method: options.method || "GET", signal: controller.signal };
    if (options.json !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(options.json);
    } else if (options.formData) {
      init.body = options.formData; // the browser sets the multipart header itself
    }
    const response = await fetch(path, init);
    let data;
    try { data = await response.json(); } catch (e) { data = { ok: false, error: "Unexpected answer from the server (HTTP " + response.status + ")." }; }
    if (!response.ok || data.ok === false) throw new ApiError(data.error || "Request failed.");
    return data;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === "AbortError") throw new ApiError(t("err_timeout"));
    throw new ApiError(t("err_network"));
  } finally {
    clearTimeout(timer);
  }
}

/* ---------- loading / error / empty states ---------- */
function showLoading(box) {
  box.innerHTML = `<div class="card" role="status"><div class="loading-card"><div class="spinner"></div><div><strong>${esc(t("loading"))}</strong></div></div><div class="skeleton" style="width:90%"></div><div class="skeleton" style="width:75%"></div><div class="skeleton" style="width:82%"></div></div>`;
}
function showError(box, message) {
  box.innerHTML = `<div class="alert alert-danger" role="alert">${icon("alert")}<div><strong>${esc(t("error_title"))}</strong><p>${esc(message)}</p></div></div>`;
}
function showEmpty(box, iconName) {
  box.innerHTML = `<div class="card empty"><div class="icon-tile blue">${icon(iconName || "sparkle")}</div><p>${esc(t("empty_results"))}</p></div>`;
}
function setBusy(button, busy) {
  if (!button) return;
  if (busy) {
    button.dataset.label = button.innerHTML;
    button.innerHTML = '<span class="spinner"></span>' + button.innerHTML;
    button.disabled = true;
  } else {
    if (button.dataset.label) button.innerHTML = button.dataset.label;
    button.disabled = false;
  }
}

/* ---------- emergency banner (used by symptoms + summary + live check) ---------- */
// compact=true is the small sticky version shown WHILE the user is typing, so it can never be missed.
function renderEmergency(e, compact) {
  if (!e) return "";
  const flags = (e.flags || []).map((f) => `<span class="badge badge-high">${esc(f.label)}</span>`).join("");
  const extra = (e.extra || []).map((x) => `<div class="support">${icon("phone")} ${esc(x)}</div>`).join("");
  const reason = e.ai_reason ? `<p class="small muted">${esc(e.ai_reason)}</p>` : "";
  const actions = `<ul>${(e.actions || []).map((a) => `<li>${esc(a)}</li>`).join("")}</ul>`;
  return `<div class="emergency ${compact ? "compact" : ""}" role="alert">
    <div class="icon-tile">${icon("alert")}</div>
    <div>
      <h2>${esc(e.title)}</h2>
      <p><strong>${esc(e.message)}</strong></p>
      ${compact ? "" : flags ? `<div class="flag-list">${flags}</div>` : ""}
      ${compact ? "" : reason}${extra}${compact ? "" : actions}
      <a class="btn btn-danger" href="tel:112">${icon("phone")} ${esc(e.call_label)}</a>
    </div></div>`;
}

/* ---------- copy / download ---------- */
async function copyText(text, button) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) { // fallback for older browsers / non-secure pages
    const area = document.createElement("textarea");
    area.value = text; document.body.appendChild(area); area.select();
    try { document.execCommand("copy"); } catch (_) { /* ignore */ }
    area.remove();
  }
  if (button) {
    const old = button.innerHTML;
    button.innerHTML = icon("copy") + " " + esc(t("copied"));
    setTimeout(() => { button.innerHTML = old; }, 1600);
  }
}
function downloadText(filename, text) {
  const blob = new Blob(["\ufeff" + text], { type: "text/plain;charset=utf-8" }); // BOM keeps Hindi/Telugu/Tamil readable in Notepad
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url; link.download = filename;
  document.body.appendChild(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ---------- page shell: navigation, language selector, footer ---------- */
const NAV = [
  { page: "landing", href: "index.html", key: "nav_home", icon: "home" },
  { page: "dashboard", href: "dashboard.html", key: "nav_dashboard", icon: "grid" },
  { page: "report", href: "report.html", key: "nav_report", icon: "file" },
  { page: "symptoms", href: "symptoms.html", key: "nav_symptoms", icon: "thermo" },
  { page: "medicines", href: "medicines.html", key: "nav_medicines", icon: "pill" },
  { page: "summary", href: "summary.html", key: "nav_summary", icon: "clipboard" },
  { page: "about", href: "about.html", key: "nav_about", icon: "info" },
  { page: "disclaimer", href: "disclaimer.html", key: "nav_disclaimer", icon: "shield" },
];

function logoHtml() {
  return `<a class="logo" href="index.html" aria-label="MediAI"><span class="logo-mark">${icon("pulse")}</span><span>Medi<b>AI</b></span></a>`;
}
function langSelectHtml() {
  const options = LANGS.map((l) => `<option value="${l.code}" ${l.code === currentLang ? "selected" : ""}>${esc(l.native)}</option>`).join("");
  return `<label class="lang-select">${icon("globe")}<span class="hidden" data-i18n="language"></span><select id="lang-select" data-i18n-aria="language" aria-label="${esc(t("language"))}">${options}</select></label>`;
}
function footerHtml() {
  return `<footer class="site-footer"><span data-i18n="footer_text"></span><span><a href="disclaimer.html" data-i18n="nav_disclaimer"></a> &nbsp; <a href="about.html" data-i18n="nav_about"></a></span></footer>`;
}

function buildShell() {
  const page = document.body.dataset.page;
  const main = document.getElementById("content");
  if (!main) return;

  if (document.body.dataset.layout === "landing") {
    const header = document.createElement("header");
    header.className = "landing-header";
    header.innerHTML = `${logoHtml()}<nav><a class="plain" href="dashboard.html" data-i18n="nav_dashboard"></a><a class="plain" href="about.html" data-i18n="nav_about"></a>${langSelectHtml()}<a class="btn btn-primary" href="dashboard.html" data-i18n="get_started"></a></nav>`;
    main.before(header);
    main.insertAdjacentHTML("afterend", footerHtml());
  } else {
    const links = NAV.map((n) => `<a class="nav-link" href="${n.href}" ${n.page === page ? 'aria-current="page"' : ""}>${icon(n.icon)}<span data-i18n="${n.key}"></span></a>`).join("");
    const shell = document.createElement("div");
    shell.className = "app-shell";
    shell.innerHTML = `
      <aside class="sidebar" id="sidebar">${logoHtml()}${links}<div class="nav-spacer"></div>
        <a class="sos-card" href="tel:112">${icon("phone")}<span data-i18n="emergency_strip"></span></a></aside>
      <div class="scrim" id="scrim"></div>
      <div class="main-col">
        <header class="topbar">
          <div class="topbar-left"><button class="menu-btn" id="menu-btn" data-i18n-aria="menu" aria-label="${esc(t("menu"))}">${icon("menu")}</button></div>
          ${langSelectHtml()}
        </header>
        <div id="page-slot"></div>
        ${footerHtml()}
      </div>`;
    document.body.prepend(shell);
    shell.querySelector("#page-slot").appendChild(main);
    shell.querySelector("#menu-btn").addEventListener("click", () => document.body.classList.toggle("nav-open"));
    shell.querySelector("#scrim").addEventListener("click", () => document.body.classList.remove("nav-open"));
    if (document.body.dataset.disclaimer === "true") {
      main.querySelector(".page-head")?.insertAdjacentHTML("afterend", `<div class="alert alert-info" role="note">${icon("shield")}<p class="small" data-i18n="disclaimer_banner"></p></div>`);
    }
  }
  document.getElementById("lang-select").addEventListener("change", (event) => {
    currentLang = event.target.value;
    try { localStorage.setItem(LANG_STORAGE_KEY, currentLang); } catch (e) { /* ignore */ }
    applyI18n();
    window.dispatchEvent(new CustomEvent("langchange"));
  });
}

/* In the HTML, <span data-icon="file"></span> is replaced by the matching icon. */
function hydrateIcons(root) {
  (root || document).querySelectorAll("[data-icon]").forEach((el) => { el.innerHTML = icon(el.dataset.icon); });
}

document.addEventListener("DOMContentLoaded", () => {
  loadSavedLang();
  buildShell();
  hydrateIcons();
  applyI18n();
});
