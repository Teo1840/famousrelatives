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
showPopup(window.currentIndex);

// Inicialización
document.addEventListener("DOMContentLoaded", () => {
  initSwitches();

  document.querySelectorAll('.card').forEach((card, i) => {
    card.dataset.id = card.dataset.id || generarUUID();

    card.addEventListener('click', (event) => {
      event.stopPropagation();

      window.currentIndex = i;
      showPopup(window.currentIndex);

      document.getElementById('popup').style.display = 'flex';
    });
  });
});