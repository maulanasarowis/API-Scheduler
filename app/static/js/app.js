function showToast(message, type = "success") {
  const el = document.createElement("div");
  el.className = `toast align-items-center text-bg-${type} border-0`;
  el.innerHTML = `<div class="d-flex"><div class="toast-body"></div><button class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
  el.querySelector(".toast-body").textContent = message;
  document.getElementById("toasts").appendChild(el);
  const t = new bootstrap.Toast(el, { delay: 4000 });
  el.addEventListener("hidden.bs.toast", () => el.remove());
  t.show();
}

function flash(message, type = "success") {
  sessionStorage.setItem("flash", JSON.stringify({ message, type }));
  location.reload();
}

async function request(url, method = "GET", data) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: data ? JSON.stringify(data) : undefined,
  });
  let json = null;
  try { json = await res.json(); } catch (e) {}
  if (!res.ok) {
    let msg = "Terjadi kesalahan";
    if (json && json.detail) {
      msg = Array.isArray(json.detail)
        ? json.detail.map(d => d.msg.replace(/^Value error, /, "")).join("; ")
        : json.detail;
    }
    throw new Error(msg);
  }
  return json;
}

document.addEventListener("DOMContentLoaded", () => {
  const f = sessionStorage.getItem("flash");
  if (f) {
    sessionStorage.removeItem("flash");
    const { message, type } = JSON.parse(f);
    showToast(message, type);
  }
});
