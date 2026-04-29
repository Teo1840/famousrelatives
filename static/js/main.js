import { showPopup, prevPopup, nextPopup, closePopup } from './popup.js';
import { initSwitches } from './switch.js';
import { renderCards } from './card.js';

// 🔗 Exponer para HTML (onclick del popup)
window.prevPopup = prevPopup;
window.nextPopup = nextPopup;
window.closePopup = closePopup;

// Estado global
window.fullList = window.arboles;
window.TargetList = get_TargetList();
window.PathList = get_PathList();
window.Target_and_PathList = get_Target_and_PathList();
window.currentIndex = 0;

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  initSwitches();
  renderCards(getActiveList());
});

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
    .filter(a => !(a.coParentIsTargetPerson && a.directPath == null))
    .sort((a, b) => (a.direct_length || 0) - (b.direct_length || 0));
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
    const isTarget = !(a.coParentIsTargetPerson && a.directPath == null);

    const main = a?.mainPath?.coParentIsPathPerson;
    const direct = a?.directPath?.coParentIsPathPerson;
    const isPath = !(main && (direct ?? true));

    return isTarget && isPath;
  });
}