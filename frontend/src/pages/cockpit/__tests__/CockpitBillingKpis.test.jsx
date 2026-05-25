// @vitest-environment jsdom
/**
 * Tests render CockpitBillingKpis (P0 cleanup cockpit, 2026-05-25).
 *
 * Vérifie :
 * 1. Les 4 cartes rendent correctement les KPIs Billing.
 * 2. Liens vers /bill-intel et /centre-action?domain=facturation.
 * 3. Fallback gracieux si billingKpis vide ou null.
 * 4. Format € FR pour surfacturations + format multi-énergie élec/gaz.
 */
import '@testing-library/jest-dom/vitest';
import React from 'react';
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import CockpitBillingKpis from '../CockpitBillingKpis';

afterEach(() => cleanup());

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

const samplePayload = {
  kpis: [
    {
      id: 'surfacturations_a_contester',
      label_fr: 'Surfacturations à contester',
      value: 19808.92,
      unit: 'EUR',
      source: 'BillingInsight.estimated_loss_eur',
      formula: 'Σ insights ouverts',
      period: 'snapshot',
      scope: 'org',
      link_to: '/bill-intel',
    },
    {
      id: 'anomalies_ouvertes',
      label_fr: 'Anomalies factures ouvertes',
      value: 109,
      unit: 'count',
      source: 'BillingInsight.id',
      formula: 'COUNT(insights status open/ack)',
      period: 'snapshot',
      scope: 'org',
      link_to: '/bill-intel',
    },
    {
      id: 'anomalies_par_energie',
      label_fr: 'Anomalies par énergie',
      value: { elec: 29, gaz: 49, inconnu: 31 },
      unit: 'count',
      source: 'BillingInsight × EnergyContract.energy_type',
      formula: 'GROUP BY energy_type',
      period: 'snapshot',
      scope: 'org',
      link_to: '/bill-intel',
    },
    {
      id: 'actions_facturation_ouvertes',
      label_fr: 'Actions facturation ouvertes',
      value: 52,
      unit: 'count',
      source: 'ActionCenterItem (domain=facturation)',
      formula: 'COUNT items non clôturés',
      period: 'snapshot',
      scope: 'org',
      link_to: '/centre-action?domain=facturation',
    },
  ],
  links: {
    bill_intel: '/bill-intel',
    centre_action_facturation: '/centre-action?domain=facturation',
  },
};

describe('CockpitBillingKpis — rendu 4 cartes', () => {
  it('rend la section avec data-testid stable', () => {
    renderWithRouter(<CockpitBillingKpis billingKpis={samplePayload} />);
    expect(screen.getByTestId('cockpit-billing-kpis')).toBeInTheDocument();
  });

  it('rend les 4 cartes avec leurs values', () => {
    renderWithRouter(<CockpitBillingKpis billingKpis={samplePayload} />);
    expect(screen.getByTestId('billing-kpi-surfacturations-value')).toHaveTextContent('19 809 €');
    expect(screen.getByTestId('billing-kpi-anomalies-ouvertes-value')).toHaveTextContent('109');
    expect(screen.getByTestId('billing-kpi-anomalies-energie-value')).toHaveTextContent(
      '29 élec · 49 gaz · 31 ?'
    );
    expect(screen.getByTestId('billing-kpi-actions-facturation-value')).toHaveTextContent('52');
  });

  it('rend les liens vers /bill-intel et /centre-action?domain=facturation', () => {
    renderWithRouter(<CockpitBillingKpis billingKpis={samplePayload} />);
    const surfactLink = screen.getByTestId('billing-kpi-surfacturations-link');
    expect(surfactLink).toHaveAttribute('href', '/bill-intel');
    const actionsLink = screen.getByTestId('billing-kpi-actions-facturation-link');
    expect(actionsLink).toHaveAttribute('href', '/centre-action?domain=facturation');
  });

  it('expose la source de chaque KPI (auditeur conformité)', () => {
    renderWithRouter(<CockpitBillingKpis billingKpis={samplePayload} />);
    const surfactCard = screen.getByTestId('billing-kpi-surfacturations');
    expect(surfactCard).toHaveTextContent(/Source : BillingInsight\.estimated_loss_eur/);
  });

  it('rend "—" si surfacturations = 0 (pas "0 €" trompeur)', () => {
    const payload = {
      ...samplePayload,
      kpis: samplePayload.kpis.map((k) =>
        k.id === 'surfacturations_a_contester' ? { ...k, value: 0 } : k
      ),
    };
    renderWithRouter(<CockpitBillingKpis billingKpis={payload} />);
    expect(screen.getByTestId('billing-kpi-surfacturations-value')).toHaveTextContent('—');
  });
});

describe('CockpitBillingKpis — fallback gracieux', () => {
  it('ne rend rien si billingKpis null', () => {
    const { container } = renderWithRouter(<CockpitBillingKpis billingKpis={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('ne rend rien si kpis vide', () => {
    const { container } = renderWithRouter(<CockpitBillingKpis billingKpis={{ kpis: [] }} />);
    expect(container.firstChild).toBeNull();
  });

  it('ne rend rien si payload mal formé', () => {
    const { container } = renderWithRouter(<CockpitBillingKpis billingKpis={{}} />);
    expect(container.firstChild).toBeNull();
  });
});

describe("CockpitBillingKpis — formats énergie sans 'inconnu' nuls", () => {
  it('omet "? inconnu" si breakdown.inconnu = 0', () => {
    const payload = {
      ...samplePayload,
      kpis: samplePayload.kpis.map((k) =>
        k.id === 'anomalies_par_energie'
          ? { ...k, value: { elec: 5, gaz: 3, inconnu: 0 } }
          : k
      ),
    };
    renderWithRouter(<CockpitBillingKpis billingKpis={payload} />);
    expect(screen.getByTestId('billing-kpi-anomalies-energie-value')).toHaveTextContent(
      '5 élec · 3 gaz'
    );
    expect(screen.getByTestId('billing-kpi-anomalies-energie-value')).not.toHaveTextContent(
      /\binconnu\b/
    );
  });
});
