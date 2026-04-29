import { showPopup, prevPopup, nextPopup, closePopup } from './popup.js';
import { initSwitches } from './switch.js';
import { renderCards } from './card.js';

// 🔗 Exponer para HTML (onclick del popup)
window.prevPopup = prevPopup;
window.nextPopup = nextPopup;
window.closePopup = closePopup;

// Estado global
window.fullList = window.arboles;
window.coParentIsTargetPersonList = get_coParentIsTargetPersonList();
window.currentIndex = 0;

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  initSwitches();
  renderCards(getActiveList());
});

// 🔎 Lista activa según switch
export function getActiveList() {
  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  return toggle?.checked
    ? window.coParentIsTargetPersonList
    : window.fullList;
}

// 🔢 Actualiza contador
export function updateListCount() {
  const el = document.getElementById("list-count");
  if (!el) return;

  const list = getActiveList();
  el.textContent = list.length;
}

// 🧠 Genera lista filtrada
function get_coParentIsTargetPersonList() {
  return window.arboles
    .filter(a => !(a.coParentIsTargetPerson && a.directPath == null))
    .sort((a, b) => (a.direct_length || 0) - (b.direct_length || 0));
}