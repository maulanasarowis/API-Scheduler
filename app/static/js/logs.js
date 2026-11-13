const detailModal = new bootstrap.Modal(document.getElementById("detailModal"));

document.querySelectorAll(".btn-detail").forEach(b => b.onclick = async () => {
  try {
    const d = await request(`/api/logs/${b.dataset.id}`);
    const meta = document.getElementById("d-meta");
    meta.innerHTML = "";
    [["API", d.api_name], ["Waktu", d.executed_at], ["Status Code", d.status_code ?? "-"],
     ["Hasil", d.success ? "Berhasil" : "Gagal"], ["Durasi", d.duration_ms + " ms"], ["Pemicu", d.trigger]]
      .forEach(([k, v]) => {
        const dt = document.createElement("dt"); dt.className = "col-4 col-md-3"; dt.textContent = k;
        const dd = document.createElement("dd"); dd.className = "col-8 col-md-9"; dd.textContent = v;
        meta.append(dt, dd);
      });
    document.getElementById("d-error-wrap").classList.toggle("d-none", !d.error_message);
    document.getElementById("d-error").textContent = d.error_message;
    let resp = d.response;
    try { resp = JSON.stringify(JSON.parse(resp), null, 2); } catch (e) {}
    document.getElementById("d-response").textContent = resp || "(kosong)";
    detailModal.show();
  } catch (e) { showToast(e.message, "danger"); }
});
