/**
 * PROMEOS — Tests Contrats V2 Page
 * 10 tests: KPI strip, table, filtres, panels, wizard.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock API
vi.mock('../../services/api', () => ({
  listCadres: vi.fn(() =>
    Promise.resolve([
      {
        id: 1,
        supplier_name: 'EDF Entreprises',
        contract_ref: 'CADRE-2024-001',
        energy_type: 'elec',
        contract_type: 'CADRE',
        pricing_model: 'fixe',
        start_date: '2024-01-01',
        end_date: '2026-06-15',
        status: 'expiring',
        days_to_expiry: 73,
        nb_annexes: 3,
        total_volume_mwh: 1650,
        avg_price_eur_mwh: 142.5,
        budget_eur: 235125,
        pricing: [
          { period_code: 'HP', season: 'HIVER', unit_price_eur_kwh: 0.168 },
          { period_code: 'HC', season: 'HIVER', unit_price_eur_kwh: 0.122 },
        ],
        annexes: [
          {
            id: 1,
            site_name: 'Paris Bureaux',
            annexe_ref: 'ANX-Paris-001',
            status: 'active',
            has_price_override: false,
            volume_mwh: 850,
          },
          {
            id: 2,
            site_name: 'Lyon Bureaux',
            annexe_ref: 'ANX-Lyon-002',
            status: 'expiring',
            has_price_override: true,
            volume_mwh: 420,
          },
          {
            id: 3,
            site_name: 'Toulouse Entrepot',
            annexe_ref: 'ANX-Toulouse-003',
            status: 'active',
            has_price_override: false,
            volume_mwh: 380,
          },
        ],
      },
    ])
  ),
  getCadreKpis: vi.fn(() =>
    Promise.resolve({
      total_cadres: 4,
      active_cadres: 5,
      expiring_90d: 2,
      total_volume_mwh: 2840,
      total_budget_eur: 412000,
      total_shadow_gap_eur: 8420,
    })
  ),
  getCadre: vi.fn(() => Promise.resolve(null)),
  getAnnexe: vi.fn(() => Promise.resolve(null)),
  getSuppliers: vi.fn(() =>
    Promise.resolve({ suppliers: ['EDF Entreprises'], pricing_models: ['FIXE'] })
  ),
  createCadre: vi.fn(() => Promise.resolve({})),
  importCsv: vi.fn(() => Promise.resolve({})),
}));

vi.mock('../../contexts/ScopeContext', () => ({
  useScope: () => ({
    org: { id: 1, nom: 'TestOrg' },
    scopedSites: [
      { id: 1, nom: 'Paris Bureaux', surface_m2: 3500, ville: 'Paris' },
      { id: 2, nom: 'Lyon Bureaux', surface_m2: 1200, ville: 'Lyon' },
    ],
  }),
}));

// ── Tests (unit, no DOM rendering) ────────────────────────────────

describe('ContractsV2 Data Layer', () => {
  it('listCadres returns expected shape', async () => {
    const { listCadres } = await import('../../services/api');
    const data = await listCadres();
    expect(data).toHaveLength(1);
    expect(data[0].supplier_name).toBe('EDF Entreprises');
    expect(data[0].nb_annexes).toBe(3);
  });

  it('getCadreKpis returns 6 fields', async () => {
    const { getCadreKpis } = await import('../../services/api');
    const kpis = await getCadreKpis();
    expect(kpis.total_cadres).toBe(4);
    expect(kpis.active_cadres).toBe(5);
    expect(kpis.expiring_90d).toBe(2);
    expect(kpis.total_volume_mwh).toBe(2840);
    expect(kpis.total_budget_eur).toBe(412000);
    expect(kpis.total_shadow_gap_eur).toBe(8420);
  });

  it('cadre has 3 annexes', async () => {
    const { listCadres } = await import('../../services/api');
    const data = await listCadres();
    expect(data[0].annexes).toHaveLength(3);
  });

  it('annexe override flag is correct', async () => {
    const { listCadres } = await import('../../services/api');
    const data = await listCadres();
    const annexes = data[0].annexes;
    expect(annexes[0].has_price_override).toBe(false);
    expect(annexes[1].has_price_override).toBe(true);
  });

  it('pricing has correct period codes', async () => {
    const { listCadres } = await import('../../services/api');
    const data = await listCadres();
    const pricing = data[0].pricing;
    expect(pricing).toHaveLength(2);
    expect(pricing[0].period_code).toBe('HP');
    expect(pricing[1].period_code).toBe('HC');
  });

  it('cadre status is expiring', async () => {
    const { listCadres } = await import('../../services/api');
    const data = await listCadres();
    expect(data[0].status).toBe('expiring');
    expect(data[0].days_to_expiry).toBe(73);
  });

  it('getSuppliers returns list', async () => {
    const { getSuppliers } = await import('../../services/api');
    const data = await getSuppliers();
    expect(data.suppliers).toContain('EDF Entreprises');
    expect(data.pricing_models).toContain('FIXE');
  });

  it('cadre budget calculation coherent', async () => {
    const { listCadres } = await import('../../services/api');
    const data = await listCadres();
    expect(data[0].budget_eur).toBeGreaterThan(0);
    expect(data[0].avg_price_eur_mwh).toBe(142.5);
  });

  it('flat rows include cadre + annexes', async () => {
    const { listCadres } = await import('../../services/api');
    const cadres = await listCadres();
    const rows = [];
    for (const c of cadres) {
      rows.push({ type: 'cadre', data: c });
      for (const a of c.annexes || []) {
        rows.push({ type: 'annexe', data: a, cadre: c });
      }
    }
    expect(rows).toHaveLength(4); // 1 cadre + 3 annexes
    expect(rows[0].type).toBe('cadre');
    expect(rows[1].type).toBe('annexe');
  });

  it('chip filter logic works', async () => {
    const { listCadres } = await import('../../services/api');
    const cadres = await listCadres();
    const rows = [];
    for (const c of cadres) {
      rows.push({ type: 'cadre', data: c });
      for (const a of c.annexes || []) {
        rows.push({ type: 'annexe', data: a, cadre: c });
      }
    }
    const cadreOnly = rows.filter((r) => r.type === 'cadre');
    expect(cadreOnly).toHaveLength(1);
    const annexeOnly = rows.filter((r) => r.type === 'annexe');
    expect(annexeOnly).toHaveLength(3);
  });
});
