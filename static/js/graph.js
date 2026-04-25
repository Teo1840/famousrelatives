export function buildGraph(a, generarUUID) {
  const nodes = [];
  const edges = [];

  const BLOCK_SIZE = 4;
  const GAP_X = 250;
  const GAP_Y = 150;

  const rootId = a.antepasado_comun?.id || generarUUID();
  const useDirect =
    a.coParentIsTargetPerson === true &&
    a.directPath != null;

  const path = useDirect
    ? a.directPath
    : (a.mainPath || {});

    nodes.push({
    id: rootId,
    shape: "image",
    image:
      a.antepasado_comun?.portraitUrl ||
      "https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png",
    font: { size: 16 },
    x: 0,
    y: 0,
    fixed: true,
    label: a.antepasado_comun?.nombre || ""
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
        p.portraitUrl ||
        "https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png",
      font: { size: 16 },
      x: x,
      y: y,
      fixed: true,
      label: p.nombre
    });

    edges.push({
      from: id,
      to: i === 0 ? rootId : asc[i - 1]._id,
      color: {color: 'green'}
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
        p.portraitUrl ||
        "https://upload.wikimedia.org/wikipedia/commons/9/99/Sample_User_Icon.png",
      font: { size: 16 },
      x: x,
      y: y,
      fixed: true,
      label: p.nombre
    });

    edges.push({
      from: i === 0 ? rootId : desc[i - 1]._id,
      to: id,
      color: {color: 'green'}
    });
  });

  return { nodes, edges };
}