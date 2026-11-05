import { showPopup, prevPopup, nextPopup, closePopup } from './popup.js';
import { initSwitches, refrescarLista, refrescarTemas } from './switch.js';
import { renderCards } from './card.js';

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

// Generar listas filtradas
function get_TargetList() {
  return window.arboles
    .filter(a => {
      const directIsClean = a?.directPath != null && !a?.directPath?.coParentIsPathPerson;
      return !a.coParentIsTargetPerson || directIsClean;
    })
    .sort((a, b) => getEffectiveLength(a) - getEffectiveLength(b));
}

function get_PathList() {
  return window.arboles
    .filter(a => {
      const main = a?.mainPath?.coParentIsPathPerson;
      const direct = a?.directPath?.coParentIsPathPerson;

      return !(main && (direct ?? true));
    })
    .sort((a, b) => getEffectiveLength(a) - getEffectiveLength(b));
}

function get_Target_and_PathList() {
  return window.arboles
    .filter(a => {
      const mainIsClean = !a.coParentIsTargetPerson && !a?.mainPath?.coParentIsPathPerson;
      const directIsClean = a?.directPath != null && !a?.directPath?.coParentIsPathPerson;
      return mainIsClean || directIsClean;
    })
    .sort((a, b) => getEffectiveLength(a) - getEffectiveLength(b));
}

function getEffectiveLength(a) {
  const main = a?.mainPath?.coParentIsPathPerson;
  const direct = a?.directPath?.coParentIsPathPerson;
  const useDirect = a?.directPath && !(main && (direct ?? true));
  return useDirect
    ? (a.direct_length ?? Infinity)
    : (a.cercania ?? Infinity);
}

export function getSortLength(a) {
  const targetToggle = document.getElementById("switch-coParentIsTargetPerson");
  const pathToggle   = document.getElementById("switch-coParentIsPathPerson");
  const mainIsPath   = a?.mainPath?.coParentIsPathPerson;
  const directIsPath = a?.directPath?.coParentIsPathPerson;

  const useDirectForPath   = pathToggle?.checked   && mainIsPath && !(directIsPath ?? true);
  const useDirectForTarget = targetToggle?.checked && a?.coParentIsTargetPerson && a?.directPath != null;

  return (useDirectForPath || useDirectForTarget)
    ? (a.direct_length ?? Infinity)
    : (a.cercania ?? Infinity);
}

export function getSortMinSideLength(a) {
  const targetToggle = document.getElementById("switch-coParentIsTargetPerson");
  const pathToggle   = document.getElementById("switch-coParentIsPathPerson");
  const mainIsPath   = a?.mainPath?.coParentIsPathPerson;
  const directIsPath = a?.directPath?.coParentIsPathPerson;

  const useDirectForPath   = pathToggle?.checked   && mainIsPath && !(directIsPath ?? true);
  const useDirectForTarget = targetToggle?.checked && a?.coParentIsTargetPerson && a?.directPath != null;

  const path = (useDirectForPath || useDirectForTarget) ? a.directPath : a.mainPath;
  const asc  = path?.asc?.length  ?? Infinity;
  const desc = path?.desc?.length ?? Infinity;
  return Math.min(asc, desc);
}

// 🔗 Exponer para HTML (onclick del popup)
window.showPopup = showPopup;
window.prevPopup = prevPopup;
window.nextPopup = nextPopup;
window.closePopup = closePopup;

// Estado global
window.currentIndex = 0;
window.activeTopicFilter = null;

function iniciarDashboard() {
  window.fullList = window.arboles;
  window.TargetList = get_TargetList();
  window.PathList = get_PathList();
  window.Target_and_PathList = get_Target_and_PathList();

  initSwitches();

  let list = getActiveList();
  const sortByAscToggle = document.getElementById("switch-sortByAsc");
  list = [...list].sort(sortByAscToggle?.checked
    ? (a, b) => getSortMinSideLength(a) - getSortMinSideLength(b)
    : (a, b) => getSortLength(a) - getSortLength(b)
  );
  renderCards(list);
  updateListCount(list);
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

// Mientras el servidor procesa árboles en segundo plano, los va mostrando
// a medida que se guardan. Solo en el dashboard (no en el HTML exportado).
function seguirProcesamiento() {
  if (!window.recargarArboles) return;

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
    let estado;
    try {
      const r = await fetch("/progress", { credentials: "same-origin" });
      estado = await r.json();
    } catch (_) {
      setTimeout(tick, 4000);
      return;
    }

    if (!estado.running) {
      if (aviso) aviso.hidden = true;
      // Si se procesó algo mientras mirábamos, traer la versión final.
      if (ultimoCurrent >= 0 || pendiente) {
        if (popupAbierto()) {
          setTimeout(tick, 2000);
          return;
        }
        await aplicar(true);
      }
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

// Inicialización. En el dashboard los datos llegan por arboles-cache.js
// (window.arbolesPromise); en el HTML exportado offline vienen ya en window.arboles.
Promise.all([Promise.resolve(window.arbolesPromise || window.arboles || []), domListo()])
  .then(([data]) => {
    window.arboles = data;
    iniciarDashboard();
    seguirProcesamiento();
  });