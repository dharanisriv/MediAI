/* Medical Report Explainer page */
(() => {
  const MAX_BYTES = 8 * 1024 * 1024;
  const ALLOWED = ["jpg", "jpeg", "png", "webp", "pdf", "txt"];

  const form = document.getElementById("report-form");
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file");
  const preview = document.getElementById("preview");
  const results = document.getElementById("results");
  const submit = document.getElementById("submit");
  let selectedFile = null;
  let previewUrl = null;

  showEmpty(results, "file");

  /* ----- choosing a file (click, keyboard or drag and drop) ----- */
  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); } });
  fileInput.addEventListener("change", () => { if (fileInput.files[0]) setFile(fileInput.files[0]); });
  ["dragenter", "dragover"].forEach((ev) => dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) => dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag"); }));
  dropzone.addEventListener("drop", (e) => { if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });

  function setFile(file) {
    const ext = (file.name.split(".").pop() || "").toLowerCase();
    if (!ALLOWED.includes(ext) || file.size > MAX_BYTES || file.size === 0) {
      clearFile();
      showError(results, t("err_file"));
      return;
    }
    selectedFile = file;
    showPreview(file, ext);
    showEmpty(results, "file");
  }

  function clearFile() {
    selectedFile = null;
    fileInput.value = "";
    if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = null; }
    preview.hidden = true;
    preview.innerHTML = "";
  }

  function showPreview(file, ext) {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = URL.createObjectURL(file);
    preview.hidden = false;
    preview.innerHTML = `<div class="preview-head"><span>${esc(t("uploaded_preview"))}: ${esc(file.name)}</span>
      <button type="button" class="btn btn-ghost" id="remove-file">${icon("x")} ${esc(t("remove_file"))}</button></div><div id="preview-body"></div>`;
    const body = preview.querySelector("#preview-body");
    if (ext === "pdf") {
      body.innerHTML = `<iframe title="PDF preview" src="${previewUrl}"></iframe>`;
    } else if (ext === "txt") {
      const reader = new FileReader();
      reader.onload = () => { body.innerHTML = `<pre>${esc(String(reader.result).slice(0, 3000))}</pre>`; };
      reader.readAsText(file);
    } else {
      body.innerHTML = `<img alt="" src="${previewUrl}">`;
    }
    preview.querySelector("#remove-file").addEventListener("click", clearFile);
  }

  /* ----- sending to the backend ----- */
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = document.getElementById("text").value.trim();
    if (!selectedFile && text.length < 20) { showError(results, t("err_need")); return; }

    const data = new FormData();
    data.append("language", currentLang);
    data.append("text", text);
    data.append("question", document.getElementById("question").value.trim());
    if (selectedFile) data.append("file", selectedFile, selectedFile.name);

    showLoading(results);
    setBusy(submit, true);
    try {
      const answer = await api("/api/report/analyze", { method: "POST", formData: data });
      results.innerHTML = renderReport(answer);
    } catch (err) {
      showError(results, err.message);
    } finally {
      setBusy(submit, false);
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });

  /* ----- showing the answer ----- */
  const FLAG = {
    high: ["high", "flag_high"], low: ["low", "flag_low"], normal: ["ok", "flag_normal"],
    abnormal_other: ["warn", "flag_other"], not_determined: ["neutral", "flag_unknown"],
  };

  function labItem(v) {
    const [kind, key] = FLAG[v.flag] || FLAG.not_determined;
    return `<div class="lab-item">
      <div class="lab-top"><span class="lab-name">${esc(v.test)}</span>${badge(kind, t(key))}</div>
      <div class="lab-nums">
        <span><small>${esc(t("col_value"))}</small><strong>${esc(v.value)} ${esc(v.unit)}</strong></span>
        <span><small>${esc(t("col_range"))}</small><strong>${esc(v.reference_range)}</strong></span>
      </div>
      ${v.purpose ? `<p class="lab-purpose">${esc(v.purpose)}</p>` : ""}
      ${v.meaning ? `<p class="lab-meaning">${esc(v.meaning)}</p>` : ""}
    </div>`;
  }

  function renderReport(d) {
    const r = d.result;
    const ai = badge("ai", t("badge_ai"));
    const terms = r.medical_terms.map((m) => `<div class="dl-item"><b>${esc(m.term)}</b>${esc(m.explanation)}</div>`).join("");
    let html = `<div class="card result-card">${aiLine()}`;
    html += section(t("summary_h"), `<p class="prose">${esc(r.plain_summary)}</p>${r.report_type ? `<p class="muted small">${esc(r.report_type)}</p>` : ""}`, ai);
    html += section(t("r_answer"), r.answer_to_user_question ? `<p class="prose">${esc(r.answer_to_user_question)}</p>` : "", ai);
    html += section(t("r_values"), r.lab_values.map(labItem).join(""), ai);
    html += section(t("r_findings"), listHtml(r.key_findings), ai);
    html += section(t("r_terms"), terms, ai);
    html += section(t("r_indicate"), listHtml(r.what_it_may_generally_indicate), ai);
    html += section(t("questions_doctor"), listHtml(r.questions_for_doctor), ai);
    html += "</div>";

    const notes = [...(d.warnings || []), r.readability_note].filter(Boolean);
    if (notes.length) html += `<div class="alert alert-warn">${icon("alert")}<div>${notes.map((n) => `<p>${esc(n)}</p>`).join("")}</div></div>`;
    html += `<div class="card"><details class="extract"><summary>${esc(t("extracted_text"))} ${badge("user", t("badge_user"))}</summary><pre>${esc(d.extracted_text)}</pre></details></div>`;
    html += disclaimerHtml(d.disclaimer);
    return html;
  }
})();
