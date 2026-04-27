/**
 * Sprint 2 Vague B ét6' — label_registries cross-vue.
 *
 * Tests des 2 registres FR centralisés (billing + monitoring) qui
 * remplacent la duplication de wording entre BillIntelPage / InsightDrawer
 * (Vague A ét2) et MonitoringPage (Vague A ét5').
 *
 * Garanties :
 *  1. Couverture des codes types backend (parité avec les codes émis par
 *     le moteur d'audit billing + alert engine monitoring).
 *  2. Aucun acronyme brut hors `<Explain>` dans le texte canonique.
 *  3. Immutabilité (Object.freeze) — empêche la mutation accidentelle d'un
 *     consommateur (BillIntelPage vs InsightDrawer divergeraient).
 *  4. Helper fallback retourne le code brut si type inconnu.
 */

import { describe, it, expect } from 'vitest';
import {
  BILLING_INSIGHT_TYPE_LABELS,
  BILLING_INSIGHT_STATUS_LABELS,
  BILLING_INVOICE_STATUS_LABELS,
  BILLING_SEVERITY_LABELS,
  BILLING_SEVERITY_BADGE,
  billingInsightLabel,
} from '../domain/billing/billingLabels.fr';
import {
  MONITORING_ALERT_TYPE_LABELS,
  MONITORING_KPI_TOOLTIPS,
  monitoringAlertLabel,
} from '../domain/monitoring/monitoringLabels.fr';

// ── Billing registry ────────────────────────────────────────────────

describe('BILLING_INSIGHT_TYPE_LABELS', () => {
  // Liste canonique des codes émis par le moteur shadow billing v4.2.
  // Source : `frontend/src/pages/BillIntelPage.jsx` ét2 commit 1245049d.
  const REQUIRED_CODES = [
    'shadow_gap',
    'unit_price_high',
    'duplicate_invoice',
    'missing_period',
    'period_too_long',
    'negative_kwh',
    'zero_amount',
    'lines_sum_mismatch',
    'consumption_spike',
    'price_drift',
    'ttc_coherence',
    'contract_expiry',
    'reseau_mismatch',
    'taxes_mismatch',
    'reconciliation_mismatch',
  ];

  it.each(REQUIRED_CODES)('expose la phrase narrative pour %s', (code) => {
    expect(BILLING_INSIGHT_TYPE_LABELS[code]).toBeDefined();
    expect(typeof BILLING_INSIGHT_TYPE_LABELS[code]).toBe('string');
    expect(BILLING_INSIGHT_TYPE_LABELS[code].length).toBeGreaterThan(15);
  });

  it("aucun label ne contient d'acronyme brut hors marqueur explicite", () => {
    // §6.3 anti-pattern : TURPE/TTC/CTA/accise restent visibles côté texte
    // canonique (ils sont encapsulés `<Explain>` côté JSX). Le test vérifie
    // qu'aucun acronyme NON listé ne fuite (NEBCO, OPERAT, BACS, APER).
    const FORBIDDEN = ['NEBCO', 'OPERAT', 'BACS', 'APER', 'ARENH', 'VNU'];
    for (const label of Object.values(BILLING_INSIGHT_TYPE_LABELS)) {
      for (const acronym of FORBIDDEN) {
        expect(label).not.toContain(acronym);
      }
    }
  });

  it('est figé (Object.freeze) pour empêcher la mutation cross-consommateur', () => {
    expect(Object.isFrozen(BILLING_INSIGHT_TYPE_LABELS)).toBe(true);
  });
});

describe('BILLING_INSIGHT_STATUS_LABELS', () => {
  it('couvre les 4 statuts workflow open/ack/resolved/false_positive', () => {
    expect(Object.keys(BILLING_INSIGHT_STATUS_LABELS).sort()).toEqual([
      'ack',
      'false_positive',
      'open',
      'resolved',
    ]);
  });

  it('utilise les libellés non-sachant ("Pris en charge" pas "En cours")', () => {
    expect(BILLING_INSIGHT_STATUS_LABELS.ack).toBe('Pris en charge');
    expect(BILLING_INSIGHT_STATUS_LABELS.false_positive).toBe('Faux positif');
  });
});

describe("BILLING_SEVERITY_LABELS / BADGE — déduplication ét6'", () => {
  it('couvre les 4 niveaux critical/high/medium/low', () => {
    expect(Object.keys(BILLING_SEVERITY_LABELS).sort()).toEqual([
      'critical',
      'high',
      'low',
      'medium',
    ]);
  });

  it("utilise le masculin ('Élevé') — s'accorde avec écart/doublon/pic", () => {
    expect(BILLING_SEVERITY_LABELS.high).toBe('Élevé');
  });

  it('mapping badge cohérent avec le design system Badge variants', () => {
    expect(BILLING_SEVERITY_BADGE.critical).toBe('crit');
    expect(BILLING_SEVERITY_BADGE.high).toBe('warn');
    expect(BILLING_SEVERITY_BADGE.medium).toBe('info');
    expect(BILLING_SEVERITY_BADGE.low).toBe('neutral');
  });

  it('est figé (Object.freeze)', () => {
    expect(Object.isFrozen(BILLING_SEVERITY_LABELS)).toBe(true);
    expect(Object.isFrozen(BILLING_SEVERITY_BADGE)).toBe(true);
  });
});

describe('BILLING_INVOICE_STATUS_LABELS', () => {
  it('couvre les 5 statuts de facture (imported→archived)', () => {
    expect(Object.keys(BILLING_INVOICE_STATUS_LABELS).sort()).toEqual([
      'anomaly',
      'archived',
      'audited',
      'imported',
      'validated',
    ]);
  });
});

describe('billingInsightLabel helper', () => {
  it('retourne la phrase narrative pour un code connu', () => {
    expect(billingInsightLabel('shadow_gap')).toBe(BILLING_INSIGHT_TYPE_LABELS.shadow_gap);
  });

  it('retourne le code brut si type inconnu (fallback)', () => {
    expect(billingInsightLabel('UNKNOWN_TYPE')).toBe('UNKNOWN_TYPE');
  });
});

// ── Monitoring registry ─────────────────────────────────────────────

describe('MONITORING_ALERT_TYPE_LABELS', () => {
  // Liste canonique des codes émis par le moteur monitoring v2 (snake_case)
  // + le moteur historique (UPPER_SNAKE).
  const HISTORICAL_CODES = [
    'BASE_NUIT_ELEVEE',
    'WEEKEND_ANORMAL',
    'DERIVE_TALON',
    'PIC_ANORMAL',
    'P95_HAUSSE',
    'DEPASSEMENT_PUISSANCE',
    'RUPTURE_PROFIL',
    'HORS_HORAIRES',
    'COURBE_PLATE',
    'DONNEES_MANQUANTES',
    'DOUBLONS_DST',
    'VALEURS_NEGATIVES',
    'SENSIBILITE_CLIMATIQUE',
  ];

  const V2_CODES = [
    'off_hours_consumption',
    'high_night_base',
    'power_risk',
    'weekend_anomaly',
    'high_base_load',
    'peak_anomaly',
    'profile_break',
    'flat_curve',
    'missing_data',
    'climate_sensitivity',
  ];

  it.each([...HISTORICAL_CODES, ...V2_CODES])('expose un libellé FR pour %s', (code) => {
    expect(MONITORING_ALERT_TYPE_LABELS[code]).toBeDefined();
    expect(typeof MONITORING_ALERT_TYPE_LABELS[code]).toBe('string');
  });

  it("DST devient 'heure d'été' (déjargonnage Vague A ét5')", () => {
    expect(MONITORING_ALERT_TYPE_LABELS.DOUBLONS_DST).toContain("heure d'été");
  });

  it("P95_HAUSSE devient 'Pointe récurrente' (déjargonnage)", () => {
    expect(MONITORING_ALERT_TYPE_LABELS.P95_HAUSSE).toContain('Pointe récurrente');
  });

  it('est figé (Object.freeze)', () => {
    expect(Object.isFrozen(MONITORING_ALERT_TYPE_LABELS)).toBe(true);
  });
});

describe('MONITORING_KPI_TOOLTIPS', () => {
  it('couvre les 5 KPI hero pmax/loadFactor/risk/quality/climate', () => {
    expect(Object.keys(MONITORING_KPI_TOOLTIPS).sort()).toEqual([
      'climate',
      'loadFactor',
      'pmax',
      'quality',
      'risk',
    ]);
  });

  it('chaque tooltip est narratif (≥80 chars) et conserve la formule technique', () => {
    expect(MONITORING_KPI_TOOLTIPS.pmax).toMatch(/Calcul/);
    expect(MONITORING_KPI_TOOLTIPS.pmax).toContain('P95');
    expect(MONITORING_KPI_TOOLTIPS.loadFactor).toContain('énergie totale / (Pmax');
    expect(MONITORING_KPI_TOOLTIPS.climate).toContain('kWh/jour par °C');
    for (const tooltip of Object.values(MONITORING_KPI_TOOLTIPS)) {
      expect(tooltip.length).toBeGreaterThanOrEqual(80);
    }
  });

  it('est figé (Object.freeze)', () => {
    expect(Object.isFrozen(MONITORING_KPI_TOOLTIPS)).toBe(true);
  });
});

describe('monitoringAlertLabel helper', () => {
  it('retourne le libellé pour un code connu', () => {
    expect(monitoringAlertLabel('BASE_NUIT_ELEVEE')).toBe('Base nuit élevée');
  });

  it('retourne le code brut si inconnu', () => {
    expect(monitoringAlertLabel('UNKNOWN_ALERT')).toBe('UNKNOWN_ALERT');
  });
});
