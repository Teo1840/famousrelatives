import { buildGraph } from '/static/js/graph.js';
import { generarUUID } from './utils.js';

export function getActiveList() {
  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  return toggle.checked
    ? window.coParentIsTargetPersonList
    : window.fullList;
}

export function showPopup(currentIndex) {
  const list = getActiveList();
  const a = list[currentIndex];

  // Info textual
  document.getElementById('popup-body').innerHTML = `
    <h3>${a.nombre}</h3>
    <img src="${a.portraitUrl || 'https://via.placeholder.com/200'}" width="200">
    <p><i>${a.relacion || ''}</i></p>
    <p><b>Cercanía:</b> ${a.cercania || ''}</p>
    <p>${a.detalle || ''}</p>
    <pre>${a.detalle || ''}</pre>`;

  // Renderizar grafo
  const toggle = document.getElementById("switch-coParentIsTargetPerson");

  const { nodes, edges } = buildGraph(
    a,
    generarUUID,
    toggle.checked
  );
  
  const container = document.getElementById('mynetwork');

  if (window.network) window.network.destroy();

  const data = {
    nodes: new vis.DataSet(nodes),
    edges: new vis.DataSet(edges)
  };

  const options = {
    physics: false,
    edges: {
      smooth: {
        type: "cubicBezier",
        roundness: 0.5
      }
    }
  };

  window.network = new vis.Network(container, data, options);
  window.network.moveTo({
    position: { x: 0, y: 0 },
    scale: 1/3
  });
}

export function closePopup() {
  document.getElementById('popup').style.display = 'none';
}

export function nextPopup(e) {
  e.stopPropagation();

  const list = getActiveList();
  if (!list?.length) return;

  window.currentIndex = (window.currentIndex + 1) % list.length;

  showPopup(window.currentIndex);
}

export function prevPopup(e) {
  e.stopPropagation();

  const list = getActiveList();
  if (!list?.length) return;

  window.currentIndex =
    (window.currentIndex - 1 + list.length) % list.length;

  showPopup(window.currentIndex);
}