// @vitest-environment jsdom
/**
 * Tests render P2-A simplification visuelle Conformité (2026-05-25).
 *
 * Vérifie :
 * 1. Les 4 cartes ATF sont rendues avec leurs testids.
 * 2. Le score affiche le bon code couleur selon seuil.
 * 3. La pénalité « à qualifier » est rendue si null (pas "0 €").
 * 4. Le libellé périmètre « X sites évalués sur Y » est rendu seulement
 *    si scope et périmètre divergent.
 * 5. CTAs Plan / Compléter ne sont visibles que si counts > 0.
 * 6. Subtitle score actionnable (« N actions prioritaires à traiter »).
 */
import '@testing-library/jest-dom/vitest';
import React from 'react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';

// Mock Explain — il dépend d'un contexte glossary qui n'est pas chargé en
// test isolé. On garde le label visible (children) sans le tooltip.
vi.mock('../../../ui', () => ({
  Explain: ({ children }) => <span>{children}</span>,
}));

import ConformiteSyntheseCompacte from '../ConformiteSyntheseCompacte';

afterEach(() => cleanup());

const baseScore = { pct: 36, pct_confidence: 'medium', total_impact_eur: null };
const baseDeadline = { deadline: '2026-09-30', days_remaining: 128, label: 'OPERAT 2025' };

describe('ConformiteSyntheseCompacte — rendu 4 cartes ATF', () => {
  it('rend les 4 cartes attendues', () => {
    render(
      <ConformiteSyntheseCompacte
        score={baseScore}
        nextDeadline={baseDeadline}
        actionsCount={3}
        proofsMissingCount={2}
        sitesEvalues={5}
        sitesPerimetre={13}
        onOpenTab={() => {}}
      />
    );
    expect(screen.getByTestId('synthese-card-score')).toBeInTheDocument();
    expect(screen.getByTestId('synthese-card-echeance')).toBeInTheDocument();
    expect(screen.getByTestId('synthese-card-actions')).toBeInTheDocument();
    expect(screen.getByTestId('synthese-card-preuves')).toBeInTheDocument();
  });

  it('affiche le score avec /100 (formaté humainement)', () => {
    render(<ConformiteSyntheseCompacte score={baseScore} nextDeadline={null} />);
    const card = screen.getByTestId('synthese-card-score');
    expect(card).toHaveTextContent('36');
    expect(card).toHaveTextContent('/100');
  });

  it('utilise le rouge si score < 50', () => {
    render(<ConformiteSyntheseCompacte score={{ ...baseScore, pct: 36 }} nextDeadline={null} />);
    const cardHtml = screen.getByTestId('synthese-card-score').innerHTML;
    expect(cardHtml).toContain('text-red-600');
  });

  it("utilise l'ambre si 50 <= score < 70", () => {
    render(<ConformiteSyntheseCompacte score={{ ...baseScore, pct: 60 }} nextDeadline={null} />);
    const cardHtml = screen.getByTestId('synthese-card-score').innerHTML;
    expect(cardHtml).toContain('text-amber-600');
  });

  it("utilise l'émeraude si score >= 70", () => {
    render(<ConformiteSyntheseCompacte score={{ ...baseScore, pct: 85 }} nextDeadline={null} />);
    const cardHtml = screen.getByTestId('synthese-card-score').innerHTML;
    expect(cardHtml).toContain('text-emerald-600');
  });

  it('affiche "Données à compléter" si score null', () => {
    render(
      <ConformiteSyntheseCompacte
        score={{ pct: null, pct_confidence: 'low', total_impact_eur: null }}
        nextDeadline={null}
      />
    );
    expect(screen.getByTestId('synthese-card-score')).toHaveTextContent(/Données à compléter/);
  });

  it('rend le subtitle actionnable "Score faible — N actions prioritaires" si pct < 50', () => {
    render(<ConformiteSyntheseCompacte score={baseScore} nextDeadline={null} actionsCount={3} />);
    expect(screen.getByTestId('synthese-card-score')).toHaveTextContent(
      /Score faible.*3 actions prioritaires.*à traiter/
    );
  });
});

describe('Carte 2 — Prochaine échéance', () => {
  it('rend date FR + jours restants + libellé obligation', () => {
    render(<ConformiteSyntheseCompacte score={baseScore} nextDeadline={baseDeadline} />);
    const card = screen.getByTestId('synthese-card-echeance');
    expect(card).toHaveTextContent('30 septembre 2026');
    expect(card).toHaveTextContent('dans 128 jours');
    expect(card).toHaveTextContent('OPERAT 2025');
  });

  it('rend message de fallback si aucune échéance', () => {
    render(<ConformiteSyntheseCompacte score={baseScore} nextDeadline={null} />);
    expect(screen.getByTestId('synthese-card-echeance')).toHaveTextContent(
      /Aucune échéance proche/
    );
  });
});

describe('Carte 3 — Actions prioritaires', () => {
  it('affiche le count + CTA "Voir le plan" si actionsCount > 0', () => {
    const onOpenTab = vi.fn();
    render(
      <ConformiteSyntheseCompacte
        score={baseScore}
        nextDeadline={null}
        actionsCount={5}
        onOpenTab={onOpenTab}
      />
    );
    expect(screen.getByTestId('synthese-card-actions')).toHaveTextContent('5');
    const cta = screen.getByTestId('synthese-cta-actions');
    expect(cta).toBeInTheDocument();
    cta.click();
    expect(onOpenTab).toHaveBeenCalledWith('execution');
  });

  it('masque CTA "Voir le plan" si actionsCount = 0', () => {
    render(
      <ConformiteSyntheseCompacte
        score={baseScore}
        nextDeadline={null}
        actionsCount={0}
        onOpenTab={() => {}}
      />
    );
    expect(screen.queryByTestId('synthese-cta-actions')).not.toBeInTheDocument();
    expect(screen.getByTestId('synthese-card-actions')).toHaveTextContent(/Aucune action requise/);
  });
});

describe('Carte 4 — Preuves manquantes + risque financier', () => {
  it('affiche "à qualifier" si total_impact_eur null (pas "0 €")', () => {
    render(
      <ConformiteSyntheseCompacte
        score={{ ...baseScore, total_impact_eur: null }}
        nextDeadline={null}
        proofsMissingCount={0}
      />
    );
    const card = screen.getByTestId('synthese-card-preuves');
    expect(card).toHaveTextContent(/à qualifier/);
    expect(card).not.toHaveTextContent(/^0\s*€/);
  });

  it('affiche le montant € formaté FR si pénalité calculée', () => {
    render(
      <ConformiteSyntheseCompacte
        score={{ ...baseScore, total_impact_eur: 45000 }}
        nextDeadline={null}
      />
    );
    const card = screen.getByTestId('synthese-card-preuves');
    expect(card).toHaveTextContent('45 000 €');
  });

  it('CTA "Compléter" visible si proofsMissingCount > 0', () => {
    const onOpenTab = vi.fn();
    render(
      <ConformiteSyntheseCompacte
        score={baseScore}
        nextDeadline={null}
        proofsMissingCount={4}
        onOpenTab={onOpenTab}
      />
    );
    const cta = screen.getByTestId('synthese-cta-preuves');
    cta.click();
    expect(onOpenTab).toHaveBeenCalledWith('preuves');
  });
});

describe('Périmètre sites — X évalués sur Y', () => {
  it('affiche "5 sites évalués sur 13 dans le périmètre" si divergent', () => {
    render(
      <ConformiteSyntheseCompacte
        score={baseScore}
        nextDeadline={null}
        sitesEvalues={5}
        sitesPerimetre={13}
      />
    );
    expect(screen.getByTestId('synthese-perimetre')).toHaveTextContent(
      '5 sites évalués sur 13 dans le périmètre'
    );
  });

  it('affiche "13 sites dans le périmètre" si scope = total (pas de divergence)', () => {
    render(
      <ConformiteSyntheseCompacte
        score={baseScore}
        nextDeadline={null}
        sitesEvalues={13}
        sitesPerimetre={13}
      />
    );
    expect(screen.getByTestId('synthese-perimetre')).toHaveTextContent(
      '13 sites dans le périmètre'
    );
  });

  it('masque le label si périmètre = 0', () => {
    render(
      <ConformiteSyntheseCompacte
        score={baseScore}
        nextDeadline={null}
        sitesEvalues={0}
        sitesPerimetre={0}
      />
    );
    expect(screen.queryByTestId('synthese-perimetre')).not.toBeInTheDocument();
  });
});
