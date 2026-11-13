const modal = new bootstrap.Modal(document.getElementById("apiModal"));
const $ = id => document.getElementById(id);
let editId = null;
let times = [];

function renderTimes() {
  const box = $("times-list");
  box.innerHTML = "";
  if (!times.length) box.innerHTML = '<span class="text-muted small">Belum ada jadwal.</span>';
  times.forEach(t => {
    const chip = document.createElement("span");
    chip.className = "time-chip";
    chip.innerHTML = `<i class="bi bi-clock"></i> ${t} <button type="button" title="Hapus"><i class="bi bi-x-lg"></i></button>`;
    chip.querySelector("button").onclick = () => { times = times.filter(x => x !== t); renderTimes(); };
    box.appendChild(chip);
  });
}

function addTime() {
  const v = $("f-time").value;
  if (v && !times.includes(v)) { times.push(v); times.sort(); renderTimes(); }
  $("f-time").value = "";
}

function openForm(api) {
  editId = api ? api.id : null;
  $("modal-title").textContent = api ? "Edit API" : "Tambah API";
  $("f-name").value = api?.name || "";
  $("f-url").value = api?.url || "";
  $("f-method").value = api?.method || "GET";
  $("f-headers").value = api?.headers || "";
  $("f-body").value = api?.body || "";
  $("f-timeout").value = api?.timeout || 30;
  $("f-active").checked = api ? api.is_active : true;
  times = api ? [...api.schedules] : [];
  $("f-time").value = "";
  renderTimes();
  modal.show();
}

$("btn-add").onclick = () => openForm(null);
$("btn-add-time").onclick = addTime;

$("btn-save").onclick = async () => {
  addTime();
  const payload = {
    name: $("f-name").value,
    url: $("f-url").value,
    method: $("f-method").value,
    headers: $("f-headers").value,
    body: $("f-body").value,
    timeout: parseInt($("f-timeout").value) || 30,
    is_active: $("f-active").checked,
    schedules: times,
  };
  try {
    if (editId) await request(`/api/configs/${editId}`, "PUT", payload);
    else await request("/api/configs", "POST", payload);
    flash("API berhasil disimpan");
  } catch (e) { showToast(e.message, "danger"); }
};

document.querySelectorAll(".btn-edit").forEach(b => b.onclick = () => openForm(JSON.parse(b.dataset.api)));

document.querySelectorAll(".btn-delete").forEach(b => b.onclick = async () => {
  if (!confirm(`Hapus API "${b.dataset.name}"? Jadwal ikut terhapus.`)) return;
  try { await request(`/api/configs/${b.dataset.id}`, "DELETE"); flash("API dihapus"); }
  catch (e) { showToast(e.message, "danger"); }
});

document.querySelectorAll(".btn-toggle").forEach(b => b.onclick = async () => {
  try {
    const r = await request(`/api/configs/${b.dataset.id}/toggle`, "POST");
    flash(r.is_active ? "API diaktifkan" : "API dinonaktifkan");
  } catch (e) { showToast(e.message, "danger"); }
});

document.querySelectorAll(".btn-run").forEach(b => b.onclick = async () => {
  b.disabled = true;
  b.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
  try {
    const r = await request(`/api/configs/${b.dataset.id}/run`, "POST");
    flash(r.success ? `Berhasil (HTTP ${r.status_code}, ${r.duration_ms} ms)` : `Gagal: ${r.error || "error"}`,
          r.success ? "success" : "danger");
  } catch (e) { showToast(e.message, "danger"); b.disabled = false; b.innerHTML = '<i class="bi bi-play-fill"></i>'; }
});
