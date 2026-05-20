import { EventItem } from './EventItem';

/**
 * M2-5.3.A / M2-5.10.B — Liste chronologique audit-list Sol (maquette §8.4
 * lignes 615-617). Ligne verticale absolute à gauche + dots colorés par
 * `EventItem` alignés sur celle-ci. La 1ère entrée porte un dot pleine
 * couleur (signature du « now » dans la timeline éditoriale).
 */
export function EventTimelineList({ events }) {
  return (
    <ol
      className="relative flex flex-col pl-3.5"
      style={
        {
          // Ligne verticale Sol — wrappée en pseudo-élément via inline style
          // box-shadow plutôt que CSS pseudo (compatible inline React).
        }
      }
    >
      <span
        aria-hidden="true"
        className="absolute top-1 bottom-1 w-px"
        style={{ left: '0px', background: 'var(--sol-rule)' }}
      />
      {events.map((event, i) => (
        <li key={event.id}>
          <EventItem event={event} isFirst={i === 0} />
        </li>
      ))}
    </ol>
  );
}
