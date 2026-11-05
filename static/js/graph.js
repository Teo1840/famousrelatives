const ICON_MALE   = "https://upload.wikimedia.org/wikipedia/commons/1/12/User_icon_2.svg";
const ICON_FEMALE = "https://upload.wikimedia.org/wikipedia/commons/6/6c/User_icon_3.svg";

function getDefaultIcon(gender) {
  return gender === "FEMALE" ? ICON_FEMALE : ICON_MALE;
}

export function buildGraph(a, generarUUID, directPath, isDark = false) {
  const nodes = [];
  const edges = [];

  const BLOCK_SIZE = 4;
  const GAP_X = 250;
  const GAP_Y = 150;

  const useDirect = directPath && a.directPath != null;

  const path = useDirect ? a.directPath : (a.mainPath || {});
  const rootId = path.antepasado_comun?.id || generarUUID();

  nodes.push({
    id: rootId,
    fsId: path.antepasado_comun?.id,
    shape: "image",
    image: path.antepasado_comun?.portraitUrl || getDefaultIcon(path.antepasado_comun?.gender),
    brokenImage: getDefaultIcon(path.antepasado_comun?.gender),
    font: { size: 16 },
    x: 0,
    y: 0,
    fixed: true,
    label: path.antepasado_comun?.nombre || ""
  });

  // Los dos lados bajan desde el antepasado común (arriba, al centro):
  // ASC a la izquierda termina en mí, DESC a la derecha en la persona famosa.
  // Cada lado avanza en filas de BLOCK_SIZE nodos haciendo zigzag hacia abajo.
  const FIRST_ROW = 1;
  const STEP_DROP = 0.25;                                // bajada por paso dentro de una fila
  const ROW_HEIGHT = (BLOCK_SIZE - 1) * STEP_DROP + 1;   // al doblar baja un GAP_Y completo

  // Posición del nodo i de un lado (side = -1 izquierda, +1 derecha).
  // Fila r: va hacia afuera si r es par y vuelve hacia el centro si es impar;
  // dentro de la fila cada paso baja un poco, así el camino siempre desciende.
  function snakePos(i, side) {
    const row = Math.floor(i / BLOCK_SIZE);
    const step = i % BLOCK_SIZE;
    const col = row % 2 === 0 ? step : BLOCK_SIZE - 1 - step;
    return {
      x: side * (col + 1) * GAP_X,
      y: (FIRST_ROW + row * ROW_HEIGHT + STEP_DROP * step) * GAP_Y
    };
  }

  // Unión curva donde la serpiente cambia de dirección (nodo i empieza fila nueva).
  // El arco se abre hacia afuera: en el borde exterior si la fila anterior iba
  // hacia afuera, y hacia el centro si volvía.
  // vis-network: en una arista que baja, curvedCW se abre a la derecha y
  // curvedCCW a la izquierda; en una que sube es al revés.
  function turnSmooth(i, side, edgeGoesDown) {
    if (i === 0 || i % BLOCK_SIZE !== 0) return undefined;
    const prevRow = Math.floor((i - 1) / BLOCK_SIZE);
    const bulge = prevRow % 2 === 0 ? side : -side; // -1 izquierda, +1 derecha
    const cwBulge = edgeGoesDown ? 1 : -1;
    return { enabled: true, type: bulge === cwBulge ? "curvedCW" : "curvedCCW", roundness: 0.6 };
  }

  // Uniones por matrimonio (parentesco político) → línea punteada.
  // Los árboles nuevos marcan el nodo con "conyuge" (su unión con el anterior es
  // un matrimonio). Los guardados antes no lo tienen: si la persona famosa es
  // cónyuge de mi pariente, el matrimonio es la última unión del camino principal.
  const asc0 = path.asc || [];
  const desc0 = path.desc || [];
  const hasSpouseFlags = [...asc0, ...desc0].some(p => p.conyuge);
  const legacyTargetSpouse = !hasSpouseFlags && !useDirect && a.coParentIsTargetPerson && desc0.length > 0;
  const isSpouseLink = (list, i) =>
    !!list[i]?.conyuge || (legacyTargetSpouse && list === desc0 && i === desc0.length - 1);

  // ======================
  // ASC (izquierda)
  // ======================
  const asc = asc0;
  asc.forEach((p, i) => {
    const id = p.id || generarUUID();
    p._id = id;

    const { x, y } = snakePos(i, -1);

    nodes.push({
      id,
      fsId: p.id,
      shape: "image",
      brokenImage: getDefaultIcon(p.gender),
      image:
        p.portraitUrl || getDefaultIcon(p.gender),
      font: { size: 16 },
      x: x,
      y: y,
      fixed: true,
      label: p.nombre
    });

    edges.push({
      from: id,
      to: i === 0 ? rootId : asc[i - 1]._id,
      smooth: turnSmooth(i, -1, false), // arista de abajo hacia arriba
      dashes: isSpouseLink(asc, i)
    });
  });

  // ======================
  // DESC (derecha)
  // ======================
  const desc = desc0;
  desc.forEach((p, i) => {
    const id = p.id || generarUUID();
    p._id = id;

    const { x, y } = snakePos(i, +1);

    nodes.push({
      id,
      fsId: p.id,
      shape: "image",
      brokenImage: getDefaultIcon(p.gender),
      image:
        p.portraitUrl || getDefaultIcon(p.gender),
      font: { size: 16 },
      x: x,
      y: y,
      fixed: true,
      label: p.nombre
    });

    edges.push({
      from: i === 0 ? rootId : desc[i - 1]._id,
      to: id,
      smooth: turnSmooth(i, +1, true), // arista de arriba hacia abajo
      dashes: isSpouseLink(desc, i)
    });
  });

  return { nodes, edges };
}