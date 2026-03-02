/**
 * PROMEOS — Schedule validation helpers (pure JS, no JSX)
 * Shared between ScheduleEditor.jsx and tests.
 *
 * Rules:
 *   - Format HH:MM strict
 *   - start < end (no midnight crossing)
 *   - No overlap: prev.end <= next.start (adjacency OK)
 *   - Empty slots = day closed = valid
 */

const HH_MM_RE = /^\d{2}:\d{2}$/;

export function parseHHMM(t) {
  if (!HH_MM_RE.test(t)) return null;
  const h = parseInt(t.slice(0, 2), 10);
  const m = parseInt(t.slice(3), 10);
  if (h > 23 || m > 59) return null;
  return h * 60 + m;
}

/**
 * Validate intervals for one day.
 * Returns array of error strings (empty = valid).
 */
export function validateDay(slots) {
  if (!slots || slots.length === 0) return [];
  const errors = [];
  const parsed = [];

  for (let i = 0; i < slots.length; i++) {
    const { start, end } = slots[i];
    const sMin = parseHHMM(start);
    const eMin = parseHHMM(end);
    if (sMin === null) {
      errors.push(`Plage ${i + 1}: format invalide pour le début`);
      continue;
    }
    if (eMin === null) {
      errors.push(`Plage ${i + 1}: format invalide pour la fin`);
      continue;
    }
    if (sMin >= eMin) {
      errors.push(`Plage ${i + 1}: début (${start}) ≥ fin (${end})`);
      continue;
    }
    parsed.push({ sMin, eMin, idx: i, start, end });
  }

  // Sort and check overlaps
  parsed.sort((a, b) => a.sMin - b.sMin);
  for (let i = 1; i < parsed.length; i++) {
    if (parsed[i].sMin < parsed[i - 1].eMin) {
      errors.push(
        `Chevauchement entre ${parsed[i - 1].start}\u2013${parsed[i - 1].end} et ${parsed[i].start}\u2013${parsed[i].end}`
      );
    }
  }
  return errors;
}
