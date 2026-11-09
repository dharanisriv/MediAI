/* Medicine Information page */
(() => {
  const form = document.getElementById("medicine-form");
  const input = document.getElementById("medicine-name");
  const results = document.getElementById("results");
  const submit = document.getElementById("submit");

  showEmpty(results, "pill");

  document.querySelectorAll(".chip.example").forEach((chip) => {
    chip.addEventListener("click", () => { input.value = chip.textContent; form.requestSubmit(); });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = input.value.trim();
    if (name.length < 2) { showError(results, t("err_need")); return; }
    showLoading(results);
    setBusy(submit, true);
    try {
      const data = await api("/api/medicines/search", { method: "POST", json: { name, language: currentLang } });
      results.innerHTML = renderMedicine(data);
    } catch (err) {
      showError(results, err.message);
    } finally {
      setBusy(submit, false);
    }
  });

  function renderMedicine(d) {
    const r = d.result, src = d.source;
    // Could not identify it: ask for more information instead of guessing.
    if (!r.identified || r.needs_more_info) {
      return `<div class="alert alert-info" role="status">${icon("info")}<div><strong>${esc(d.query)}</strong>
        <p>${esc(r.clarification_message || "I could not confidently identify this medicine. Please type the full name, the strength, or the active ingredient printed on the strip.")}</p></div></div>${disclaimerHtml(d.disclaimer)}`;
    }
    const ai = badge("ai", t("badge_ai"));
    const sourceBadge = src.verified ? badge("ok", t("src_verified")) : badge("warn", t("src_unverified"));
    let sourceNote = "";
    if (src.verified) {
      const date = /^\d{8}$/.test(src.label_date || "") ? `${src.label_date.slice(0, 4)}-${src.label_date.slice(4, 6)}-${src.label_date.slice(6)}` : "";
      const names = [...(src.brand_names || []), ...(src.generic_names || [])].join(", ");
      sourceNote = `<p class="muted small">${esc(src.name)}${names ? ": " + esc(names) : ""}${date ? " (" + esc(date) + ")" : ""}. ${esc(t("src_us_note"))}</p>`;
    }
    let html = `<div class="card result-card">${aiLine()}
      <div class="med-title"><h2>${esc(r.medicine_name || d.query)}</h2>${r.generic_name ? `<span class="muted">${esc(t("m_generic"))}: ${esc(r.generic_name)}</span>` : ""}</div>
      <p style="margin-top:8px">${sourceBadge}</p>${sourceNote}`;
    html += section(t("m_uses"), listHtml(r.common_uses));
    html += section(t("m_how"), r.how_it_works ? `<p class="prose">${esc(r.how_it_works)}</p>` : "");
    html += section(t("m_side"), listHtml(r.common_side_effects));
    html += section(t("m_serious"), listHtml(r.serious_side_effects_seek_help));
    html += section(t("m_warn"), listHtml(r.important_warnings));
    html += section(t("m_inter"), listHtml(r.potential_interactions));
    html += section(t("m_storage"), r.storage ? `<p class="prose">${esc(r.storage)}</p>` : "");
    html += section(t("m_ask"), listHtml(r.questions_for_pharmacist_or_doctor));
    html += "</div>" + disclaimerHtml(d.disclaimer);
    return html;
  }
})();
