/**
 * SolBriefingHead — HOC grammaire éditoriale Sol §5 (head + week-cards).
 *
 * Sprint 2 Vague B ét8' (27/04/2026). Factorise les ~15 lignes JSX
 * répétées à l'identique dans les 10 pages PROMEOS qui consomment
 * `usePageBriefing` :
 *
 *   {error && !briefing && <SolNarrative error={...} onRetry={...} />}
 *   {briefing && <SolNarrative narrative={...} kpis={...} ... />}
 *   {briefing && <SolWeekCards cards={...} fallbackBody={...} ... />}
 *
 * Composant stateless (props-driven) : le hook `usePageBriefing` reste
 * appelé UNE SEULE FOIS au niveau page (pas de doublon réseau). Le caller
 * passe `briefing` + `error` + `onRetry` reçus du hook.
 *
 * Props :
 *   - briefing  : objet retourné par usePageBriefing (kicker/title/narrative/
 *                 kpis/weekCards/events/fallbackBody/narrativeTone)
 *   - error     : string|null — passé à SolNarrative pour error state
 *   - onRetry   : function|null — invoke fetchBriefing pour retry
 *   - omitHeader: bool — true si SolPageHeader est rendu ailleurs
 *                 (PageShell.editorialHeader). Défaut : false.
 *   - onNavigate: function — handler navigation pour week-cards CTA.
 *   - useEventStream : bool — Sprint 2 Vague C ét12d (audit Marie + UX P0-B).
 *                 Si true ET briefing.events présents, on rend
 *                 <SolEventStream> (pile §10 native source/confidence/
 *                 owner_role/mitigation visibles) au lieu de <SolWeekCards>.
 *                 Évite le doublon sémantique 6 cards typologiquement
 *                 proches sur Cockpit. Défaut : false (rétro-compat).
 *   - eventStreamTitle : surtitre §5 du SolEventStream si activé.
 *
 * Doctrine §5 + ADR-001 — invariant grammaire éditoriale.
 * Doctrine §8.1 — zéro logique métier (composant pur display).
 */
import SolNarrative from './SolNarrative';
import SolWeekCards from './SolWeekCards';
import { SolEventStream } from './SolEventCard';

export default function SolBriefingHead({
  briefing,
  error = null,
  onRetry = null,
  omitHeader = false,
  onNavigate,
  useEventStream = false,
  eventStreamTitle = 'Cette semaine chez vous',
}) {
  // Erreur briefing : SolNarrative s'occupe de l'affichage error state
  // (memory feedback CX 27/04 : ne pas masquer silencieusement).
  if (error && !briefing) {
    return <SolNarrative error={error} onRetry={onRetry} />;
  }
  if (!briefing) return null;

  // Vague C ét12d : si la page-pilote a opt-in pour la pile §10 native ET
  // que le moteur d'événements a poussé au moins un événement, on bascule
  // vers SolEventStream. Sinon fallback SolWeekCards (pages legacy +
  // cockpit dont events.length===0).
  const hasEvents = briefing.events && briefing.events.length > 0;
  const showEventStream = useEventStream && hasEvents;

  return (
    <>
      <SolNarrative
        kicker={omitHeader ? null : briefing.kicker}
        title={omitHeader ? null : briefing.title}
        italicHook={omitHeader ? null : briefing.italicHook}
        narrative={briefing.narrative}
        kpis={briefing.kpis}
      />
      {showEventStream ? (
        <SolEventStream
          events={briefing.events}
          max={3}
          onNavigate={onNavigate}
          title={eventStreamTitle}
        />
      ) : (
        <SolWeekCards
          cards={briefing.weekCards}
          fallbackBody={briefing.fallbackBody}
          tone={briefing.narrativeTone}
          onNavigate={onNavigate}
        />
      )}
    </>
  );
}
