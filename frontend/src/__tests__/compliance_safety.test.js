/**
 * PROMEOS — Tests securite conformite
 * Verifie que l'UI ne cree jamais un faux sentiment de conformite.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const src = join(__dirname, '..');
const read = (p) => (existsSync(p) ? readFileSync(p, 'utf-8') : '');

const LABELS_SRC = read(join(src, 'domain', 'compliance', 'complianceLabels.fr.js'));
const EXPORT_SRC = read(join(src, 'components', 'ExportOperatModal.jsx'));
const EFA_SRC = read(join(src, 'pages', 'tertiaire', 'TertiaireEfaDetailPage.jsx'));

// ── A. Export OPERAT ne simule jamais un depot reel ──────────────────

describe('ExportOperatModal — securite simulation', () => {
  test('contient un banner avertissement simulation', () => {
    expect(EXPORT_SRC).toMatch(/aucun depot.*reel|Simulation.*depot/i);
  });

  test('le titre contient "preparation" ou "preparatoire"', () => {
    expect(EXPORT_SRC).toMatch(/title=.*[Pp]repara/);
  });

  test('le bouton telecharger mentionne "preparatoire"', () => {
    expect(EXPORT_SRC).toMatch(/preparatoire/);
  });
});

// ── B. EFA Detail Page — garde-fous OPERAT ──────────────────────────

describe('TertiaireEfaDetailPage — securite OPERAT', () => {
  test('contient un banner aide a la conformite', () => {
    expect(EFA_SRC).toMatch(/[Aa]ide a la conformite|[Pp]reparation.*dossier/);
  });

  test('mentionne operat.ademe.fr pour le depot reel', () => {
    expect(EFA_SRC).toMatch(/operat\.ademe\.fr/);
  });

  test('le bouton export dit "preparatoire" pas "exporter le pack"', () => {
    expect(EFA_SRC).toMatch(/[Pp]ack preparatoire|[Gg]enerer le pack/);
  });
});

// ── C. Labels centralises — pas de faux statut conforme ─────────────

describe('complianceLabels.fr.js — garde-fous statuts', () => {
  test('contient le statut "evaluation_incomplete"', () => {
    expect(LABELS_SRC).toMatch(/evaluation_incomplete/);
  });

  test('contient le statut "classe_a_verifier"', () => {
    expect(LABELS_SRC).toMatch(/classe_a_verifier/);
  });

  test('contient le statut "preuves_non_tracables"', () => {
    expect(LABELS_SRC).toMatch(/preuves_non_tracables/);
  });

  test('contient CONFORMITE_WARNINGS avec operat_simulation', () => {
    expect(LABELS_SRC).toMatch(/CONFORMITE_WARNINGS/);
    expect(LABELS_SRC).toMatch(/operat_simulation/);
  });

  test('contient DECLARATION_STATUS_LABELS avec "Simulation non déposée"', () => {
    expect(LABELS_SRC).toMatch(/DECLARATION_STATUS_LABELS/);
    expect(LABELS_SRC).toMatch(/Simulation non déposée/);
  });

  test('DECLARATION_STATUS_LABELS mappe "exported" en "Pack préparatoire généré"', () => {
    expect(LABELS_SRC).toMatch(/exported.*Pack pr[ée]paratoire/);
  });
});
