/**
 * SolBriefingFooter — HOC SolPageFooter alimenté par briefing.provenance.
 *
 * Sprint 2 Vague B ét8' (27/04/2026). Factorise les ~6 lignes JSX
 * dupliquées dans 10 pages PROMEOS pour rendre la footer Source · Confiance ·
 * Mis à jour à partir du `briefing.provenance` retourné par usePageBriefing.
 *
 * Pattern factorisé :
 *   {briefing?.provenance && (
 *     <SolPageFooter
 *       source={briefing.provenance.source}
 *       confidence={briefing.provenance.confidence}
 *       updatedAt={briefing.provenance.updated_at}
 *       methodologyUrl={briefing.provenance.methodology_url}
 *     />
 *   )}
 *
 * Composant stateless. Render `null` proprement si pas de provenance.
 *
 * Props :
 *   - briefing : objet retourné par usePageBriefing (lit `provenance`)
 *
 * Doctrine §5 footer + règle d'or chiffres (memory feedback 27/04) :
 * la provenance est la garantie auditeur "ce chiffre est vérifiable".
 */
import SolPageFooter from './SolPageFooter';

export default function SolBriefingFooter({ briefing }) {
  if (!briefing?.provenance) return null;
  const p = briefing.provenance;
  return (
    <SolPageFooter
      source={p.source}
      confidence={p.confidence}
      updatedAt={p.updated_at}
      methodologyUrl={p.methodology_url}
    />
  );
}
