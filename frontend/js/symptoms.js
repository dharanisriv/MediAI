/* Symptom Checker page: body map + symptom list + emergency checks */
(() => {
  const AREAS = ["head", "eyes", "ears", "nose", "throat", "chest", "abdomen", "back", "arms", "hands", "legs", "feet", "skin", "general"];
  const FRONT_ONLY = new Set(["eyes", "nose", "throat", "chest", "abdomen"]);

  // Common symptoms per area (shown in English; the user can write in any language below).
  const SYMPTOMS = {
    head: ["Headache", "Dizziness or light-headedness", "Head injury", "Migraine-like pain with light sensitivity", "Neck stiffness", "Sudden severe headache"],
    eyes: ["Redness", "Itching or watering", "Blurred vision", "Eye pain", "Swollen eyelid", "Sensitivity to light"],
    ears: ["Ear pain", "Blocked ear", "Ringing in the ear", "Reduced hearing", "Discharge from the ear"],
    nose: ["Runny nose", "Blocked nose", "Sneezing", "Nosebleed", "Loss of smell"],
    throat: ["Sore throat", "Difficulty swallowing", "Hoarse voice", "Swollen glands in the neck", "Cough"],
    chest: ["Cough", "Wheezing", "Chest pain or pressure", "Fast or irregular heartbeat", "Difficulty breathing", "Heartburn or acidity"],
    abdomen: ["Stomach pain", "Nausea", "Vomiting", "Loose motions (diarrhoea)", "Constipation", "Bloating", "Loss of appetite", "Burning while passing urine"],
    back: ["Lower back pain", "Upper back pain", "Stiffness", "Pain spreading down the leg", "Muscle spasm"],
    arms: ["Pain in the arm", "Swelling", "Numbness or tingling", "Weakness", "Shoulder or elbow joint pain"],
    hands: ["Pain in the hand or wrist", "Numbness or tingling", "Swollen fingers", "Stiff joints", "Cut or injury"],
    legs: ["Pain in the leg", "Swelling", "Cramps", "Numbness or tingling", "Hip or knee joint pain", "Weakness"],
    feet: ["Foot pain", "Swollen ankle", "Heel pain", "Numbness or tingling", "Cracked skin", "Wound that heals slowly"],
    skin: ["Rash", "Itching", "Redness", "Dry or flaky skin", "Blisters", "Boils or pus", "Swelling of the skin"],
    general: ["Fever", "Tiredness", "Body aches", "Chills", "Weight loss without trying", "Night sweats", "Excessive thirst", "Loss of appetite"],
  };
  // These options match our emergency rules, so we label them clearly.
  const URGENT = new Set(["Chest pain or pressure", "Difficulty breathing", "Sudden severe headache"]);

  const $ = (id) => document.getElementById(id);
  const form = $("symptom-form"), results = $("results"), live = $("live-emergency"), submit = $("submit");
  const svg = $("body-svg"), chips = $("area-chips"), list = $("symptom-list");
  let area = null;
  let selected = new Set();
  let backView = false;

  showEmpty(results, "thermo");

  /* ----- body map ----- */
  function buildChips() {
    chips.innerHTML = AREAS.map((a) => `<button type="button" class="chip" data-area="${a}" aria-pressed="${a === area}">${esc(t("area_" + a))}</button>`).join("");
  }
  function setView(back) {
    backView = back;
    // SVG elements have no .hidden property, so we toggle the attribute directly.
    $("view-front").toggleAttribute("hidden", back);
    $("view-back").toggleAttribute("hidden", !back);
    $("view-toggle").textContent = t(back ? "view_front" : "view_back");
  }
  function selectArea(next) {
    area = next;
    selected = new Set(); // symptoms belong to one area, so start fresh
    if (next === "back") setView(true);
    else if (FRONT_ONLY.has(next)) setView(false);
    svg.querySelectorAll(".region").forEach((r) => r.classList.toggle("active", r.dataset.area === next));
    svg.classList.toggle("all-active", next === "skin" || next === "general");
    buildChips();
    renderSymptoms();
    scheduleLiveCheck();
  }
  svg.addEventListener("click", (e) => { const r = e.target.closest(".region"); if (r) selectArea(r.dataset.area); });
  svg.addEventListener("keydown", (e) => {
    const r = e.target.closest(".region");
    if (r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); selectArea(r.dataset.area); }
  });
  chips.addEventListener("click", (e) => { const c = e.target.closest(".chip"); if (c) selectArea(c.dataset.area); });
  $("view-toggle").addEventListener("click", () => setView(!backView));

  /* ----- symptom checklist ----- */
  function renderSymptoms() {
    if (!area) { list.innerHTML = `<p class="muted">${esc(t("pick_area"))}</p>`; return; }
    list.innerHTML = SYMPTOMS[area].map((s, i) => `<label class="check ${selected.has(s) ? "on" : ""}">
        <input type="checkbox" data-i="${i}" ${selected.has(s) ? "checked" : ""}><span>${esc(s)}</span>
        ${URGENT.has(s) ? badge("high", t("urgent_sign")) : ""}</label>`).join("");
  }
  list.addEventListener("change", (e) => {
    const box = e.target.closest("input[type=checkbox]");
    if (!box) return;
    const name = SYMPTOMS[area][Number(box.dataset.i)];
    if (box.checked) selected.add(name); else selected.delete(name);
    box.closest(".check").classList.toggle("on", box.checked);
    scheduleLiveCheck();
  });

  /* ----- instant emergency check while typing (rules on the server, no AI) ----- */
  let timer = null, requestId = 0;
  const liveText = () => [...selected, $("description").value].join(". ");
  function scheduleLiveCheck() {
    clearTimeout(timer);
    timer = setTimeout(runLiveCheck, 500);
  }
  async function runLiveCheck() {
    const text = liveText().trim();
    const mine = ++requestId;
    if (text.length < 3) { live.innerHTML = ""; return; }
    try {
      const data = await api("/api/safety/check", { method: "POST", json: { text, language: currentLang }, timeoutMs: 8000 });
      if (mine === requestId) live.innerHTML = renderEmergency(data.emergency, true);
    } catch (e) { /* the live check is a bonus; the real check runs on submit */ }
  }
  $("description").addEventListener("input", scheduleLiveCheck);

  /* ----- submit ----- */
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const description = $("description").value.trim();
    if (!selected.size && !description) { showError(results, t("err_need")); return; }
    const severity = form.querySelector("input[name=severity]:checked").value;
    const payload = {
      language: currentLang, area: area || "general", symptoms: [...selected], description,
      duration: $("duration").value, severity, age: $("age").value.trim(), history: $("history").value.trim(),
    };
    showLoading(results);
    setBusy(submit, true);
    try {
      const data = await api("/api/symptoms/analyze", { method: "POST", json: payload });
      if (data.emergency) {
        // Emergency first: big warning, NO self-care advice.
        results.innerHTML = renderEmergency(data.emergency) + disclaimerHtml(data.disclaimer);
        live.innerHTML = "";
      } else {
        live.innerHTML = "";
        results.innerHTML = renderEntered(payload) + renderResult(data);
      }
    } catch (err) {
      showError(results, err.message);
    } finally {
      setBusy(submit, false);
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  /* ----- showing the answer ----- */
  function renderEntered(p) {
    const rows = [
      [t("step_area").replace(/^\d\.\s*/, ""), t("area_" + p.area)],
      [t("step_symptoms").replace(/^\d\.\s*/, ""), p.symptoms.join(", ")],
      [t("desc_label"), p.description], [t("duration"), $("duration").selectedOptions[0].textContent],
      [t("severity"), t("sev_" + p.severity)], [t("age"), p.age], [t("history_label"), p.history],
    ].filter((r) => r[1]);
    return `<div class="card result-card entered"><div class="result-head"><h2>${esc(t("what_you_entered"))}</h2>${badge("user", t("badge_user"))}</div>
      <dl>${rows.map((r) => `<dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd>`).join("")}</dl></div>`;
  }

  const URGENCY = { self_care_ok: "ok", see_doctor_soon: "ai", see_doctor_within_24_hours: "warn", urgent_care_today: "high" };

  function renderResult(d) {
    const r = d.result, w = r.when_to_see_doctor, ai = badge("ai", t("badge_ai"));
    const explanations = r.possible_explanations.map((p) => `<div class="explain"><b>${esc(p.name)}</b>${esc(p.why_it_may_fit)}</div>`).join("");
    const when = `<p>${badge(URGENCY[w.urgency] || "ai", w.urgency_label || w.urgency)}</p><p class="prose">${esc(w.reasoning)}</p>`;
    let html = `<div class="card result-card">${aiLine()}`;
    html += section(t("summary_h"), `<p class="prose">${esc(r.symptom_summary)}</p>`, ai);
    html += section(t("s_possible"), explanations, ai);
    html += section(t("s_when"), when, ai);
    html += section(t("s_warning"), listHtml(w.warning_signs_to_watch), ai);
    html += section(t("s_selfcare"), listHtml(r.self_care), ai);
    html += section(t("questions_doctor"), listHtml(r.questions_for_doctor), ai);
    html += "</div>" + disclaimerHtml(d.disclaimer);
    return html;
  }

  /* ----- language change: rebuild the labels that JavaScript created ----- */
  window.addEventListener("langchange", () => { buildChips(); renderSymptoms(); setView(backView); });

  buildChips();
})();
