// @vitest-environment jsdom
/**
 * P0-B 2026-05-23 — CadreApplicable interactif.
 *
 * Vérifie :
 *  1. Une carte DATA_MISSING est cliquable et ouvre le panneau.
 *  2. Une carte NOT_APPLICABLE n'est pas cliquable.
 *  3. Une carte APPLICABLE n'est pas cliquable (sauf si onRuleClick fourni).
 *  4. Le panneau affiche site / champ / hint FR.
 *  5. Le CTA navigue vers /patrimoine?incomplete=<RULE>.
 *  6. Le callback onRuleClick custom est appelé avec (rule, summary).
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, within, cleanup } from '@testing-library/react';

afterEach(cleanup);
import { MemoryRouter, Routes, Route, useLocation } from 'react-router-dom';
import CadreApplicable from '../CadreApplicable';

function NavWatcher() {
  const location = useLocation();
  return <div data-testid="location">{location.pathname + location.search}</div>;
}

function renderWithRouter(ui) {
  return render(
    <MemoryRouter initialEntries={['/cockpit/strategique']}>
      <Routes>
        <Route path="/cockpit/strategique" element={<>{ui}<NavWatcher /></>} />
        <Route path="/patrimoine" element={<NavWatcher />} />
      </Routes>
    </MemoryRouter>,
  );
}

const dataMissingSite = (rule, scope_id, label, reason_code, remediation) => ({
  rule_code: rule,
  rule_version: 'test',
  scope_level: 'site',
  scope_id,
  scope_label: label,
  status: 'data_missing',
  reason_code,
  reason_human: 'donnée manquante',
  missing_inputs: ['x'],
  ...remediation,
});

describe('CadreApplicable interactif', () => {
  it('tile DATA_MISSING est marquée actionable et ouvre le panneau', () => {
    const applicability = {
      DT: [
        dataMissingSite('DT', 1, 'Site Alpha', 'DT.DATA_MISSING.SURFACE', {
          remediation_field: 'site.tertiaire_area_m2',
          remediation_level: 'site',
          remediation_label_fr: 'Surface tertiaire',
          remediation_hint_fr: 'Renseignez la surface tertiaire.',
          cta_label_fr: 'Compléter la surface',
        }),
      ],
      BACS: [],
      APER: [],
      SME: [],
      BEGES: [],
    };

    renderWithRouter(<CadreApplicable applicability={applicability} maturity={0.6} />);
    const dtTile = screen.getByRole('button', { name: /Décret tertiaire/i });
    expect(dtTile.getAttribute('data-actionable')).toBe('true');
    expect(dtTile.getAttribute('data-status')).toBe('data_missing');

    fireEvent.click(dtTile);
    const panel = screen.getByRole('dialog', { name: /Données à compléter/i });
    expect(panel).toBeTruthy();
    expect(within(panel).getByText('Site Alpha')).toBeTruthy();
    expect(within(panel).getByText('Surface tertiaire')).toBeTruthy();
    expect(within(panel).getByText(/Renseignez la surface tertiaire/i)).toBeTruthy();
  });

  it('tile NOT_APPLICABLE est non-actionable et ne propose pas de CTA', () => {
    const applicability = {
      DT: [
        {
          rule_code: 'DT',
          status: 'not_applicable',
          scope_level: 'site',
          scope_id: 1,
          scope_label: 'Site',
          reason_code: 'DT.NOT_APPLICABLE.SDP_LT_1000',
          reason_human: 'surface < 1000',
        },
      ],
    };
    renderWithRouter(<CadreApplicable applicability={applicability} maturity={1.0} />);
    const dtTile = screen.getByRole('button', { name: /Décret tertiaire/i });
    expect(dtTile.getAttribute('data-actionable')).toBe('false');

    fireEvent.click(dtTile);
    // Pas de panneau ouvert
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  it('tile APPLICABLE est non-actionable par défaut', () => {
    const applicability = {
      DT: [
        {
          rule_code: 'DT',
          status: 'applicable',
          scope_level: 'site',
          scope_id: 1,
          scope_label: 'Site',
          reason_code: 'DT.APPLICABLE',
          reason_human: 'OK',
        },
      ],
    };
    renderWithRouter(<CadreApplicable applicability={applicability} maturity={0.8} />);
    const dtTile = screen.getByRole('button', { name: /Décret tertiaire/i });
    expect(dtTile.getAttribute('data-actionable')).toBe('false');
  });

  it('CTA navigue vers /patrimoine?incomplete=<RULE>', () => {
    const applicability = {
      DT: [],
      BACS: [
        dataMissingSite('BACS', 2, 'Bâtiment Beta', 'BACS.DATA_MISSING.CVC_POWER', {
          remediation_field: 'batiment.cvc_power_kw',
          remediation_level: 'batiment',
          remediation_label_fr: 'Puissance CVC',
          remediation_hint_fr: 'Renseignez la puissance.',
          cta_label_fr: 'Compléter la puissance CVC',
        }),
      ],
      APER: [],
      SME: [],
      BEGES: [],
    };
    renderWithRouter(<CadreApplicable applicability={applicability} maturity={0.4} />);
    fireEvent.click(screen.getByRole('button', { name: /Régulation chauffage/i }));
    const cta = screen.getByRole('button', { name: /Compléter la puissance CVC/i });
    fireEvent.click(cta);
    const location = screen.getByTestId('location');
    expect(location.textContent).toBe('/patrimoine?incomplete=BACS');
  });

  it('callback onRuleClick custom reçoit (rule, summary)', () => {
    const applicability = {
      DT: [
        {
          rule_code: 'DT',
          status: 'applicable',
          scope_level: 'site',
          scope_id: 1,
          scope_label: 'Site',
          reason_code: 'DT.APPLICABLE',
          reason_human: 'OK',
        },
      ],
    };
    const cb = vi.fn();
    renderWithRouter(
      <CadreApplicable applicability={applicability} maturity={0.5} onRuleClick={cb} />,
    );
    fireEvent.click(screen.getByRole('button', { name: /Décret tertiaire/i }));
    expect(cb).toHaveBeenCalledOnce();
    const [rule, summary] = cb.mock.calls[0];
    expect(rule).toBe('DT');
    expect(summary).toMatchObject({ status: 'applicable', count: 1 });
  });

  it('le panneau peut être fermé', () => {
    const applicability = {
      DT: [
        dataMissingSite('DT', 1, 'Site X', 'DT.DATA_MISSING.SURFACE', {
          remediation_label_fr: 'Surface tertiaire',
          remediation_hint_fr: 'Hint.',
          cta_label_fr: 'Compléter',
        }),
      ],
    };
    renderWithRouter(<CadreApplicable applicability={applicability} maturity={0.5} />);
    fireEvent.click(screen.getByRole('button', { name: /Décret tertiaire/i }));
    expect(screen.queryByRole('dialog')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: /Fermer/i }));
    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
