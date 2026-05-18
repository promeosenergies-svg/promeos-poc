import { EventItem } from './EventItem';

/**
 * M2-5.3.A — Liste chronologique des events d'un item (timeline).
 */
export function EventTimelineList({ events }) {
  return (
    <ol className="space-y-3">
      {events.map((event) => (
        <li key={event.id}>
          <EventItem event={event} />
        </li>
      ))}
    </ol>
  );
}
