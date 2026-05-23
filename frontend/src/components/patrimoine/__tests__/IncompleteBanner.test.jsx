// @vitest-environment jsdom
/**
 * P0-B 2026-05-23 — bandeau "données à compléter" dans Patrimoine.
 *
 * Vérifie :
 *  1. Affiche le label FR de la règle.
 *  2. Affiche le compteur de sites si fourni.
 *  3. Affiche le hint FR depuis remediation.
 *  4. Affiche le message org-level si remediation_level=organisation/entite_juridique.
 *  5. Le bouton "Effacer" déclenche le callback.
 *  6. FR strict — pas d'anglais résiduel dans les libellés.
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import IncompleteBanner from '../IncompleteBanner';

afterEach(cleanup);

describe('IncompleteBanner', () => {
  it('affiche le libellé FR pour DT', () => {
    render(<IncompleteBanner rule="DT" siteCount={3} onClear={() => {}} />);
    expect(screen.getByText(/Sites à compléter pour le Décret Tertiaire/i)).toBeTruthy();
    expect(screen.getByText(/3 sites/)).toBeTruthy();
  });

  it('affiche le hint FR depuis remediation', () => {
    const remediation = {
      remediation_field: 'site.tertiaire_area_m2',
      remediation_level: 'site',
      remediation_label_fr: 'Surface tertiaire',
      remediation_hint_fr: 'Renseignez la surface tertiaire pour confirmer.',
      cta_label_fr: 'Compléter la surface',
    };
    render(
      <IncompleteBanner rule="DT" remediation={remediation} siteCount={2} onClear={() => {}} />,
    );
    expect(screen.getByText(/Renseignez la surface tertiaire/i)).toBeTruthy();
  });

  it('affiche le message org-level si remediation_level=organisation', () => {
    const remediation = {
      remediation_field: 'organisation.effectif_total',
      remediation_level: 'organisation',
      remediation_label_fr: "Effectif de l'organisation",
      remediation_hint_fr: 'Renseignez l\'effectif.',
      cta_label_fr: 'Compléter',
    };
    render(<IncompleteBanner rule="SME" remediation={remediation} onClear={() => {}} />);
    expect(screen.getByText(/À compléter dans les informations de l'organisation/i)).toBeTruthy();
    expect(screen.getByText(/écran en préparation/i)).toBeTruthy();
  });

  it('le bouton Effacer déclenche onClear', () => {
    const onClear = vi.fn();
    render(<IncompleteBanner rule="DT" siteCount={1} onClear={onClear} />);
    fireEvent.click(screen.getByRole('button', { name: /Effacer le filtre/i }));
    expect(onClear).toHaveBeenCalledOnce();
  });

  it('singulier vs pluriel sur le compteur de sites', () => {
    const { rerender } = render(<IncompleteBanner rule="DT" siteCount={1} onClear={() => {}} />);
    expect(screen.getByText(/1 site$/)).toBeTruthy();
    rerender(<IncompleteBanner rule="DT" siteCount={5} onClear={() => {}} />);
    expect(screen.getByText(/5 sites/)).toBeTruthy();
  });

  it('libellés FR pour les 5 règles', () => {
    for (const [rule, expected] of [
      ['DT', 'Décret Tertiaire'],
      ['BACS', 'Régulation chauffage (BACS)'],
      ['APER', 'EnR parking / toiture (APER)'],
      ['SME', 'Audit énergétique (SMÉ)'],
      ['BEGES', 'Bilan GES réglementaire'],
    ]) {
      cleanup();
      render(<IncompleteBanner rule={rule} onClear={() => {}} />);
      expect(screen.getByText(new RegExp(expected.replace(/[()\/]/g, '\\$&'), 'i'))).toBeTruthy();
    }
  });

  it('texte sans jargon technique anglais', () => {
    const remediation = {
      remediation_field: 'site.tertiaire_area_m2',
      remediation_level: 'site',
      remediation_label_fr: 'Surface tertiaire',
      remediation_hint_fr: 'Renseignez la surface.',
      cta_label_fr: 'Compléter',
    };
    const { container } = render(
      <IncompleteBanner rule="DT" remediation={remediation} siteCount={2} onClear={() => {}} />,
    );
    const text = container.textContent || '';
    for (const word of ['data', 'missing', 'fix', 'filter', 'banner', 'remediation']) {
      expect(text.toLowerCase()).not.toContain(word);
    }
  });
});
