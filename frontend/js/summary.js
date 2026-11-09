/* Personalized Health Summary page */
(() => {
  const FIELDS = ["age", "history", "conditions", "medications", "allergies", "symptoms", "report_findings", "concerns"];
  const SAVE_KEY = "mediai_saved_summary_form"; // used ONLY if the user ticks "save on this device"
  const $ = (id) => document.getElementById(id);
  const form = $("summary-form"), results = $("results"), live = $("live-emergency"), submit = $("submit");
  let lastText = "";

  showEmpty(results, "clipboard");

  /* ----- optional save on THIS device (never sent anywhere) ----- */
  function loadSaved() {
    try {
      const raw = localStorage.getItem(SAVE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw);
      FIELDS.forEach((f) => { if (saved[f]) $(f).value = saved[f]; });
      $("save-local").checked = true;
    } catch (e) { /* storage blocked or corrupted: ignore */ }
  }
  function saveIfChosen(values) {
    try {
      if ($("save-local").checked) localStorage.setItem(SAVE_KEY, JSON.stringify(values));
      else localStorage.removeItem(SAVE_KEY);
    } catch (e) { /* ignore */ }
  }
  $("clear-saved").addEventListener("click", () => {
    try { localStorage.removeItem(SAVE_KEY); } catch (e) { /* ignore */ }
    form.reset();
    live.innerHTML = "";
    showEmpty(results, "clipboard");
  });
  loadSaved();

  /* ----- instant emergency check on the "symptoms" and "concerns" boxes ----- */
  let timer = null, requestId = 0;
  function scheduleLiveCheck() { clearTimeout(timer); timer = setTimeout(runLiveCheck, 600); }
  async function runLiveCheck() {
    const text = [$("symptoms").value, $("concerns").value].join(". ").trim();
    const mine = ++requestId;
    if (text.length < 3) { live.innerHTML = ""; return; }
    try {
      const data = await api("/api/safety/check", { method: "POST", json: { text, language: currentLang }, timeoutMs: 8000 });
      if (mine === requestId) live.innerHTML = renderEmergency(data.emergency, true);
    } catch (e) { /* bonus check only */ }
  }
  $("symptoms").addEventListener("input", scheduleLiveCheck);
  $("concerns").addEventListener("input", scheduleLiveCheck);

  /* ----- generate ----- */
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = {};
    FIELDS.forEach((f) => { values[f] = $(f).value.trim(); });
    if (!FIELDS.some((f) => values[f])) { showError(results, t("err_need")); return; }
    saveIfChosen(values);

    showLoading(results);
    setBusy(submit, true);
    try {
      const data = await api("/api/summary/generate", { method: "POST", json: { language: currentLang, ...values } });
      live.innerHTML = renderEmergency(data.emergency, true);
      results.innerHTML = renderSummary(data);
      $("copy-btn").addEventListener("click", (e) => copyText(lastText, e.currentTarget));
      $("download-btn").addEventListener("click", () => downloadText("MediAI_Health_Summary.txt", lastText));
    } catch (err) {
      showError(results, err.message);
    } finally {
      setBusy(submit, false);
      (live.innerHTML ? live : results).scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  /* ----- showing + exporting ----- */
  function renderSummary(d) {
    const r = d.result;
    const you = badge("user", t("badge_user")), ai = badge("ai", t("badge_ai"));
    // [heading, content (string or list), badge]
    const parts = [
      [t("sec_basic"), r.basic_information, you], [t("sec_history"), r.medical_history, you],
      [t("sec_meds"), r.medications_and_allergies, you], [t("sec_symptoms"), r.symptoms_summary, you],
      [t("sec_report"), r.report_findings_summary, you], [t("sec_concerns"), r.important_concerns, ai],
      [t("sec_questions"), r.questions_for_professional, ai],
    ];
    const body = parts.map(([title, content, b]) =>
      section(title, Array.isArray(content) ? listHtml(content) : `<p class="prose">${esc(content)}</p>`, b)).join("");
    const note = r.missing_information_note ? `<section class="result-section"><p class="muted">${esc(r.missing_information_note)}</p></section>` : "";

    // Plain-text version for Copy / Download
    const lines = ["MediAI Health Summary", new Date().toLocaleString(), ""];
    parts.forEach(([title, content]) => {
      lines.push(title, Array.isArray(content) ? content.map((c) => "- " + c).join("\n") : content, "");
    });
    if (r.missing_information_note) lines.push(r.missing_information_note, "");
    lines.push(t("summary_not_record"), d.disclaimer);
    lastText = lines.join("\n");

    return `<div class="card result-card">${aiLine()}
      <div class="result-head"><h2>${esc(t("nav_summary"))}</h2><div class="btn-row" style="margin:0">
        <button class="btn btn-ghost" id="copy-btn" type="button">${icon("copy")} ${esc(t("copy"))}</button>
        <button class="btn btn-ghost" id="download-btn" type="button">${icon("download")} ${esc(t("download"))}</button></div></div>
      ${body}${note}<p class="muted small">${esc(t("summary_not_record"))}</p></div>${disclaimerHtml(d.disclaimer)}`;
  }
})();
