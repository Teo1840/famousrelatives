import { showPopup, prevPopup, nextPopup, closePopup } from './popup.js';
import { initSwitches, refrescarLista, refrescarTemas } from './switch.js';

// Lista activa según switch
export function getActiveList() {
  const targetToggle = document.getElementById("switch-coParentIsTargetPerson");
  const pathToggle = document.getElementById("switch-coParentIsPathPerson");

  if (targetToggle?.checked && pathToggle?.checked) {
    return window.Target_and_PathList;
  }

  if (targetToggle?.checked) {
    return window.TargetList;
  }

  if (pathToggle?.checked) {
    return window.PathList;
  }

  return window.fullList;
}

// Actualiza contador
export function updateListCount(list) {
  const el = document.getElementById("list-count");
  if (!el) return;

  const activeList = list ?? getActiveList();
  el.textContent = activeList.length;
}

// Generar listas filtradas (el orden lo pone switch.js → update()).
// Solo "a través del cónyuge de la persona": se queda si hay camino directo
// por sangre, aunque ese camino pase por mi cónyuge (ese es el otro switch).
function get_TargetList() {
  return window.arboles.filter(a => !a.coParentIsTargetPerson || a?.directPath != null);
}

function get_PathList() {
  return window.arboles.filter(a => {
    const main = a?.mainPath?.coParentIsPathPerson;
    const direct = a?.directPath?.coParentIsPathPerson;
    return !(main && (direct ?? true));
  });
}

function get_Target_and_PathList() {
  return window.arboles.filter(a => {
    const mainIsClean = !a.coParentIsTargetPerson && !a?.mainPath?.coParentIsPathPerson;
    const directIsClean = a?.directPath != null && !a?.directPath?.coParentIsPathPerson;
    return mainIsClean || directIsClean;
  });
}

// Cercanía del camino que se está mostrando (principal o directo).
export function getSortLength(a) {
  return shouldUseDirectPath(a)
    ? (a.direct_length ?? Infinity)
    : (a.cercania ?? Infinity);
}

export function getSortMinSideLength(a) {
  const path = getDisplayedPath(a);
  const asc  = path?.asc?.length  ?? Infinity;
  const desc = path?.desc?.length ?? Infinity;
  return Math.min(asc, desc);
}

// Si la tarjeta muestra el camino directo en vez del principal (según switches).
export function shouldUseDirectPath(a) {
  const targetToggle = document.getElementById("switch-coParentIsTargetPerson");
  const pathToggle   = document.getElementById("switch-coParentIsPathPerson");
  const mainIsPath   = a?.mainPath?.coParentIsPathPerson;
  const directIsPath = a?.directPath?.coParentIsPathPerson;

  if (targetToggle?.checked && a?.coParentIsTargetPerson && a?.directPath != null) return true;
  if (pathToggle?.checked && mainIsPath && !(directIsPath ?? true)) return true;
  return false;
}

export function getDisplayedPath(a) {
  return (shouldUseDirectPath(a) ? a.directPath : a.mainPath) || {};
}

// --- Filtro por ancestro (padres / abuelos) ---
// 1 = padres, 2 = abuelos, 3 = bisabuelos.
const MAX_GEN_ANCESTRO = 3;

// ID del usuario: la última persona de "asc" que más se repite entre los árboles.
export function getViewerId(arboles) {
  const counts = new Map();
  (arboles || []).forEach(a => {
    const id = a?.mainPath?.asc?.at(-1)?.id;
    if (id) counts.set(id, (counts.get(id) || 0) + 1);
  });
  let best = null;
  counts.forEach((n, id) => { if (best === null || n > counts.get(best)) best = id; });
  return best;
}

// Ancestros propios del usuario por los que pasa el camino:
// [{ person, gen }] con gen 1 = padre/madre, 2 = abuelo/a...
// Vacío si el camino sube por el cónyuge (no son ancestros propios).
export function getViewerAncestors(path, viewerId) {
  if (!path || path.coParentIsPathPerson) return [];
  const asc = path.asc || [];
  if (!asc.length || (viewerId && asc.at(-1)?.id !== viewerId)) return [];

  const line = [...asc].reverse();
  if (path.antepasado_comun?.id) line.push(path.antepasado_comun);

  return line
    .slice(1, MAX_GEN_ANCESTRO + 1)
    .map((person, i) => ({ person, gen: i + 1 }))
    .filter(x => x.person?.id);
}

// 🔗 Exponer para HTML (onclick del popup)
window.showPopup = showPopup;
window.prevPopup = prevPopup;
window.nextPopup = nextPopup;
window.closePopup = closePopup;

// Estado global
window.currentIndex = 0;
window.activeTopicFilter = null;
window.activeAncestorFilter = null;
window.activePaisFilter = null;

function iniciarDashboard() {
  window.fullList = window.arboles;
  window.TargetList = get_TargetList();
  window.PathList = get_PathList();
  window.Target_and_PathList = get_Target_and_PathList();

  initSwitches();
  // Primer dibujo con todos los filtros (tema, cercanía, ancestro) y el orden.
  refrescarLista();
}

function domListo() {
  return document.readyState === "loading"
    ? new Promise(resolve => document.addEventListener("DOMContentLoaded", resolve, { once: true }))
    : Promise.resolve();
}

// Reemplaza los datos y redibuja manteniendo filtros, slider y orden.
function actualizarDatos(data) {
  window.arboles = data;
  window.fullList = data;
  window.TargetList = get_TargetList();
  window.PathList = get_PathList();
  window.Target_and_PathList = get_Target_and_PathList();
  refrescarTemas();
  refrescarLista();
}

function popupAbierto() {
  return document.getElementById("popup")?.style.display === "flex";
}

// Mientras se buscan parientes en segundo plano, los va mostrando a medida
// que se guardan. Solo en la extensión (no en el HTML exportado).
// app.js la vuelve a llamar cada vez que arranca una búsqueda.
let siguiendo = false;
function seguirProcesamiento() {
  if (!window.recargarArboles || !window.obtenerProgreso || siguiendo) return;
  siguiendo = true;

  const aviso = document.getElementById("progreso-busqueda");
  let ultimoCurrent = -1;
  let pendiente = false;

  async function aplicar(forzar) {
    if (popupAbierto()) {
      pendiente = true;  // no mover las tarjetas con el popup abierto
      return;
    }
    const data = await window.recargarArboles(forzar);
    if (data) actualizarDatos(data);
    pendiente = false;
  }

  async function tick() {
    const estado = await window.obtenerProgreso();

    if (!estado.running) {
      if (aviso) aviso.hidden = true;
      // Si se procesó algo mientras mirábamos, traer la versión final.
      if (ultimoCurrent >= 0 || pendiente) {
        if (popupAbierto()) {
          setTimeout(tick, 2000);
          return;
        }
        // Antes del await: si arranca otra búsqueda justo ahora, que la siga.
        siguiendo = false;
        await aplicar(true);
      }
      siguiendo = false;
      return;
    }

    if (aviso) {
      aviso.hidden = false;
      aviso.textContent = `Buscando parientes… ${estado.current} / ${estado.total}`;
    }
    if (estado.current !== ultimoCurrent || pendiente) {
      ultimoCurrent = estado.current;
      await aplicar(false);
    }
    setTimeout(tick, 2000);
  }

  tick();
}
window.seguirProcesamiento = seguirProcesamiento;

// Eventos del popup (antes eran onclick="..." en el HTML, que las extensiones
// no permiten). Vive acá para que también funcione en el HTML exportado.
function conectarPopup() {
  const popup = document.getElementById("popup");
  if (!popup) return;
  popup.addEventListener("click", closePopup);
  popup.querySelector(".popup-nav.left")?.addEventListener("click", prevPopup);
  popup.querySelector(".popup-nav.right")?.addEventListener("click", nextPopup);
  popup.querySelector(".popup-content")?.addEventListener("click", e => e.stopPropagation());
  popup.querySelector(".popup-close")?.addEventListener("click", closePopup);
}

// Inicialización. En el dashboard los datos llegan por arboles-cache.js
// (window.arbolesPromise); en el HTML exportado offline vienen ya en window.arboles.
Promise.all([Promise.resolve(window.arbolesPromise || window.arboles || []), domListo()])
  .then(([data]) => {
    window.arboles = data;
    conectarPopup();
    iniciarDashboard();
    seguirProcesamiento();
  });