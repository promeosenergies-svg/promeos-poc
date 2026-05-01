/**
 * Sprint Refonte Narrative dynamique — Phase 4.bis FE wiring.
 *
 * Tests source-guard (convention projet, cf solEventCard.test.js) :
 * valide que les composants FE consomment correctement les payloads
 * structurés Phase 4.0.B exposés par narrative_generator backend
 * (typology / primary_trigger / secondary_trigger / weekly_deltas /
 * primary_push).
 *
 * Couvre :
 * - Phase 4.bis.A : usePageBriefing expose les nouveaux champs
 * - Phase 4.bis.B : SolWeeklyDeltaBadge — chip up/down sémantique
 * - Phase 4.bis.C : SolNarrative consomme primary_push + primary_trigger
 *
 * Audit Phase 3 P0-3 : « Tout l'investissement Phase 1-3 reste mort
 * côté frontend. » → Phase 4.bis remédie.
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const SRC = join(__dirname, '..');
const readSrc = (rel) => readFileSync(join(SRC, rel), 'utf-8');

// ─── Phase 4.bis.A — usePageBriefing étendu ──────────────────────────────

describe('Phase 4.bis.A — usePageBriefing expose payload Phase 4.0.B', () => {
  const src = readSrc('hooks/usePageBriefing.js');

  it('expose typology depuis le payload backend', () => {
    expect(src).toMatch(/typology:\s*payload\?\.typology/);
  });

  it('expose primaryTrigger (camelCase frontend) depuis primary_trigger backend', () => {
    expect(src).toMatch(/primaryTrigger:\s*payload\?\.primary_trigger/);
  });

  it('expose secondaryTrigger depuis secondary_trigger backend', () => {
    expect(src).toMatch(/secondaryTrigger:\s*payload\?\.secondary_trigger/);
  });

  it('expose weeklyDeltas depuis weekly_deltas backend', () => {
    expect(src).toMatch(/weeklyDeltas:\s*payload\?\.weekly_deltas/);
  });

  it('expose primaryPush depuis primary_push backend', () => {
    expect(src).toMatch(/primaryPush:\s*payload\?\.primary_push/);
  });

  it('défaults safe à null si payload BE non encore wiré', () => {
    // Pour les builders pas encore wirés (cockpit_daily, etc.), tous
    // les champs Phase 4.0.B sont null — pas d'erreur de rendu FE.
    expect(src).toMatch(/typology:\s*payload\?\.typology\s*\|\|\s*null/);
    expect(src).toMatch(/primaryPush:\s*payload\?\.primary_push\s*\|\|\s*null/);
  });
});

// ─── Phase 4.bis.B — SolWeeklyDeltaBadge ────────────────────────────────

describe('Phase 4.bis.B — SolWeeklyDeltaBadge structure', () => {
  it('le fichier existe', () => {
    expect(existsSync(join(SRC, 'ui/sol/SolWeeklyDeltaBadge.jsx'))).toBe(true);
  });

  const src = readSrc('ui/sol/SolWeeklyDeltaBadge.jsx');

  it('exporte un composant React par défaut', () => {
    expect(src).toMatch(/export default function SolWeeklyDeltaBadge/);
  });

  it('importe les 3 icônes Lucide (ArrowUp, ArrowDown, Minus)', () => {
    expect(src).toMatch(/from 'lucide-react'/);
    expect(src).toMatch(/ArrowUp/);
    expect(src).toMatch(/ArrowDown/);
    expect(src).toMatch(/Minus/);
  });

  it('définit METRIC_UP_IS_BAD pour mapping sémantique up/down → tone', () => {
    expect(src).toMatch(/METRIC_UP_IS_BAD/);
    // exposure_eur: up = mauvais (TENSION) — exposition qui monte
    expect(src).toMatch(/exposure_eur:\s*true/);
    // potential_mwh_year: up = bon (CALME) — potentiel qui monte
    expect(src).toMatch(/potential_mwh_year:\s*false/);
  });

  it('détecte la direction depuis la clause backend (Unicode minus)', () => {
    // Backend `format_push_clause` utilise minus Unicode "−" pour négatif
    expect(src).toMatch(/startsWith\('−'\)/);
    expect(src).toMatch(/startsWith\('\+'\)/);
  });

  it('utilise les tokens Sol design system (sol-refuse-fg / sol-calme-fg)', () => {
    expect(src).toMatch(/var\(--sol-refuse-fg\)/);
    expect(src).toMatch(/var\(--sol-calme-fg\)/);
  });

  it('expose data-testid + data-metric + data-direction pour Playwright', () => {
    expect(src).toMatch(/data-testid="sol-weekly-delta-badge"/);
    expect(src).toMatch(/data-metric=/);
    expect(src).toMatch(/data-direction=/);
  });

  it("a un aria-label accessibilité pour lecteur d'écran", () => {
    expect(src).toMatch(/aria-label=/);
    expect(src).toMatch(/role="status"/);
  });

  it('rend rien si primaryPush null (silence éditorial Option 3.C)', () => {
    expect(src).toMatch(/if\s*\(\s*!primaryPush.*?\)\s*return\s+null/);
  });
});

// ─── Phase 4.bis.C — SolNarrative consomme primary_push + drill-down ────

describe('Phase 4.bis.C — SolNarrative wiring Phase 4.0.B', () => {
  const src = readSrc('ui/sol/SolNarrative.jsx');

  it('importe SolWeeklyDeltaBadge', () => {
    expect(src).toMatch(/import\s+SolWeeklyDeltaBadge\s+from\s+'\.\/SolWeeklyDeltaBadge'/);
  });

  it('expose les nouvelles props primaryPush + primaryTrigger', () => {
    expect(src).toMatch(/primaryPush\s*=\s*null/);
    expect(src).toMatch(/primaryTrigger\s*=\s*null/);
  });

  it('rend SolWeeklyDeltaBadge quand primaryPush présent', () => {
    expect(src).toMatch(/<SolWeeklyDeltaBadge\s+primaryPush={primaryPush}/);
  });

  it('définit le mapping TRIGGER_DRILL_DOWN pour les 4 triggers event-driven', () => {
    expect(src).toMatch(/TRIGGER_DRILL_DOWN/);
    expect(src).toMatch(/dt_trajectory_drift/);
    expect(src).toMatch(/major_anomaly/);
    expect(src).toMatch(/audit_deadline_imminent/);
    expect(src).toMatch(/purchase_window_open/);
  });

  it('construit le href drill-down avec linked_site_ids[0] si dispo', () => {
    expect(src).toMatch(/linked_site_ids/);
    expect(src).toMatch(/site_id=/);
  });

  it('expose data-testid sol-narrative-drill-down pour Playwright', () => {
    expect(src).toMatch(/data-testid="sol-narrative-drill-down"/);
  });

  it('expose data-testid sol-narrative-push-row pour Playwright', () => {
    expect(src).toMatch(/data-testid="sol-narrative-push-row"/);
  });

  it('importe ExternalLink de lucide pour icône drill-down', () => {
    expect(src).toMatch(/ExternalLink/);
  });

  it("respecte la règle d'or §8.1 : aucun calcul métier (pas de heuristique €/score)", () => {
    // Vérification approximative : aucune multiplication / addition
    // sur des valeurs métier directement dans le composant.
    expect(src).not.toMatch(/\*\s*1000(?!\s*\))/); // pas de seuil hardcodé
    expect(src).not.toMatch(/0\.05/); // pas de % seuil hardcodé
  });
});

// ─── Phase 8.A — UX patch hiérarchie + a11y daltonisme ─────────────────

describe('Phase 8.A — UX patch hiérarchie italic_hook', () => {
  const src = readSrc('ui/sol/SolNarrative.jsx');

  it('italic_hook rendu hors du <h1> (sous-titre subordonné)', () => {
    // Avant Phase 8.A : `{title} — <em>{italicHook}</em>` dans <h1>
    // Après : `<p data-testid="sol-narrative-italic-hook">` séparé
    expect(src).toMatch(/data-testid="sol-narrative-italic-hook"/);
  });

  it('italic_hook utilise text-sm + italic + ink-500 (sous-titre)', () => {
    expect(src).toMatch(/text-sm font-normal italic text-\[var\(--sol-ink-500\)\]/);
  });

  it("h1 ne contient plus l'em italicHook inline", () => {
    // Le pattern "{title}\n            {italicHook && (" dans <h1> doit avoir disparu
    expect(src).not.toMatch(
      /<h1[^>]*>[^<]*\{title\}[\s\S]*?\{italicHook[\s\S]*?<em>\{italicHook\}/
    );
  });
});

describe('Phase 8.A — a11y daltonisme SolWeeklyDeltaBadge', () => {
  const src = readSrc('ui/sol/SolWeeklyDeltaBadge.jsx');

  it('expose borderStyle distinct par tone (dashed vs solid)', () => {
    expect(src).toMatch(/borderStyle.*?'border-dashed'/s);
    expect(src).toMatch(/borderStyle.*?'border-solid'/s);
  });

  it('expose srLabel sémantique (tension / positif / neutre)', () => {
    expect(src).toMatch(/srLabel.*?'tension'/);
    expect(src).toMatch(/srLabel.*?'positif'/);
    expect(src).toMatch(/srLabel.*?'neutre'/);
  });

  it('rend un span sr-only avec le srLabel', () => {
    expect(src).toMatch(/sr-only/);
  });

  it('aria-label inclut le tone sémantique avant le clause', () => {
    expect(src).toMatch(/aria-label=.*?Signal \$\{styles\.srLabel\}/);
  });
});

// ─── Cohérence cross-stack BE ↔ FE ──────────────────────────────────────

describe('Cohérence BE ↔ FE Phase 4.bis', () => {
  it('les 4 triggers FE TRIGGER_DRILL_DOWN matchent les TriggerType BE event-driven', () => {
    const src = readSrc('ui/sol/SolNarrative.jsx');
    // BE event-driven triggers (cf doctrine/triggers.py + sentence_composer.py
    // TRIGGER_TO_COMPOSER) :
    const beTriggers = [
      'dt_trajectory_drift',
      'major_anomaly',
      'audit_deadline_imminent',
      'purchase_window_open',
    ];
    for (const t of beTriggers) {
      expect(src).toMatch(new RegExp(t));
    }
  });

  it('le mapping METRIC_UP_IS_BAD couvre les 4 métriques weekly_deltas BE canoniques', () => {
    const src = readSrc('ui/sol/SolWeeklyDeltaBadge.jsx');
    const beMetrics = ['exposure_eur', 'sites_in_drift', 'potential_mwh_year', 'compliance_score'];
    for (const m of beMetrics) {
      expect(src).toMatch(new RegExp(m));
    }
  });
});
