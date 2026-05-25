// @vitest-environment jsdom
/**
 * Tests Cockpit P1 (2026-05-25) — CockpitExecutiveNarrative.
 *
 * Vérifie :
 * 1. Les 3 blocs canoniques rendent (Situation 30s / Top 3 / Pourquoi).
 * 2. 5 KPIs DAF/DG s'affichent avec format € FR, /100, jours, count.
 * 3. Top 3 priorités : badge rank, why_fr, impact, CTA hub canonique.
 * 4. Fallback gracieux : null/vide → composant retourne null.
 * 5. Doctrine §6.2 : CTA pointent vers /bill-intel /conformite /patrimoine.
 */
import '@testing-library/jest-dom/vitest';
import React from 'react';
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import CockpitExecutiveNarrative from '../CockpitExecutiveNarrative';

afterEach(() => cleanup());

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

const sampleSummary = {
  kpis: [
    {
      id: 'score_conformite',
      label_fr: 'Score conformité',
      value: 36.2,
      unit: '/100',
      source: 'compliance_score_service.compute_portfolio_compliance',
      formula: 'Moyenne pondérée frameworks DT/BACS/APER',
      period: 'snapshot',
      scope: '5 site(s)',
      sub_label_fr: 'Fiabilité : low',
    },
    {
      id: 'risque_financier_a_contester',
      label_fr: 'Surfacturations à contester',
      value: 19808.92,
      unit: '€',
      source: 'BillingInsight.estimated_loss_eur',
      formula: 'Σ insights open/ack',
      period: 'snapshot',
      scope: '5 site(s)',
    },
    {
      id: 'prochaine_echeance',
      label_fr: 'Prochaine échéance',
      value: 42,
      unit: 'jours',
      source: 'compliance.timeline.next_deadline',
      formula: 'MIN(events.deadline)',
      period: 'snapshot',
      scope: 'org',
      sub_label_fr: 'Échéance OPERAT 2026',
    },
    {
      id: 'actions_ouvertes',
      label_fr: 'Actions ouvertes',
      value: 58,
      unit: 'actions',
      source: 'ActionCenterItem',
      formula: 'COUNT(lifecycle ≠ closed)',
      period: 'snapshot',
      scope: 'org',
    },
    {
      id: 'sites_dans_perimetre',
      label_fr: 'Sites suivis',
      value: 5,
      unit: 'sites',
      source: 'Site.actif=True',
      formula: 'COUNT sites actifs',
      period: 'snapshot',
      scope: 'org',
    },
  ],
};

const samplePriorities = [
  {
    id: 'billing_439',
    label_fr: 'Surfacturation à contester (2149 €)',
    why_fr: 'Montant à contester',
    impact: { value: 2148.64, unit: '€' },
    deadline: { iso: null, days_remaining: null },
    perimetre_fr: 'Site #3',
    cta: { label_fr: 'Voir la facture', link: '/bill-intel?insight=439' },
    priority_rank: 1,
  },
  {
    id: 'compliance_next',
    label_fr: 'Échéance conformité : OPERAT 2026',
    why_fr: 'Risque réglementaire',
    impact: { value: 42, unit: 'jours restants' },
    deadline: { iso: '2026-07-01', days_remaining: 42 },
    perimetre_fr: 'org',
    cta: { label_fr: "Voir l'obligation", link: '/conformite' },
    priority_rank: 2,
  },
];

describe('CockpitExecutiveNarrative — 3 blocs', () => {
  it('rend la section narrative complète', () => {
    renderWithRouter(
      <CockpitExecutiveNarrative
        executiveSummary={sampleSummary}
        topPriorities={samplePriorities}
      />
    );
    expect(screen.getByTestId('cockpit-executive-narrative')).toBeInTheDocument();
    expect(screen.getByTestId('exec-situation')).toBeInTheDocument();
    expect(screen.getByTestId('exec-top-priorities')).toBeInTheDocument();
    expect(screen.getByTestId('exec-why-microcopy')).toBeInTheDocument();
  });

  it('rend les 5 KPIs du bloc « Situation en 30 secondes »', () => {
    renderWithRouter(
      <CockpitExecutiveNarrative
        executiveSummary={sampleSummary}
        topPriorities={samplePriorities}
      />
    );
    expect(screen.getByTestId('exec-kpi-score_conformite-value')).toHaveTextContent('36,2 /100');
    expect(screen.getByTestId('exec-kpi-risque_financier_a_contester-value')).toHaveTextContent(
      /19\s?809\s?€/
    );
    expect(screen.getByTestId('exec-kpi-prochaine_echeance-value')).toHaveTextContent('42 j');
    expect(screen.getByTestId('exec-kpi-actions_ouvertes-value')).toHaveTextContent('58');
    expect(screen.getByTestId('exec-kpi-sites_dans_perimetre-value')).toHaveTextContent('5');
  });

  it('rend la couleur seuil pour score conformité < 50 → rouge', () => {
    renderWithRouter(
      <CockpitExecutiveNarrative
        executiveSummary={sampleSummary}
        topPriorities={samplePriorities}
      />
    );
    const scoreValue = screen.getByTestId('exec-kpi-score_conformite-value');
    expect(scoreValue.className).toMatch(/text-red-600/);
  });
});

describe('CockpitExecutiveNarrative — Top 3 priorités', () => {
  it('rend chaque priorité avec rang + why + impact + CTA', () => {
    renderWithRouter(
      <CockpitExecutiveNarrative
        executiveSummary={sampleSummary}
        topPriorities={samplePriorities}
      />
    );
    expect(screen.getByTestId('exec-priority-1')).toBeInTheDocument();
    expect(screen.getByTestId('exec-priority-2')).toBeInTheDocument();
    expect(screen.queryByTestId('exec-priority-3')).toBeNull();

    const p1 = screen.getByTestId('exec-priority-1');
    expect(p1).toHaveTextContent('Montant à contester');
    expect(p1).toHaveTextContent(/2\s?149\s?€/);

    const cta1 = screen.getByTestId('exec-priority-1-cta');
    expect(cta1).toHaveAttribute('href', '/bill-intel?insight=439');
    expect(cta1).toHaveTextContent('Voir la facture');
  });

  it('CTAs pointent uniquement vers pages hub canoniques (doctrine §6.2)', () => {
    renderWithRouter(
      <CockpitExecutiveNarrative
        executiveSummary={sampleSummary}
        topPriorities={samplePriorities}
      />
    );
    const cta1 = screen.getByTestId('exec-priority-1-cta');
    const cta2 = screen.getByTestId('exec-priority-2-cta');
    const allowed = ['/bill-intel', '/conformite', '/patrimoine', '/centre-action'];
    for (const cta of [cta1, cta2]) {
      const href = cta.getAttribute('href');
      expect(
        allowed.some((route) => href.startsWith(route)),
        `CTA href ${href} doit pointer vers une page hub canonique`
      ).toBe(true);
    }
  });

  it('affiche le bloc échéance quand days_remaining présent', () => {
    renderWithRouter(
      <CockpitExecutiveNarrative
        executiveSummary={sampleSummary}
        topPriorities={samplePriorities}
      />
    );
    const p2 = screen.getByTestId('exec-priority-2');
    expect(p2).toHaveTextContent('dans 42 j');
  });
});

describe('CockpitExecutiveNarrative — fallback gracieux', () => {
  it('retourne null si kpis vide ET priorities vide', () => {
    const { container } = renderWithRouter(
      <CockpitExecutiveNarrative executiveSummary={{ kpis: [] }} topPriorities={[]} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('retourne null si tout est null', () => {
    const { container } = renderWithRouter(
      <CockpitExecutiveNarrative executiveSummary={null} topPriorities={null} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('rend seulement Situation si top_priorities vide', () => {
    renderWithRouter(
      <CockpitExecutiveNarrative executiveSummary={sampleSummary} topPriorities={[]} />
    );
    expect(screen.getByTestId('exec-situation')).toBeInTheDocument();
    expect(screen.queryByTestId('exec-top-priorities')).toBeNull();
  });
});
