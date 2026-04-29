/**
 * solTones.js — Dictionnaire unifié tons sémantiques Sol (Étape 2.bis · 29/04/2026).
 *
 * Centralise les mappings urgency/severity vers tokens Sol. Évite la
 * duplication signalée par /simplify P1 audit fin Étape 2 :
 *   - CockpitPilotage:URGENCY_TONE
 *   - CockpitDecision:SEVERITY_TO_TONE
 * Les deux dictionnaires partageaient les mêmes clés (critical/high/medium/low)
 * et les mêmes variables CSS — toute évolution d'un token devait être
 * propagée manuellement aux deux fichiers.
 *
 * Convention :
 *   - bg     : background-color (token Sol bg)
 *   - line   : border-color (token Sol line, semi-opaque)
 *   - fg     : text/icon color (token Sol fg)
 *   - chipBg : background pour chip "P1/P2..." inscrit dans la card
 *   - label  : libellé court FR pour chip de criticité
 */

const ATTENTION_BASE = {
  bg: 'var(--sol-attention-bg)',
  line: 'var(--sol-attention-line)',
  fg: 'var(--sol-attention-fg)',
  chipBg: 'rgba(0,0,0,0.06)',
};

export const SOL_SEVERITY_TONES = Object.freeze({
  critical: {
    bg: 'var(--sol-refuse-bg)',
    line: 'var(--sol-refuse-line)',
    fg: 'var(--sol-refuse-fg)',
    chipBg: 'rgba(0,0,0,0.06)',
    label: 'Critique',
  },
  high: { ...ATTENTION_BASE, label: 'Important' },
  medium: { ...ATTENTION_BASE, label: 'À surveiller' },
  low: {
    bg: 'var(--sol-bg-canvas)',
    line: 'var(--sol-rule)',
    fg: 'var(--sol-ink-700)',
    chipBg: 'rgba(0,0,0,0.04)',
    label: 'Information',
  },
  neutral: {
    bg: 'var(--sol-bg-canvas)',
    line: 'var(--sol-rule)',
    fg: 'var(--sol-ink-700)',
    chipBg: 'rgba(0,0,0,0.04)',
    label: '',
  },
});

/** Lookup helper qui retourne 'medium' tone par défaut si clé inconnue. */
export const severityTone = (key) => SOL_SEVERITY_TONES[key] || SOL_SEVERITY_TONES.medium;

/** Tons confiance pour badges Calculé/Modélisé (page Décision). */
export const SOL_CONFIDENCE_TONES = Object.freeze({
  calculated_regulatory: {
    bg: 'var(--sol-succes-bg)',
    fg: 'var(--sol-succes-fg)',
    label: 'Calculé',
  },
  calculated_contractual: {
    bg: 'var(--sol-succes-bg)',
    fg: 'var(--sol-succes-fg)',
    label: 'Calculé',
  },
  modeled_cee: {
    bg: 'var(--sol-attention-bg)',
    fg: 'var(--sol-attention-fg)',
    label: 'Modélisé',
  },
  modeled: {
    bg: 'var(--sol-attention-bg)',
    fg: 'var(--sol-attention-fg)',
    label: 'Modélisé',
  },
  indicative: {
    bg: 'var(--sol-hce-bg)',
    fg: 'var(--sol-hce-fg)',
    label: 'Indicatif',
  },
});

export const confidenceTone = (key) =>
  SOL_CONFIDENCE_TONES[key] || SOL_CONFIDENCE_TONES.calculated_regulatory;
