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

  const useDirect =
    directPath &&
    a.coParentIsTargetPerson === true &&
    a.directPath != null;

  if (directPath && !useDirect && a.coParentIsTargetPerson === true) {
    return { nodes: [], edges: [] };
  }

  const path = useDirect ? a.directPath : (a.mainPath || {});
  const rootId = path.antepasado_comun?.id || generarUUID();

  nodes.push({
    id: rootId,
    shape: "image",
    image: path.antepasado_comun?.portraitUrl || getDefaultIcon(path.antepasado_comun?.gender),
    font: { size: 16 },
    x: 0,
    y: 0,
    fixed: true,
    label: path.antepasado_comun?.nombre || ""
  });

  // ======================
  // ASC (izquierda)
  // ======================
  const asc = path.asc || [];
  asc.forEach((p, i) => {
    const id = p.id || generarUUID();
    p._id = id;

    const block_number = Math.floor(i / BLOCK_SIZE);
    const direction = block_number % 2 === 0 ? -1 : 1;
    const possition = direction==-1 ? i % BLOCK_SIZE : BLOCK_SIZE - i % BLOCK_SIZE;

    const y = -(2 + 0.25*possition + block_number)*GAP_Y;
    const x = -(possition + 1)*GAP_X;

    nodes.push({
      id,
      shape: "image",
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
      to: i === 0 ? rootId : asc[i - 1]._id
    });
  });

  // ======================
  // DESC (derecha)
  // ======================
  const desc = path.desc || [];
  desc.forEach((p, i) => {
    const id = p.id || generarUUID();
    p._id = id;

    const block_number = Math.floor(i / BLOCK_SIZE);
    const direction = block_number % 2 === 0 ? 1 : -1;
    const possition = direction==1 ? i % BLOCK_SIZE : BLOCK_SIZE - i % BLOCK_SIZE;

    const y = +(2 + 0.25*possition + block_number)*GAP_Y;
    const x = +(possition + 1)*GAP_X;

    nodes.push({
      id,
      shape: "image",
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
      to: id
    });
  });

  return { nodes, edges };
}