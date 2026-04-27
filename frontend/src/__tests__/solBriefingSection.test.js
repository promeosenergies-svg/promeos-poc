/**
 * Sprint 2 Vague B ét8' — SolBriefingHead/Footer HOC.
 *
 * Tests source-guard (convention projet) : factorisation grammaire §5
 * vers 2 composants stateless réutilisables. Vérifie que les 3 pages
 * pilotes (BillIntelPage / MonitoringPage / AnomaliesPage) consomment bien
 * le HOC à la place du pattern dupliqué.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ── A. SolBriefingHead — composant ──────────────────────────────────

describe('A. SolBriefingHead — structure', () => {
  it('le fichier existe au bon emplacement', () => {
    expect(existsSync(join(SRC, 'ui/sol/SolBriefingHead.jsx'))).toBe(true);
  });

  const src = readSrc('ui/sol/SolBriefingHead.jsx');

  it('exporte un composant React par défaut', () => {
    expect(src).toMatch(/export default function SolBriefingHead/);
  });

  it('importe SolNarrative + SolWeekCards (pas SolPageFooter)', () => {
    expect(src).toMatch(/import SolNarrative from '\.\/SolNarrative'/);
    expect(src).toMatch(/import SolWeekCards from '\.\/SolWeekCards'/);
    expect(src).not.toMatch(/import SolPageFooter/);
  });

  it('accepte les props briefing / error / onRetry / omitHeader / onNavigate', () => {
    expect(src).toMatch(/briefing/);
    expect(src).toMatch(/error\s*=\s*null/);
    expect(src).toMatch(/onRetry\s*=\s*null/);
    expect(src).toMatch(/omitHeader\s*=\s*false/);
    expect(src).toMatch(/onNavigate/);
  });

  it('rend null si briefing absent (early return)', () => {
    expect(src).toMatch(/if \(!briefing\) return null/);
  });

  it('rend SolNarrative error state si error && !briefing', () => {
    expect(src).toMatch(/error && !briefing/);
    // Assertions atomiques (robustes au réordre attributs par prettier)
    expect(src).toMatch(/<SolNarrative error=\{error\}/);
    expect(src).toMatch(/onRetry=\{onRetry\}/);
  });

  it('passe omitHeader pour neutraliser kicker/title/italicHook si demandé', () => {
    expect(src).toMatch(/omitHeader \? null : briefing\.kicker/);
    expect(src).toMatch(/omitHeader \? null : briefing\.title/);
    expect(src).toMatch(/omitHeader \? null : briefing\.italicHook/);
  });

  it('passe les props week-cards complètes (cards/fallbackBody/tone/onNavigate)', () => {
    expect(src).toMatch(/cards=\{briefing\.weekCards\}/);
    expect(src).toMatch(/fallbackBody=\{briefing\.fallbackBody\}/);
    expect(src).toMatch(/tone=\{briefing\.narrativeTone\}/);
    expect(src).toMatch(/onNavigate=\{onNavigate\}/);
  });
});

// ── B. SolBriefingFooter — composant ───────────────────────────────

describe('B. SolBriefingFooter — structure', () => {
  it('le fichier existe au bon emplacement', () => {
    expect(existsSync(join(SRC, 'ui/sol/SolBriefingFooter.jsx'))).toBe(true);
  });

  const src = readSrc('ui/sol/SolBriefingFooter.jsx');

  it('exporte un composant React par défaut', () => {
    expect(src).toMatch(/export default function SolBriefingFooter/);
  });

  it('importe SolPageFooter (et lui seul)', () => {
    expect(src).toMatch(/import SolPageFooter from '\.\/SolPageFooter'/);
    expect(src).not.toMatch(/import SolNarrative/);
    expect(src).not.toMatch(/import SolWeekCards/);
  });

  it('rend null si briefing.provenance absent (early return)', () => {
    expect(src).toMatch(/if \(!briefing\?\.provenance\) return null/);
  });

  it('mappe provenance → SolPageFooter (source/confidence/updatedAt/methodologyUrl)', () => {
    expect(src).toMatch(/source=\{p\.source\}/);
    expect(src).toMatch(/confidence=\{p\.confidence\}/);
    expect(src).toMatch(/updatedAt=\{p\.updated_at\}/);
    expect(src).toMatch(/methodologyUrl=\{p\.methodology_url\}/);
  });
});

// ── C. Migrations pages-pilotes (3 pages) ──────────────────────────

describe('C. Migration BillIntelPage', () => {
  const src = readSrc('pages/BillIntelPage.jsx');

  it('importe SolBriefingHead + SolBriefingFooter', () => {
    expect(src).toMatch(/import SolBriefingHead from '\.\.\/ui\/sol\/SolBriefingHead'/);
    expect(src).toMatch(/import SolBriefingFooter from '\.\.\/ui\/sol\/SolBriefingFooter'/);
  });

  it('ne rend plus directement <SolNarrative narrative=...> (factorisé via HOC)', () => {
    // Le pattern dupliqué original `narrative={solBriefing.narrative}`
    // dans le JSX rendu (pas un import) doit avoir disparu.
    expect(src).not.toMatch(/narrative=\{solBriefing\.narrative\}/);
  });

  it('ne rend plus directement <SolWeekCards cards=...> (factorisé via HOC)', () => {
    expect(src).not.toMatch(/cards=\{solBriefing\.weekCards\}/);
  });

  it('ne rend plus directement <SolPageFooter source=...> (factorisé via HOC)', () => {
    expect(src).not.toMatch(/source=\{solBriefing\.provenance\.source\}/);
  });

  it('rend <SolBriefingHead> avec omitHeader (kicker/title via PageShell)', () => {
    expect(src).toMatch(/<SolBriefingHead/);
    expect(src).toMatch(/omitHeader/);
  });

  it('rend <SolBriefingFooter briefing={solBriefing}>', () => {
    expect(src).toMatch(/<SolBriefingFooter briefing=\{solBriefing\}/);
  });
});

describe('D. Migration MonitoringPage', () => {
  const src = readSrc('pages/MonitoringPage.jsx');

  it('importe SolBriefingHead + SolBriefingFooter', () => {
    expect(src).toMatch(/import SolBriefingHead/);
    expect(src).toMatch(/import SolBriefingFooter/);
  });

  it('rend <SolBriefingHead> et <SolBriefingFooter>', () => {
    expect(src).toMatch(/<SolBriefingHead/);
    expect(src).toMatch(/<SolBriefingFooter/);
  });

  it('le pattern dupliqué a disparu (3 sites)', () => {
    expect(src).not.toMatch(/cards=\{solBriefing\.weekCards\}/);
    expect(src).not.toMatch(/source=\{solBriefing\.provenance\.source\}/);
  });
});

describe('E. Migration AnomaliesPage', () => {
  const src = readSrc('pages/AnomaliesPage.jsx');

  it('importe SolBriefingHead + SolBriefingFooter', () => {
    expect(src).toMatch(/import SolBriefingHead/);
    expect(src).toMatch(/import SolBriefingFooter/);
  });

  it('rend <SolBriefingHead> et <SolBriefingFooter>', () => {
    expect(src).toMatch(/<SolBriefingHead/);
    expect(src).toMatch(/<SolBriefingFooter/);
  });

  it('le pattern dupliqué a disparu (3 sites)', () => {
    expect(src).not.toMatch(/cards=\{solBriefing\.weekCards\}/);
    expect(src).not.toMatch(/source=\{solBriefing\.provenance\.source\}/);
  });
});

// ── F. Doctrine §8.1 — composants stateless ─────────────────────────

describe('F. Doctrine §8.1 — pureté display', () => {
  it("SolBriefingHead n'utilise aucun useState/useEffect/useMemo (stateless)", () => {
    const src = readSrc('ui/sol/SolBriefingHead.jsx');
    expect(src).not.toMatch(/useState|useEffect|useMemo/);
  });

  it("SolBriefingFooter n'utilise aucun useState/useEffect/useMemo (stateless)", () => {
    const src = readSrc('ui/sol/SolBriefingFooter.jsx');
    expect(src).not.toMatch(/useState|useEffect|useMemo/);
  });

  /**
   * Le HOC ne doit ni IMPORTER ni APPELER `usePageBriefing` — le hook
   * reste invoqué au niveau page (1 fetch / pas de doublon). On vérifie
   * en cherchant la ligne `import { usePageBriefing }` ou `import ...
   * from '../hooks/usePageBriefing'`. Les mentions en JSDoc (commentaires)
   * sont permises et utiles pour expliquer le contrat aux mainteneurs.
   */
  it("SolBriefingHead n'importe pas usePageBriefing", () => {
    const src = readSrc('ui/sol/SolBriefingHead.jsx');
    expect(src).not.toMatch(/^import .*usePageBriefing/m);
  });

  it("SolBriefingFooter n'importe pas usePageBriefing", () => {
    const src = readSrc('ui/sol/SolBriefingFooter.jsx');
    expect(src).not.toMatch(/^import .*usePageBriefing/m);
  });
});
