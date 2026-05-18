// @vitest-environment jsdom
/**
 * M2-5.3.B — Tests du composant EvidenceItem (rendu jsdom).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';

import { EvidenceItem } from '../components/EvidenceItem';

afterEach(cleanup);

describe('EvidenceItem', () => {
  test('renders filename and a "En attente" badge when verified_at is null', () => {
    render(
      <EvidenceItem
        evidence={{
          id: '1',
          original_filename: 'facture-q3.pdf',
          verified_at: null,
          expires_at: null,
          uploaded_at: '2026-05-01T00:00:00Z',
          file_size_bytes: 1024,
        }}
      />
    );
    expect(screen.getByText('facture-q3.pdf')).toBeInTheDocument();
    expect(screen.getByText('En attente')).toBeInTheDocument();
  });

  test('renders a "Vérifiée" badge when verified and not expired', () => {
    const future = new Date(Date.now() + 86400000).toISOString();
    render(
      <EvidenceItem
        evidence={{
          id: '1',
          original_filename: 'x.pdf',
          verified_at: '2026-05-10T10:00:00Z',
          expires_at: future,
          uploaded_at: '2026-05-01T00:00:00Z',
        }}
      />
    );
    expect(screen.getByText('Vérifiée')).toBeInTheDocument();
  });

  test('renders an "Expirée" badge when the expiry date has passed', () => {
    render(
      <EvidenceItem
        evidence={{
          id: '1',
          original_filename: 'x.pdf',
          verified_at: '2026-01-01T00:00:00Z',
          expires_at: '2026-02-01T00:00:00Z',
          uploaded_at: '2026-01-01T00:00:00Z',
        }}
      />
    );
    expect(screen.getByText('Expirée')).toBeInTheDocument();
  });

  test('never exposes storage_uri', () => {
    render(
      <EvidenceItem
        evidence={{
          id: '1',
          original_filename: 'x.pdf',
          verified_at: null,
          uploaded_at: '2026-05-01T00:00:00Z',
          storage_uri: '/internal/storage/secret/x.pdf',
        }}
      />
    );
    expect(screen.queryByText(/internal\/storage/)).not.toBeInTheDocument();
    expect(screen.queryByText(/storage_uri/)).not.toBeInTheDocument();
  });

  test('renders the description when present', () => {
    render(
      <EvidenceItem
        evidence={{
          id: '1',
          original_filename: 'x.pdf',
          verified_at: null,
          uploaded_at: '2026-05-01T00:00:00Z',
          description: 'Facture Engie Q3',
        }}
      />
    );
    expect(screen.getByText('Facture Engie Q3')).toBeInTheDocument();
  });

  test('renders the file size formatted in FR units', () => {
    render(
      <EvidenceItem
        evidence={{
          id: '1',
          original_filename: 'x.pdf',
          verified_at: null,
          uploaded_at: '2026-05-01T00:00:00Z',
          file_size_bytes: 2 * 1024 * 1024,
        }}
      />
    );
    // fmtNum formate en locale FR → séparateur décimal virgule.
    expect(screen.getByText(/2,0 Mo/)).toBeInTheDocument();
  });
});
