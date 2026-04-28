import { showPopup, prevPopup, nextPopup, closePopup } from './popup.js';
import { initSwitches } from './switch.js';
import { generarUUID } from './utils.js';

// 🔗 Exponer para HTML (porque usás onclick)
window.prevPopup = prevPopup;
window.nextPopup = nextPopup;
window.closePopup = closePopup;

// Estado global
window.fullList = window.arboles;
window.coParentIsTargetPersonList = window.fullList.filter(a => {
  const isTarget = a.coParentIsTargetPerson;
  const hasDirect = a.directPath != null;

  return !(isTarget && !hasDirect);
});

window.currentIndex = 0;

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  initSwitches();

  document.querySelectorAll('.card').forEach((card, i) => {
    card.dataset.id = card.dataset.id || generarUUID();

    card.addEventListener('click', (event) => {
      event.stopPropagation();

      const list = getActiveList();

      const realIndex = list.findIndex(item =>
        item.person_code === window.fullList[i].person_code
      );

      window.currentIndex = realIndex !== -1 ? realIndex : 0;

      showPopup(window.currentIndex);

      document.getElementById('popup').style.display = 'flex';
    });
  });
});

export function getActiveList() {
  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  return toggle.checked
    ? window.coParentIsTargetPersonList
    : window.fullList;
}