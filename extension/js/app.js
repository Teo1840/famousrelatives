// Arranque de la app dentro de la extensión (reemplaza a app.py).
// 1. Se asegura de que haya sesión de FamilySearch.
// 2. Descarga la lista de famosos de Supabase.
// 3. Arma los árboles guardados y se los pasa a main.js (window.arbolesPromise).
// 4. Busca en FamilySearch a las personas que todavía no se consultaron.
import { obtenerCuenta, esperarLogin, abrirFamilySearch, vigilarCambioDeCuenta } from "./session.js";
import { cargarFamosos } from "./famosos.js";
import { generateTrees, applyViewerPortrait, DEFAULT_PORTRAIT_URL } from "./trees.js";
import { obtenerArbolesUsuario, obtenerIdsProcesados, obtenerRetrato, borrarUsuario } from "./store.js";
import { SessionExpired } from "./fs-api.js";

// "Actualizar mis árboles" vuelve a consultar a todos: como mucho cada 5 minutos.
const FORCE_REFRESH_COOLDOWN_MS = 5 * 60 * 1000;

const $ = id => document.getElementById(id);
const sleep = ms => new Promise(r => setTimeout(r, ms));

let cuenta = null;                         // { personId, nombre }
let lista = { famosos: [], categorias: {} };

// Progreso de la búsqueda; main.js lo consulta con window.obtenerProgreso().
const estado = { running: false, current: 0, total: 0 };
let version = 0;           // sube cada vez que se guarda algo
let versionEntregada = -1; // la última que se le pasó a main.js

// procesando = true muestra el círculo animado (algo está en curso).
function mostrarAviso(texto, esError = false, procesando = false) {
  const el = $("app-aviso");
  el.textContent = texto || "";
  el.hidden = !texto;
  el.classList.toggle("error", esError);
  el.classList.toggle("procesando", procesando);
}

// --- Sesión ---

async function asegurarSesion() {
  let c;
  while (true) {
    try {
      c = await obtenerCuenta();
      break;
    } catch (e) {
      mostrarAviso(e.message, true);
      await sleep(5000);
    }
  }
  if (c) return c;

  mostrarAviso("");
  $("login-panel").hidden = false;
  c = await esperarLogin();
  $("login-panel").hidden = true;
  return c;
}

// --- Árboles para mostrar ---

// Misma forma que services/cards.py → serializar_arboles.
function serializar(a) {
  return {
    person_code: a.person_code,
    name: a.name || "",
    info: a.info || "",
    topics: a.topics || [],
    wiki: a.wiki || null,
    paises: a.paises || [],
    cercania: a.cercania || 0,
    relationshipDescription: a.relationshipDescription || "",
    portraitUrl: a.portraitUrl || DEFAULT_PORTRAIT_URL,
    coParentIsPathPerson: a.coParentIsPathPerson || false,
    coParentIsTargetPerson: a.coParentIsTargetPerson || false,
    mainPath: a.mainPath || { asc: [], desc: [] },
    directPath: a.directPath || null,
    direct_length: a.direct_length || 0,
    antepasado_comun: a.antepasado_comun || {},
    detalle: a.texto || "",
  };
}

// Árboles guardados + datos actuales de la lista (categorías, descripción,
// Wikipedia, países), así editar Supabase no obliga a volver a consultar
// FamilySearch. Las personas que se sacaron de la lista no se muestran.
async function armarArboles() {
  const [rows, retrato] = await Promise.all([
    obtenerArbolesUsuario(cuenta.personId),
    obtenerRetrato(cuenta.personId),
  ]);
  const porCodigo = new Map(lista.famosos.map(f => [f.person_code, f]));

  const arboles = [];
  for (const row of rows) {
    if (!row.found || !row.data) continue;
    const famoso = porCodigo.get(row.person_code);
    if (!famoso) continue;
    const tree = structuredClone(row.data);
    Object.assign(tree, {
      name: famoso.name, info: famoso.info, topics: famoso.topics,
      wiki: famoso.wiki, paises: famoso.paises,
    });
    if (retrato) applyViewerPortrait(tree, cuenta.personId, retrato);
    arboles.push(serializar(tree));
  }
  return arboles;
}

window.obtenerProgreso = async () => ({ ...estado });

// Devuelve la lista nueva si cambió algo (o siempre, con forzar), o null.
window.recargarArboles = async (forzar = false) => {
  if (!forzar && version === versionEntregada) return null;
  versionEntregada = version;
  return armarArboles();
};

// --- Personas nuevas (punto rojo) ---

async function contarNuevas() {
  if (!cuenta) return 0;
  const ids = await obtenerIdsProcesados(cuenta.personId);
  return lista.famosos.filter(f => !ids.has(f.person_code)).length;
}

async function actualizarPuntoNuevas() {
  const n = await contarNuevas();
  const msg = n ? (n === 1 ? "1 persona nueva para buscar" : `${n} personas nuevas para buscar`) : "";
  $("btn-actions-toggle").classList.toggle("has-dot", n > 0);
  $("btn-actions-toggle").title = msg || "Acciones";
  $("btn-buscar-nuevas").classList.toggle("has-dot", n > 0);
  $("btn-buscar-nuevas").title = msg;
  return n;
}

// --- Búsqueda en FamilySearch ---

async function buscar(forceRefresh = false) {
  if (estado.running || !lista.famosos.length) return;

  Object.assign(estado, { running: true, current: 0, total: lista.famosos.length });
  window.seguirProcesamiento?.();

  try {
    await generateTrees(lista.famosos, cuenta.personId, {
      forceRefresh,
      onProgress: current => { estado.current = current; version++; },
    });
  } catch (e) {
    if (e instanceof SessionExpired) {
      estado.running = false;
      mostrarAviso("Se cerró la sesión de FamilySearch.", true);
      $("login-panel").hidden = false;
      await esperarLogin();
      location.reload();
      return;
    }
    console.error(e);
    mostrarAviso("Hubo un error buscando parientes: " + e.message, true);
  } finally {
    estado.running = false;
    estado.current = estado.total;
    version++;
  }
  await actualizarPuntoNuevas();
}

async function actualizarTodo() {
  const key = "ultimoActualizar:" + cuenta.personId;
  const { [key]: ultimo } = await chrome.storage.local.get(key);
  const espera = ultimo ? FORCE_REFRESH_COOLDOWN_MS - (Date.now() - ultimo) : 0;
  if (espera > 0) {
    const mins = Math.floor(espera / 60000);
    const secs = Math.ceil((espera % 60000) / 1000);
    alert(`"Actualizar mis árboles" se puede usar una vez cada 5 minutos. Esperá ${mins}m ${secs}s.`);
    return;
  }
  const ok = confirm(
    "Vas a volver a consultar TODAS las personas en FamilySearch, ignorando lo guardado.\n\n" +
    "Para no saturar FamilySearch, las consultas van más lentas, así que puede tardar varios minutos.\n\n¿Continuar?"
  );
  if (!ok) return;
  await chrome.storage.local.set({ [key]: Date.now() });
  buscar(true);
}

// --- Menú de acciones ---

function conectarMenu() {
  const toggle = $("btn-actions-toggle");
  const actions = $("dashboard-actions");
  const cerrar = () => { actions.classList.remove("open"); toggle.classList.remove("active"); };

  toggle.addEventListener("click", () => {
    actions.classList.toggle("open");
    toggle.classList.toggle("active");
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".header-menu")) cerrar();
  });

  $("btn-buscar-nuevas").addEventListener("click", () => { cerrar(); buscar(false); });
  $("btn-actualizar").addEventListener("click", () => { cerrar(); actualizarTodo(); });
  $("btn-abrir-fs").addEventListener("click", () => { cerrar(); abrirFamilySearch(); });
  $("btn-borrar-datos").addEventListener("click", async () => {
    cerrar();
    if (estado.running) { alert("Esperá a que termine la búsqueda."); return; }
    if (!confirm("Se van a borrar los parientes guardados de esta cuenta en esta computadora. " +
                 "La próxima vez se vuelven a buscar en FamilySearch.\n\n¿Continuar?")) return;
    await borrarUsuario(cuenta.personId);
    location.reload();
  });
  $("btn-login").addEventListener("click", abrirFamilySearch);
}

// --- Inicio ---

async function iniciar() {
  mostrarAviso("Conectando con FamilySearch…", false, true);
  cuenta = await asegurarSesion();

  const estadoCuenta = $("cuenta-estado");
  estadoCuenta.textContent = `✓ ${cuenta.nombre}`;
  estadoCuenta.title = "Sesión de FamilySearch activa";
  estadoCuenta.hidden = false;

  mostrarAviso("Descargando la lista de famosos…", false, true);
  try {
    lista = await cargarFamosos();
    mostrarAviso(lista.offline ? "Sin conexión: se muestra la última lista de famosos guardada." : "");
  } catch (e) {
    mostrarAviso(e.message, true);
  }
  window.CATEGORIAS = lista.categorias;

  const arboles = await armarArboles();
  versionEntregada = version;
  return arboles;
}

conectarMenu();
window.arbolesPromise = iniciar();

// Después de que main.js dibuje (su .then corre antes que este setTimeout).
window.arbolesPromise.then(() => setTimeout(async () => {
  // Si entra otra cuenta de FamilySearch (o se cierra la sesión), recargar.
  vigilarCambioDeCuenta(async () => {
    let c;
    try { c = await obtenerCuenta(); } catch (_) { return; }
    if (c?.personId !== cuenta.personId) location.reload();
  });

  const nuevas = await actualizarPuntoNuevas();
  if (nuevas > 0) buscar(false);
}, 0));
