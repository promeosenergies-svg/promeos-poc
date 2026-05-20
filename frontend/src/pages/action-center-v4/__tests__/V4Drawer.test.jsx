// @vitest-environment jsdom
/**
 * M2-5.10.B.bis — Tests du composant V4Drawer (drawer Sol custom).
 *
 * Contourne le wrapper `src/ui/Drawer.jsx` legacy pour porter le pixel-perfect
 * Sol (largeur 760, header sticky Sol, footer sticky canvas).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { V4Drawer } from '../components/V4Drawer';

afterEach(cleanup);

describe('V4Drawer', () => {
  test('renders nothing when closed', () => {
    const { container } = render(
      <V4Drawer open={false} onClose={vi.fn()}>
        <div>body</div>
      </V4Drawer>
    );
    expect(container.firstChild).toBeNull();
  });

  test('renders the dialog with role=dialog aria-modal when open', () => {
    render(
      <V4Drawer open onClose={vi.fn()} ariaLabel="Détail">
        <div>body</div>
      </V4Drawer>
    );
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-label', 'Détail');
  });

  test('renders the children inside the body', () => {
    render(
      <V4Drawer open onClose={vi.fn()}>
        <span>body content</span>
      </V4Drawer>
    );
    expect(screen.getByText('body content')).toBeInTheDocument();
  });

  test('renders the breadcrumb slot in the header', () => {
    render(
      <V4Drawer open onClose={vi.fn()} breadcrumb={<span>BC</span>}>
        <div />
      </V4Drawer>
    );
    expect(screen.getByText('BC')).toBeInTheDocument();
  });

  test('renders the headerActions slot below the breadcrumb', () => {
    render(
      <V4Drawer open onClose={vi.fn()} headerActions={<button type="button">Action</button>}>
        <div />
      </V4Drawer>
    );
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument();
  });

  test('renders the footer slot when provided', () => {
    render(
      <V4Drawer open onClose={vi.fn()} footer={<span>footer-content</span>}>
        <div />
      </V4Drawer>
    );
    expect(screen.getByText('footer-content')).toBeInTheDocument();
  });

  test('hides the footer when not provided', () => {
    const { container } = render(
      <V4Drawer open onClose={vi.fn()}>
        <div />
      </V4Drawer>
    );
    expect(container.querySelector('footer')).toBeNull();
  });

  test('Escape calls onClose', () => {
    const onClose = vi.fn();
    render(
      <V4Drawer open onClose={onClose}>
        <div />
      </V4Drawer>
    );
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });

  test('clicking the backdrop calls onClose', () => {
    const onClose = vi.fn();
    const { container } = render(
      <V4Drawer open onClose={onClose}>
        <div />
      </V4Drawer>
    );
    // Premier child du dialog = backdrop (absolute inset-0).
    const backdrop = container.querySelector('[aria-hidden="true"]');
    fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  test('clicking the close button calls onClose', () => {
    const onClose = vi.fn();
    render(
      <V4Drawer open onClose={onClose}>
        <div />
      </V4Drawer>
    );
    fireEvent.click(screen.getByRole('button', { name: /fermer/i }));
    expect(onClose).toHaveBeenCalled();
  });

  test('applies the custom width prop (default 760px)', () => {
    const { rerender, container } = render(
      <V4Drawer open onClose={vi.fn()}>
        <div />
      </V4Drawer>
    );
    // Le panel est le 2e child du dialog (1er = backdrop).
    let panel = container.querySelectorAll('[role="dialog"] > div')[1];
    expect(panel.style.width).toBe('760px');

    rerender(
      <V4Drawer open onClose={vi.fn()} width={900}>
        <div />
      </V4Drawer>
    );
    panel = container.querySelectorAll('[role="dialog"] > div')[1];
    expect(panel.style.width).toBe('900px');
  });
});
