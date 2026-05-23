// @vitest-environment jsdom
/**
 * M2-5.3.A / M2-5.8.B / M2-5.10.A — Tests d'`ItemsTable` (rendu jsdom).
 *
 * Restyle Sol M2-5.10.A : 5 colonnes (Classement · Item · État · Domaine ·
 * Priorité). La colonne « Mis à jour » est retirée (absente de la maquette
 * §8.3) — la date reste dans le drawer détail. Le `kind` est rendu en MONO
 * uppercase (ANOMALIE / ACTION / DÉCISION / SIGNAL / PREUVE / ÉCHÉANCE /
 * RECO).
 */
import '@testing-library/jest-dom/vitest';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';

import { ItemsTable } from '../components/ItemsTable';

afterEach(cleanup);

const noop = () => {};

const sampleItems = [
  {
    id: 'item-1',
    title: 'Vérifier consommation HP/HC Q3',
    kind: 'anomaly',
    priority_bracket: 'P1',
    priority_score: 73,
    lifecycle_state: 'triaged',
    domain: 'conformite',
  },
  {
    id: 'item-2',
    title: 'Déclaration OPERAT 2026',
    kind: 'deadline',
    priority_bracket: 'P2',
    priority_score: 55,
    lifecycle_state: 'planned',
    domain: 'facturation',
  },
];

describe('ItemsTable', () => {
  test('renders one row per item', () => {
    render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    expect(screen.getByText('Vérifier consommation HP/HC Q3')).toBeInTheDocument();
    expect(screen.getByText('Déclaration OPERAT 2026')).toBeInTheDocument();
  });

  test('renders a lifecycle badge per row', () => {
    render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    expect(screen.getByText('Trié')).toBeInTheDocument();
    expect(screen.getByText('Planifié')).toBeInTheDocument();
  });

  test('renders no body row for an empty array', () => {
    const { container } = render(<ItemsTable items={[]} onOpenItem={noop} />);
    expect(container.querySelectorAll('tbody tr').length).toBe(0);
  });

  test('rows carry cursor-pointer (clickable affordance)', () => {
    const { container } = render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    const rows = container.querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
    rows.forEach((tr) => expect(tr.className).toContain('cursor-pointer'));
  });

  test('clicking a row calls onOpenItem with the item', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sampleItems} onOpenItem={onOpenItem} />);
    // M2-6.C.P2-cleanup P2-6 — sélection par rôle a11y (le <tr> porte
    // `role="button"` + aria-label `Ouvrir l'action : <title>`) au lieu de
    // `.closest('tr')` couplé au markup table. Résiste à un refacto futur
    // de structure (table → div role="grid", etc.).
    fireEvent.click(
      screen.getByRole('button', { name: /ouvrir l'action.*vérifier consommation hp\/hc q3/i })
    );
    expect(onOpenItem).toHaveBeenCalledWith(sampleItems[0]);
  });

  // ── M2-5.10.A → M2-5.11.E — 7 colonnes (Classement / Item / État /
  //    Domaine / € / Pilote / Priorité — BACKLOG_M3 CFO + owner traité) ─
  test('renders exactly 7 column headers (Classement / Item / État / Domaine / € / Pilote / Priorité)', () => {
    const { container } = render(<ItemsTable items={sampleItems} onOpenItem={noop} />);
    const ths = container.querySelectorAll('thead th');
    expect(ths.length).toBe(7);
    // « Mis à jour » a été retirée (drawer détail le porte).
    expect(container.querySelector('thead')).not.toHaveTextContent('Mis à jour');
    // Colonne € (M2-5.11.D → M2-6.B.frontend renommée « Impact estimé »,
    // source `estimated_impact_euros` scalaire vs ancien `impact_at_risk_eur`)
    // + Pilote (M2-5.11.E) présentes.
    expect(container.querySelector('thead')).toHaveTextContent(/impact estimé/i);
    expect(container.querySelector('thead')).toHaveTextContent(/pilote/i);
  });

  // ── M2-5.11.E — colonne Pilote (owner_display_name) ───────────────────
  test('renders the owner display name when item.owner_display_name is set', () => {
    const items = [
      {
        id: 'own1',
        title: 'Avec pilote',
        kind: 'anomaly',
        priority_bracket: 'P0',
        priority_score: 90,
        lifecycle_state: 'new',
        domain: 'energie',
        owner_id: '11111111-2222-3333-4444-555555555555',
        owner_display_name: 'J. Martin',
      },
    ];
    render(<ItemsTable items={items} onOpenItem={noop} />);
    expect(screen.getByText('J. Martin')).toBeInTheDocument();
  });

  test('renders « Non assigné » when owner_display_name is null', () => {
    const items = [
      {
        id: 'own2',
        title: 'Sans pilote',
        kind: 'action',
        priority_bracket: 'P2',
        priority_score: 50,
        lifecycle_state: 'new',
        domain: 'energie',
        owner_id: null,
        owner_display_name: null,
      },
    ];
    render(<ItemsTable items={items} onOpenItem={noop} />);
    expect(screen.getByText(/non assigné/i)).toBeInTheDocument();
  });

  // ── M2-6.B.frontend — rendu cellule « Impact estimé » ──────────────
  // (remplace ancien test sur `impact_at_risk_eur` — la colonne consomme
  // désormais `estimated_impact_euros`, format `formatEurosColumn`)
  test('renders the € amount in full mode when estimated_impact_euros < 10k', () => {
    const items = [
      {
        id: '€1',
        title: 'Vedette < 10k',
        kind: 'anomaly',
        priority_bracket: 'P0',
        priority_score: 90,
        lifecycle_state: 'new',
        domain: 'energie',
        estimated_impact_euros: 7500,
      },
    ];
    const { container } = render(<ItemsTable items={items} onOpenItem={noop} />);
    // formatEurosColumn(7500) → "7 500 €" (full, sous seuil 10k).
    // `\s` matche U+202F narrow no-break space (séparateur milliers FR).
    expect(container.textContent).toMatch(/7\s?500\s?€/);
  });

  test('renders the € amount in compact mode when estimated_impact_euros >= 10k', () => {
    const items = [
      {
        id: '€2',
        title: 'Renouvellement contrat',
        kind: 'decision',
        priority_bracket: 'P2',
        priority_score: 54,
        lifecycle_state: 'planned',
        domain: 'purchase',
        estimated_impact_euros: 35000,
      },
    ];
    const { container } = render(<ItemsTable items={items} onOpenItem={noop} />);
    // formatEurosColumn(35000) → "35 k€" (compact ≥ 10k).
    expect(container.textContent).toMatch(/35\s?k€/);
  });

  test('renders « — » when estimated_impact_euros is null (NULL strict)', () => {
    const items = [
      {
        id: '€3',
        title: 'Sans chiffre',
        kind: 'action',
        priority_bracket: 'P2',
        priority_score: 50,
        lifecycle_state: 'new',
        domain: 'energie',
        estimated_impact_euros: null,
      },
    ];
    const { container } = render(<ItemsTable items={items} onOpenItem={noop} />);
    expect(container.textContent).toContain('—');
  });
});

describe('ItemsTable — a11y clavier + priorité + kind FR (M2-5.8.B)', () => {
  const sample = [
    {
      id: 'a',
      title: 'Vérifier HP/HC',
      kind: 'anomaly',
      priority_bracket: 'P0',
      priority_score: 92,
      lifecycle_state: 'new',
      domain: 'optimisation',
    },
  ];
  // M2-6.C.P2-cleanup P2-6 — sélection par rôle a11y (le <tr> porte
  // `role="button"` + aria-label `Ouvrir l'action : <title>`) au lieu de
  // `.closest('tr')` couplé au markup table.
  const rowOf = (title) =>
    screen.getByRole('button', { name: new RegExp(`ouvrir l'action.*${title}`, 'i') });

  test('a clickable row is focusable (tabindex=0)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC')).toHaveAttribute('tabindex', '0');
  });

  test('a clickable row carries role="button"', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC')).toHaveAttribute('role', 'button');
  });

  test('a clickable row carries an explicit aria-label', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC').getAttribute('aria-label')).toMatch(/ouvrir.*vérifier hp\/hc/i);
  });

  test('Enter on a row calls onOpenItem', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sample} onOpenItem={onOpenItem} />);
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: 'Enter' });
    expect(onOpenItem).toHaveBeenCalledWith(sample[0]);
  });

  test('Space on a row calls onOpenItem', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sample} onOpenItem={onOpenItem} />);
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: ' ' });
    expect(onOpenItem).toHaveBeenCalledWith(sample[0]);
  });

  test('other keys do not trigger onOpenItem', () => {
    const onOpenItem = vi.fn();
    render(<ItemsTable items={sample} onOpenItem={onOpenItem} />);
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: 'Escape' });
    fireEvent.keyDown(rowOf('Vérifier HP/HC'), { key: 'a' });
    expect(onOpenItem).not.toHaveBeenCalled();
  });

  test('a row carries the focus-visible ring class', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC').className).toMatch(/focus-visible:ring/);
  });

  test('renders the priority bracket and score (M2-5.10.A)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(screen.getByText('P0')).toBeInTheDocument();
    expect(screen.getByText('92')).toBeInTheDocument();
  });

  test('renders the kind label in FR uppercase (M2-5.10.A)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    // KindCell affiche le label MONO uppercase via KIND_LABELS_UPPER.
    expect(screen.getByText('ANOMALIE')).toBeInTheDocument();
    expect(screen.queryByText('anomaly')).not.toBeInTheDocument();
  });

  test('renders the domain in FR, not the raw backend value (M2-5.9.bis)', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    // DomainChip rend la valeur en mixed-case via DOMAIN_LABELS (chip MONO).
    expect(screen.getByText('Optimisation énergétique')).toBeInTheDocument();
    expect(screen.queryByText('optimisation')).not.toBeInTheDocument();
  });

  test('renders the upper FR label for all 7 backend kinds (M2-5.10.A)', () => {
    const items = [
      'anomaly',
      'action',
      'decision',
      'signal',
      'evidence_request',
      'deadline',
      'recommendation',
    ].map((kind, i) => ({
      id: `i${i}`,
      title: `T${i}`,
      kind,
      priority_bracket: 'P2',
      lifecycle_state: 'new',
    }));
    render(<ItemsTable items={items} onOpenItem={vi.fn()} />);
    ['ANOMALIE', 'ACTION', 'DÉCISION', 'SIGNAL', 'PREUVE', 'ÉCHÉANCE', 'RECO'].forEach((label) =>
      expect(screen.getByText(label)).toBeInTheDocument()
    );
  });

  test('falls back to "TYPE INCONNU" for an unknown kind (M2-5.10.A)', () => {
    const items = [
      {
        id: 'x',
        title: 'T',
        kind: 'invented_kind',
        priority_bracket: 'P2',
        lifecycle_state: 'new',
      },
    ];
    render(<ItemsTable items={items} onOpenItem={vi.fn()} />);
    expect(screen.getByText('TYPE INCONNU')).toBeInTheDocument();
  });

  // ── M2-5.10.A — strip vertical 3px couleur priorité (signature maquette) ──
  test('the row carries data-priority for the left strip rendering', () => {
    render(<ItemsTable items={sample} onOpenItem={vi.fn()} />);
    expect(rowOf('Vérifier HP/HC')).toHaveAttribute('data-priority', 'P0');
  });
});
