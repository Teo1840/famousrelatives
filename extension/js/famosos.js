// Lista de famosos y descripciones de categorías desde Supabase.
// Si no hay conexión se usa la última copia que se pudo descargar.
import { SUPABASE_URL, SUPABASE_ANON_KEY } from "../config.js";

const CACHE_KEY = "famososCache";

async function leerTabla(tabla) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${tabla}?select=*`, {
    headers: { apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}` },
  });
  if (!r.ok) throw new Error(`Supabase ${tabla}: HTTP ${r.status}`);
  return r.json();
}

function normalizar(f) {
  return {
    person_code: (f.person_code || "").trim(),
    name: f.name || "",
    info: f.info || "",
    topics: f.topics || [],
    paises: f.paises || [],
    wiki: f.wiki || null,
  };
}

// { famosos: [...], categorias: { nombre: descripcionHtml }, offline: bool }
export async function cargarFamosos() {
  try {
    const [famosos, categorias] = await Promise.all([leerTabla("famosos"), leerTabla("categorias")]);
    const data = {
      famosos: famosos.map(normalizar).filter(f => f.person_code && f.name),
      categorias: Object.fromEntries(
        categorias.filter(c => c.descripcion).map(c => [c.nombre, c.descripcion])
      ),
    };
    await chrome.storage.local.set({ [CACHE_KEY]: data });
    return { ...data, offline: false };
  } catch (err) {
    console.warn("No se pudo descargar la lista de famosos:", err);
    const { [CACHE_KEY]: cached } = await chrome.storage.local.get(CACHE_KEY);
    if (cached) return { ...cached, offline: true };
    throw new Error("No se pudo descargar la lista de famosos. Revisá tu conexión a internet.", { cause: err });
  }
}
