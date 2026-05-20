/**
 * M2-5.10.E — Groupe des events par jour pour la timeline Journal (maquette
 * §8.2 day-groups : Aujourd'hui · Hier · Plus tôt).
 *
 * Doctrine : sélection visuelle pure, pas du calcul métier (règle d'or
 * PROMEOS). Les events sont déjà triés `occurred_at DESC` côté backend ;
 * on conserve l'ordre.
 *
 * Returns: array of { dayKey, label, events } — l'UI itère pour rendre
 * un `<DayGroup>` par bucket. `dayKey` est utile pour `key=` React.
 */
export function groupEventsByDay(events, { now = new Date() } = {}) {
  if (!Array.isArray(events) || events.length === 0) return [];

  const today = startOfDay(now);
  const yesterday = new Date(today.getTime() - 86400000);

  const groups = new Map();
  for (const event of events) {
    const dt = event.occurred_at ? new Date(event.occurred_at) : null;
    if (!dt || Number.isNaN(dt.getTime())) continue;
    const day = startOfDay(dt);
    const dayKey = day.toISOString().slice(0, 10);
    if (!groups.has(dayKey)) {
      groups.set(dayKey, {
        dayKey,
        date: day,
        label: labelForDay(day, today, yesterday),
        events: [],
      });
    }
    groups.get(dayKey).events.push(event);
  }
  // Map preserve l'ordre d'insertion (events triés DESC backend → groups DESC).
  return Array.from(groups.values());
}

function startOfDay(d) {
  const out = new Date(d);
  out.setHours(0, 0, 0, 0);
  return out;
}

function labelForDay(day, today, yesterday) {
  const ts = day.getTime();
  if (ts === today.getTime()) return "Aujourd'hui";
  if (ts === yesterday.getTime()) return 'Hier';
  return day.toLocaleDateString('fr-FR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });
}
