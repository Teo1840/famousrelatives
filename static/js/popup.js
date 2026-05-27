import { buildGraph } from '/static/js/graph.js';
import { getActiveList } from './main.js';
import { generarUUID } from './utils.js';
import { computeRelationshipDescription } from './relationship.js';

function shouldUseDirectPath(a) {
  const targetToggle = document.getElementById("switch-coParentIsTargetPerson");
  const pathToggle   = document.getElementById("switch-coParentIsPathPerson");
  const mainIsPath   = a?.mainPath?.coParentIsPathPerson;
  const directIsPath = a?.directPath?.coParentIsPathPerson;

  if (targetToggle?.checked && a?.coParentIsTargetPerson && a?.directPath != null) return true;
  if (pathToggle?.checked && mainIsPath && !(directIsPath ?? true)) return true;
  return false;
}

export function showPopup(currentIndex) {
  const list = getActiveList();
  const a = list[currentIndex];
  if (!a) return;

  renderPopupInfo(a);

  requestAnimationFrame(() => {
    renderGraph(a, shouldUseDirectPath(a));
  });

  document.getElementById('popup').style.display = 'flex';
}

function renderGraph(a, useDirectPath) {
  const container = document.getElementById('mynetwork');
  if (!container) return;

  // 🔥 limpiar contenido previo
  container.innerHTML = "";

  const isDark = document.body.classList.contains('dark-mode');

  const { nodes, edges } = buildGraph(
    a,
    generarUUID,
    useDirectPath,
    isDark
  );

  // 🔥 destruir grafo anterior
  if (window.network) {
    window.network.destroy();
    window.network = null;
  }

  if (!nodes.length) {
    container.innerHTML = "<p>No hay datos para mostrar</p>";
    return;
  }

  const data = {
    nodes: new vis.DataSet(nodes),
    edges: new vis.DataSet(edges)
  };

  const options = {
    physics: false,
    nodes: {
      font: {
        color: isDark ? '#e4e6eb' : '#222222',
        size: 14,
        strokeWidth: isDark ? 3 : 2,
        strokeColor: isDark ? '#0f1115' : '#ffffff'
      },
      color: {
        border: isDark ? '#2a2f3a' : '#cccccc',
        highlight: { border: '#84b943', background: isDark ? '#1e2d12' : '#f0f8e0' },
        hover:     { border: '#84b943', background: isDark ? '#1e2d12' : '#f0f8e0' }
      }
    },
    edges: {
      color: {
        color:     isDark ? '#84b943' : '#4a9e22',
        highlight: isDark ? '#b8d96e' : '#2e7d32',
        hover:     isDark ? '#b8d96e' : '#2e7d32'
      },
      width: 2,
      smooth: {
        type: "cubicBezier",
        roundness: 0.5
      }
    }
  };

  window.network = new vis.Network(container, data, options);
  window.network.fit();
}

function renderPopupInfo(a) {
  const container = document.getElementById('popup-body');
  if (!container) return;

  const useDirect = shouldUseDirectPath(a);
  const valor = useDirect
    ? (a.direct_length ?? '')
    : (a.cercania ?? '');

  const directPath = a.directPath;
  const relDesc = (useDirect && directPath)
    ? computeRelationshipDescription(
        directPath.asc.length,
        directPath.desc.length,
        a.name,
        directPath.desc.at(-1)?.gender || ""
      )
    : (a.relationshipDescription || '');

  container.innerHTML = `
    <h3>${a.name}</h3>
    <img src="${a.portraitUrl || 'https://via.placeholder.com/200'}" width="200">
    <p><i>${relDesc}</i></p>
    <p><b>${'Cercanía'}:</b> ${valor}</p>
    <pre>${a.detalle || ''}</pre>
  `;
}

export function closePopup() {
  const popup = document.getElementById('popup');
  if (popup) {
    popup.style.display = 'none';
  }

  // 🔥 limpiar grafo al cerrar
  if (window.network) {
    window.network.destroy();
    window.network = null;
  }
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