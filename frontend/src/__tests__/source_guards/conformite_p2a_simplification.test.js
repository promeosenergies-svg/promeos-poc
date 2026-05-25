/**
 * Source-guards P2-A simplification visuelle Conformité (2026-05-25).
 *
 * Garde-fous cardinaux :
 * 1. Anti-régression fallback "APER" (hotfix #301 déjà couvert ailleurs).
 * 2. Anti-régression hardcode `total_impact_eur: 0` (bug du DAF qui voyait
 *    "0 €" en haut et "45 k€" en bas).
 * 3. ConformitePage rend ConformiteSyntheseCompacte (4 cartes ATF).
 * 4. Frise réglementaire wrappée dans `<details>` (repli par défaut).
 * 5. Briefing éditorial wrappé dans `<details>` (repli par défaut).
 * 6. Aucun texte anglais visible utilisateur (« high-priority items », etc.).
 * 7. Aucun « KB » visible utilisateur dans labels affichés.
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const ROOT = resolve(__dirname, '../../../');
const PAGE = resolve(ROOT, 'src/pages/ConformitePage.jsx');
const SYNTHESE = resolve(ROOT, 'src/components/conformite/ConformiteSyntheseCompacte.jsx');

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

describe('ConformitePage — P2-A simplification visuelle', () => {
  const pageSrc = readFileSync(PAGE, 'utf-8');
  const pageCleaned = stripComments(pageSrc);

  it('rend le composant ConformiteSyntheseCompacte (above-the-fold)', () => {
    expect(pageCleaned).toMatch(/import\s+ConformiteSyntheseCompacte\s+from/);
    expect(pageCleaned).toMatch(/<ConformiteSyntheseCompacte/);
  });

  it('ne hardcode plus `total_impact_eur: 0` (bug pénalité divergente)', () => {
    // Le placeholder historique `total_impact_eur: 0` cassait la confiance
    // du DAF (0 € en haut, 45 k€ en bas dans la frise). On consomme la
    // SoT backend `timeline.total_penalty_exposure_eur`.
    expect(pageCleaned).not.toMatch(/total_impact_eur:\s*0\s*,/);
    // L'empty state (pas de summary) garde null (distinct de 0 — "à qualifier")
    expect(pageCleaned).toMatch(/total_impact_eur:\s*null/);
    // Utilisation effective de timeline.total_penalty_exposure_eur
    expect(pageCleaned).toMatch(/timeline\?\.total_penalty_exposure_eur/);
  });

  it('wrappe la frise réglementaire dans <details> (repli ATF)', () => {
    // La frise est dans un <details> avec un data-testid identifiable.
    expect(pageCleaned).toMatch(/data-testid=["']frise-reglementaire-summary["']/);
    // RegulatoryTimeline est rendu à l'intérieur d'un <details>
    const friseMatch = pageSrc.match(/<details[\s\S]*?<RegulatoryTimeline[\s\S]*?<\/details>/);
    expect(friseMatch).not.toBeNull();
  });

  it('wrappe SolBriefingHead + CrossModuleCTA dans <details> (repli ATF)', () => {
    const briefingMatch = pageSrc.match(/<details[\s\S]*?<SolBriefingHead[\s\S]*?<\/details>/);
    expect(briefingMatch).not.toBeNull();
  });

  it('ne rend plus le RiskBadge dupliqué dans ConformitePage', () => {
    // RiskBadge a été remplacé par la carte 4 de ConformiteSyntheseCompacte.
    // L'import est commenté (rétro-compat éventuelle), JSX retiré.
    expect(pageCleaned).not.toMatch(/<RiskBadge\b/);
  });
});

describe('ConformiteSyntheseCompacte — 4 cartes ATF', () => {
  const src = readFileSync(SYNTHESE, 'utf-8');
  const cleaned = stripComments(src);

  it('rend exactement 4 cartes (Score · Échéance · Actions · Preuves)', () => {
    // Le composant interne <Card testid="..."> propage vers data-testid
    // au rendu DOM. Source-guard : compter les usages `testid="synthese-card-`.
    const cards = cleaned.match(/testid=["']synthese-card-/g) || [];
    expect(cards.length).toBe(4);
    for (const id of ['score', 'echeance', 'actions', 'preuves']) {
      expect(cleaned).toContain(`testid="synthese-card-${id}"`);
    }
  });

  it('rend un libellé périmètre clair (X évalués / Y dans le périmètre)', () => {
    // Template literals : "sites évalué" peut être suffixé par "s" pluriel.
    expect(cleaned).toMatch(/sites?[\s\S]{0,80}évalué/);
    expect(cleaned).toMatch(/dans le périmètre/);
    expect(cleaned).toContain('data-testid="synthese-perimetre"');
  });

  it('affiche un risque financier "à qualifier" si non calculé (pas "0 €")', () => {
    expect(cleaned).toMatch(/à qualifier/);
    expect(cleaned).not.toMatch(/['"]0\s*€['"]/);
  });

  it('expose CTAs uniques par carte (anti-doublon, pas de "Voir plus")', () => {
    expect(cleaned).toContain('data-testid="synthese-cta-actions"');
    expect(cleaned).toContain('data-testid="synthese-cta-preuves"');
    // Les CTAs n'utilisent pas le terme générique "Voir plus" (anti-jargon
    // copywriting Sol §5).
    expect(cleaned).not.toMatch(/>Voir plus</);
  });

  it('utilise un fallback subtitle actionnable si score faible', () => {
    // "Score faible — N actions prioritaires à traiter" (pas anxiogène,
    // dit ce qu'il faut faire). Le subtitle est un template literal avec
    // pluralisation conditionnelle (` prioritaire${actionsCount > 1 ? 's' : ''}`).
    expect(cleaned).toMatch(/Score faible\s*—/);
    expect(cleaned).toMatch(/prioritaire/);
    expect(cleaned).toMatch(/à traiter/);
  });
});

describe('P2-A simplification — anti-jargon & accents', () => {
  const pageSrc = readFileSync(PAGE, 'utf-8');
  const syntheseSrc = readFileSync(SYNTHESE, 'utf-8');

  it('aucun texte anglais visible utilisateur dans la synthèse compacte', () => {
    // Patterns interdits : "high-priority items require action" et autres
    // textes anglais nus dans le JSX rendu.
    expect(syntheseSrc).not.toMatch(/>[^<>]*high-priority items[^<>]*</i);
    expect(syntheseSrc).not.toMatch(/>[^<>]*require action[^<>]*</i);
    expect(syntheseSrc).not.toMatch(/>[^<>]*compliance score[^<>]*</);
  });

  it('aucun « KB » nu dans labels affichés utilisateur (terme interne)', () => {
    // Les labels rendus utilisateur ne doivent pas mentionner "KB" ou
    // "knowledge base" — préférer "Analyse réglementaire automatique".
    // (Les commentaires/code restent libres.)
    const visibleStrings =
      syntheseSrc.match(/(?:title|aria-label|placeholder)=["'][^"']*["']/g) || [];
    for (const s of visibleStrings) {
      expect(s).not.toMatch(/\bKB\b/);
    }
  });

  it("aucun accent manquant sur 'reglementaire' dans le code rendu (UI)", () => {
    // Le texte affiché utilise « réglementaire » (avec accents). Les
    // commentaires/code/keys peuvent rester sans accent.
    const renderedStrings = syntheseSrc.match(/>\s*([A-ZÀ-ÿ][a-zA-Zà-ÿ\s'\-:.()0-9—]*)</g) || [];
    for (const s of renderedStrings) {
      // Détecter "reglementaire" sans é (faux positif si "Règlement" : on
      // cherche uniquement "reglementaire" exact, pas "réglementaire").
      expect(s).not.toMatch(/\breglementaire\b/);
    }
  });
});
