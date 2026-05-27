function ancestorTerm(n, female) {
  const s = female ? "a" : "o";
  if (n === 1) return female ? "madre" : "padre";
  if (n === 2) return `abuel${s}`;
  if (n === 3) return `bisabuel${s}`;
  if (n === 4) return `tatarabuel${s}`;
  const degree = n - 3;
  return `${degree}° tatarabuel${s}`;
}

function descendantTerm(n, female) {
  const s = female ? "a" : "o";
  if (n === 1) return female ? "hija" : "hijo";
  if (n === 2) return `niet${s}`;
  if (n === 3) return `bisniet${s}`;
  if (n === 4) return `tataranieto${female ? "a" : ""}`;
  const degree = n - 3;
  return `${degree}° tataranieto${female ? "a" : ""}`;
}

const ORDINALS_MALE   = ["", "", "segundo", "tercero", "cuarto", "quinto", "sexto", "séptimo", "octavo", "noveno", "décimo"];
const ORDINALS_FEMALE = ["", "", "segunda", "tercera", "cuarta", "quinta", "sexta", "séptima", "octava", "novena", "décima"];

function ordinal(n, female) {
  const list = female ? ORDINALS_FEMALE : ORDINALS_MALE;
  return n < list.length ? list[n] : `${n}°`;
}

export function computeRelationshipDescription(ascLen, descLen, personName, gender) {
  const female = gender?.toUpperCase() === "FEMALE";

  let rel;

  if (ascLen === 0 && descLen === 0) {
    return personName;
  }

  if (descLen === 0) {
    rel = ancestorTerm(ascLen, female);
  } else if (ascLen === 0) {
    rel = descendantTerm(descLen, female);
  } else {
    const minSide = Math.min(ascLen, descLen);
    const removed = Math.abs(ascLen - descLen);

    if (minSide === 1) {
      if (removed === 0) {
        rel = female ? "hermana" : "hermano";
      } else if (ascLen < descLen) {
        const base = female ? "sobrina" : "sobrino";
        if (descLen === 2) {
          rel = base;
        } else {
          rel = `${base} ${descendantTerm(descLen - 1, female)}`;
        }
      } else {
        const base = female ? "tía" : "tío";
        if (ascLen === 2) {
          rel = base;
        } else {
          rel = `${base} ${ancestorTerm(ascLen - 1, female)}`;
        }
      }
    } else {
      const degree = minSide - 1;
      const base = female ? "prima" : "primo";
      const degStr = degree >= 2 ? ` ${ordinal(degree, female)}` : "";
      const remStr = removed > 0
        ? ` ${removed} ${removed === 1 ? "vez" : "veces"} removido${female ? "a" : ""}`
        : "";
      rel = `${base}${degStr}${remStr}`;
    }
  }

  return `${personName} es tu ${rel}`;
}
