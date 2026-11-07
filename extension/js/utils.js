export function generarUUID() {
  if (typeof self.crypto?.randomUUID === 'function') {
    return self.crypto.randomUUID();
  } else {
    return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
  }
}

// Texto que viene de afuera (FamilySearch, Supabase) → seguro para meter en
// innerHTML. Los nombres del árbol de FamilySearch los puede editar cualquiera.
export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Solo deja pasar links http(s); cualquier otra cosa (javascript:, data:...) → fallback.
export function safeUrl(value, fallback = "") {
  try {
    const url = new URL(String(value ?? ""));
    if (url.protocol === "https:" || url.protocol === "http:") return escapeHtml(url.href);
  } catch (_) {
    // no es una URL válida
  }
  return escapeHtml(fallback);
}
