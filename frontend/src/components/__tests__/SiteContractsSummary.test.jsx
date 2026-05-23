// @vitest-environment jsdom
/**
 * P0-C 2026-05-23 — SiteContractsSummary affiche la couverture contractuelle.
 *
 * Vérifie :
 *  1. Badge "Tous les points sont couverts" quand status = contrat_rattache.
 *  2. Badge + liste des points non couverts quand status = contrat_partiel.
 *  3. CTA "Rattacher un contrat" affiché quand uncovered > 0.
 *  4. Libellés FR canoniques "Point de livraison électricité — PRM/PDL <code>"
 *     et "Point de livraison gaz — PCE <code>".
 *  5. Liste explicite des points couverts par contrat.
 *  6. Badge "Contrat expiré" et "Incohérence énergie".
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, within, cleanup, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../services/api', () => ({
  getPatrimoineContracts: vi.fn(),
}));
vi.mock('../../services/api/conformite', () => ({
  getSiteContractCoverage: vi.fn(),
}));

import { getPatrimoineContracts } from '../../services/api';
import { getSiteContractCoverage } from '../../services/api/conformite';
import SiteContractsSummary from '../SiteContractsSummary';

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

const dpElec = {
  id: 1,
  code: '14010101010101',
  energy_type: 'elec',
  status: 'active',
  label_fr: 'Point de livraison électricité — PRM/PDL 14010101010101',
  covering_contract_ids: [10],
};
const dpGaz = {
  id: 2,
  code: 'GI222222',
  energy_type: 'gaz',
  status: 'active',
  label_fr: 'Point de livraison gaz — PCE GI222222',
  covering_contract_ids: [],
};

const contractElec = {
  id: 10,
  supplier_name: 'EDF',
  energy_type: 'elec',
  reference_fournisseur: 'CTR-2025-001',
  start_date: '2025-01-01',
  end_date: '2026-12-31',
  delivery_point_ids: [1],
  delivery_points_count: 1,
};

describe('SiteContractsSummary (P0-C)', () => {
  it('affiche le badge "Tous les points sont couverts" si contrat_rattache', async () => {
    getPatrimoineContracts.mockResolvedValue({ contracts: [contractElec] });
    getSiteContractCoverage.mockResolvedValue({
      status: 'contrat_rattache',
      delivery_points_active: [dpElec],
      contracts_active: [contractElec],
      uncovered_delivery_points: [],
      expired_contracts: [],
      energy_mismatches: [],
      foreign_delivery_point_links: [],
      ready_for_billing: true,
      ready_for_purchase: true,
      actions: [],
    });

    renderWithRouter(<SiteContractsSummary siteId={1} />);
    await waitFor(() => expect(screen.getByText(/Tous les points sont couverts/i)).toBeTruthy());
    const banner = screen
      .getByText(/Tous les points sont couverts/i)
      .closest('[data-component="ContractCoverageBanner"]');
    expect(banner.getAttribute('data-coverage-status')).toBe('contrat_rattache');
  });

  it('affiche les points non couverts + CTA "Rattacher un contrat" si contrat_partiel', async () => {
    getPatrimoineContracts.mockResolvedValue({ contracts: [contractElec] });
    getSiteContractCoverage.mockResolvedValue({
      status: 'contrat_partiel',
      delivery_points_active: [dpElec, dpGaz],
      contracts_active: [contractElec],
      uncovered_delivery_points: [dpGaz],
      expired_contracts: [],
      energy_mismatches: [],
      foreign_delivery_point_links: [],
      ready_for_billing: false,
      ready_for_purchase: false,
      actions: [
        {
          code: 'ATTACH_CONTRACT',
          label_fr: 'Rattacher un contrat à Point de livraison gaz — PCE GI222222',
          target_type: 'delivery_point',
          target_id: 2,
        },
      ],
    });
    const onAttach = vi.fn();

    renderWithRouter(<SiteContractsSummary siteId={1} onAttachContract={onAttach} />);
    await waitFor(() => expect(screen.getByText(/Couverture partielle/i)).toBeTruthy());

    const banner = screen
      .getByText(/Couverture partielle/i)
      .closest('[data-component="ContractCoverageBanner"]');
    expect(within(banner).getByText(/Point de livraison gaz — PCE GI222222/)).toBeTruthy();
    expect(within(banner).getByText(/sans contrat actif/i)).toBeTruthy();

    const cta = screen.getByRole('button', { name: /Rattacher un contrat/i });
    fireEvent.click(cta);
    expect(onAttach).toHaveBeenCalledOnce();
  });

  it('affiche libellé FR électricité "Point de livraison électricité — PRM/PDL <code>"', async () => {
    getPatrimoineContracts.mockResolvedValue({ contracts: [contractElec] });
    getSiteContractCoverage.mockResolvedValue({
      status: 'contrat_rattache',
      delivery_points_active: [dpElec],
      contracts_active: [contractElec],
      uncovered_delivery_points: [],
      expired_contracts: [],
      energy_mismatches: [],
      foreign_delivery_point_links: [],
      ready_for_billing: true,
      ready_for_purchase: true,
      actions: [],
    });

    renderWithRouter(<SiteContractsSummary siteId={1} />);
    await waitFor(() =>
      expect(
        screen.getByText(/Point de livraison électricité — PRM\/PDL 14010101010101/)
      ).toBeTruthy()
    );
  });

  it('affiche libellé FR gaz "Point de livraison gaz — PCE <code>"', async () => {
    getPatrimoineContracts.mockResolvedValue({ contracts: [] });
    getSiteContractCoverage.mockResolvedValue({
      status: 'contrat_manquant',
      delivery_points_active: [dpGaz],
      contracts_active: [],
      uncovered_delivery_points: [dpGaz],
      expired_contracts: [],
      energy_mismatches: [],
      foreign_delivery_point_links: [],
      ready_for_billing: false,
      ready_for_purchase: false,
      actions: [],
    });

    renderWithRouter(<SiteContractsSummary siteId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/Point de livraison gaz — PCE GI222222/)).toBeTruthy()
    );
  });

  it('affiche badge "Contrat expiré" si status=contrat_expire', async () => {
    const expiredCt = { ...contractElec, end_date: '2024-01-01' };
    getPatrimoineContracts.mockResolvedValue({ contracts: [expiredCt] });
    getSiteContractCoverage.mockResolvedValue({
      status: 'contrat_expire',
      delivery_points_active: [dpElec],
      contracts_active: [],
      uncovered_delivery_points: [],
      expired_contracts: [
        {
          ...expiredCt,
          is_expired: true,
          label_fr: 'EDF — Électricité (contrat n° CTR-2025-001)',
        },
      ],
      energy_mismatches: [],
      foreign_delivery_point_links: [],
      ready_for_billing: false,
      ready_for_purchase: false,
      actions: [],
    });

    renderWithRouter(<SiteContractsSummary siteId={1} />);
    await waitFor(() => expect(screen.getByText(/Contrat expiré/i)).toBeTruthy());
  });

  it('affiche badge "Incohérence énergie" si status=contrat_incoherent', async () => {
    getPatrimoineContracts.mockResolvedValue({ contracts: [contractElec] });
    getSiteContractCoverage.mockResolvedValue({
      status: 'contrat_incoherent',
      delivery_points_active: [dpGaz],
      contracts_active: [contractElec],
      uncovered_delivery_points: [],
      expired_contracts: [],
      energy_mismatches: [
        {
          contract_id: 10,
          delivery_point_id: 2,
          contract_energy: 'elec',
          delivery_point_energy: 'gaz',
          message_fr:
            'Contrat EDF — Électricité (contrat n° CTR-2025-001) rattaché à Point de livraison gaz — PCE GI222222 — énergies incompatibles.',
        },
      ],
      foreign_delivery_point_links: [],
      ready_for_billing: false,
      ready_for_purchase: false,
      actions: [],
    });

    renderWithRouter(<SiteContractsSummary siteId={1} />);
    await waitFor(() => expect(screen.getByText(/Incohérence énergie/i)).toBeTruthy());
    expect(screen.getByText(/énergies incompatibles/i)).toBeTruthy();
  });

  it('affiche la liste des points couverts par contrat', async () => {
    getPatrimoineContracts.mockResolvedValue({ contracts: [contractElec] });
    getSiteContractCoverage.mockResolvedValue({
      status: 'contrat_rattache',
      delivery_points_active: [dpElec],
      contracts_active: [contractElec],
      uncovered_delivery_points: [],
      expired_contracts: [],
      energy_mismatches: [],
      foreign_delivery_point_links: [],
      ready_for_billing: true,
      ready_for_purchase: true,
      actions: [],
    });

    renderWithRouter(<SiteContractsSummary siteId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/Points de livraison couverts \(1\)/)).toBeTruthy()
    );
    const contractCard = screen.getByText(/EDF/i).closest('[data-contract-id="10"]');
    expect(
      within(contractCard).getByText(/Point de livraison électricité — PRM\/PDL 14010101010101/)
    ).toBeTruthy();
  });
});
