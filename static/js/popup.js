import { buildGraph } from '/static/js/graph.js';
import { generarUUID } from './utils.js';

export function showPopup(arboles, currentIndex, generarUUID) {
  const a = arboles[currentIndex];

  // Info textual
  document.getElementById('popup-body').innerHTML = `
    <h3>${a.nombre}</h3>
    <img src="${a.portraitUrl || 'https://via.placeholder.com/200'}" width="200">
    <p><i>${a.relacion || ''}</i></p>
    <p><b>Cercanía:</b> ${a.cercania || ''}</p>
    <p>${a.extra || ''}</p>
    <pre>${a.detalle || ''}</pre>`;

  // Renderizar grafo
  const { nodes, edges } = buildGraph(a, generarUUID);
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
  if (!window.arboles || window.arboles.length === 0) return;

  window.currentIndex = (window.currentIndex + 1) % window.arboles.length;
  showPopup(window.arboles, window.currentIndex, generarUUID);
}

export function prevPopup(e) {
  e.stopPropagation();
  if (!window.arboles || window.arboles.length === 0) return;

  window.currentIndex =
    (window.currentIndex - 1 + window.arboles.length) % window.arboles.length;

  showPopup(window.arboles, window.currentIndex, generarUUID);
}