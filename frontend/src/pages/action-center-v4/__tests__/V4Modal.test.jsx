// @vitest-environment jsdom
/**
 * M2-6.C.1-reduit — Tests V4Modal dédiés (coverage anti-régression).
 *
 * V4Modal existe depuis M2-5.11.A et est consommé par 6 modals enfants,
 * mais n'avait pas de tests dédiés (coverage indirect seulement). Ce
 * fichier livre la coverage cardinale + valide le nouveau variant
 * warning Q30=C/Q36=A.
 *
 * Signature actuelle : `{ open, onClose, ariaLabel, title, children,
 * footer, width=480, variant='default', testId='v4-modal' }`.
 * Pattern footer = JSX passé directement (pas primaryAction/secondaryAction).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { V4Modal } from '../components/V4Modal';

afterEach(cleanup);

describe('V4Modal — wrapper structurel Sol (M2-5.11.A + M2-6.C.1-reduit)', () => {
  test('rend rien quand open=false', () => {
    render(
      <V4Modal open={false} onClose={() => {}} title="Test">
        Body
      </V4Modal>
    );
    expect(screen.queryByTestId('v4-modal')).not.toBeInTheDocument();
  });

  test('rend header + body + footer quand open=true', () => {
    render(
      <V4Modal
        open
        onClose={() => {}}
        title="Mon Modal"
        footer={<button type="button">Valider</button>}
      >
        Corps spécifique
      </V4Modal>
    );
    expect(screen.getByText('Mon Modal')).toBeInTheDocument();
    expect(screen.getByText('Corps spécifique')).toBeInTheDocument();
    expect(screen.getByText('Valider')).toBeInTheDocument();
  });

  test('click sur backdrop déclenche onClose', () => {
    const onClose = vi.fn();
    render(
      <V4Modal open onClose={onClose} title="Test">
        Body
      </V4Modal>
    );
    fireEvent.click(screen.getByTestId('v4-modal-backdrop'));
    expect(onClose).toHaveBeenCalled();
  });

  test('Escape ferme le modal', () => {
    const onClose = vi.fn();
    render(
      <V4Modal open onClose={onClose} title="Test">
        Body
      </V4Modal>
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  test('a11y : role=dialog + aria-modal=true + aria-label', () => {
    render(
      <V4Modal open onClose={() => {}} title="Titre cardinal">
        Body
      </V4Modal>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    // aria-label utilise title comme fallback
    expect(dialog).toHaveAttribute('aria-label', 'Titre cardinal');
  });

  test('aria-label utilise ariaLabel prop si fourni (override title)', () => {
    render(
      <V4Modal open onClose={() => {}} title="Titre" ariaLabel="Aria custom">
        Body
      </V4Modal>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-label', 'Aria custom');
  });

  test('body scroll lock activé pendant open', () => {
    const { unmount } = render(
      <V4Modal open onClose={() => {}} title="Test">
        Body
      </V4Modal>
    );
    expect(document.body.style.overflow).toBe('hidden');
    unmount();
    // Cleanup restaure overflow.
    expect(document.body.style.overflow).toBe('');
  });

  // ── M2-6.C.1-reduit — variant warning Q30=C/Q36=A ──────────────────

  test('variant="default" par défaut (Q36=A fallback)', () => {
    render(
      <V4Modal open onClose={() => {}} title="Test">
        Body
      </V4Modal>
    );
    const dialog = screen.getByTestId('v4-modal');
    expect(dialog).toHaveAttribute('data-variant', 'default');
  });

  test('variant="warning" expose data-variant="warning" (Q36=A)', () => {
    render(
      <V4Modal open onClose={() => {}} title="Confirmer clôture" variant="warning">
        Body
      </V4Modal>
    );
    const dialog = screen.getByTestId('v4-modal');
    expect(dialog).toHaveAttribute('data-variant', 'warning');
  });

  // M2-6.C.P2-cleanup P2-3 — sélection sémantique du panel via
  // `getByRole('dialog')` + filtre backdrop (`aria-hidden="true"`) au lieu du
  // string-match `container.innerHTML` global (fragile aux changements de
  // markup parent). On garde une regex sur l'attribut `style` de l'élément
  // ciblé : jsdom ne résout pas les `var()` dans `toHaveStyle`, mais préserve
  // intacte la chaîne inline écrite par React (assertion exacte, scope précis).
  function modalPanel(dialog) {
    return dialog.querySelector('div:not([aria-hidden="true"])');
  }

  test('variant="warning" applique border-top ambre --sol-attention-line', () => {
    render(
      <V4Modal open onClose={() => {}} title="Warning" variant="warning">
        Body
      </V4Modal>
    );
    const panel = modalPanel(screen.getByRole('dialog'));
    expect(panel?.getAttribute('style')).toMatch(
      /border-top:\s*3px solid var\(--sol-attention-line\)/
    );
  });

  test('variant="default" n\'applique PAS border-top warning', () => {
    render(
      <V4Modal open onClose={() => {}} title="Default" variant="default">
        Body
      </V4Modal>
    );
    const panel = modalPanel(screen.getByRole('dialog'));
    expect(panel?.getAttribute('style')).not.toMatch(
      /border-top:\s*3px solid var\(--sol-attention-line\)/
    );
  });

  test('testId custom propage sur data-testid + backdrop', () => {
    render(
      <V4Modal open onClose={() => {}} title="Test" testId="my-modal">
        Body
      </V4Modal>
    );
    expect(screen.getByTestId('my-modal')).toBeInTheDocument();
    expect(screen.getByTestId('my-modal-backdrop')).toBeInTheDocument();
  });
});
