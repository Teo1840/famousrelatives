import { showPopup, prevPopup, nextPopup, closePopup } from './popup.js';
import { initSwitches } from './switch.js';
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
export function updateListCount() {
  const el = document.getElementById("list-count");
  if (!el) return;

  const list = getActiveList();
  el.textContent = list.length;
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

export function getEffectiveMinSideLength(a) {
  const main   = a?.mainPath?.coParentIsPathPerson;
  const direct = a?.directPath?.coParentIsPathPerson;
  const useDirect = a?.directPath && !(main && (direct ?? true));

  const path = useDirect ? a.directPath : a.mainPath;
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
window.fullList = window.arboles;
window.currentIndex = 0;

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  window.TargetList = get_TargetList();
  window.PathList = get_PathList();
  window.Target_and_PathList = get_Target_and_PathList();

  initSwitches();

  const list = getActiveList();
  renderCards(list);
  updateListCount();
});