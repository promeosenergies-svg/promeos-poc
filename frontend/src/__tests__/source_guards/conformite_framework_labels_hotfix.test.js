/**
 * Source-guard hotfix 2026-05-24 — labels frameworks réglementaires.
 *
 * Garde-fou cardinal : ComplianceScoreHeader.jsx ne doit plus contenir
 * de fallback métier `: 'APER'` (bug pré-hotfix qui étiquetait audit_sme,
 * iso_50001, solar_toiture, beges comme APER).
 *
 * Doctrine §8.1 « zero business logic frontend » : le label code→FR est
 * métier réglementaire et doit venir du backend (`fw.label_fr`,
 * FRAMEWORK_LABELS_FR dans compliance_score_service.py).
 */
import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, it, expect } from 'vitest';

const ROOT = resolve(__dirname, '../../../');
const COMPONENT = resolve(ROOT, 'src/components/conformite/ComplianceScoreHeader.jsx');
const BACKEND_SERVICE = resolve(ROOT, '../backend/services/compliance_score_service.py');

/** Enleve commentaires JS pour éviter faux positifs sur la justification du fix. */
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

describe('ComplianceScoreHeader — anti-régression mapping fallback APER', () => {
  const src = readFileSync(COMPONENT, 'utf-8');
  const cleaned = stripComments(src);

  it("ne contient PLUS de fallback ternaire `: 'APER'` (bug pré-hotfix)", () => {
    // Match : `: 'APER'` ou `: "APER"` à la fin d'un ternaire (fallback).
    expect(cleaned).not.toMatch(/:\s*['"]APER['"]\s*[,;)]/);
    // Match : `? 'BACS' : 'APER'` (ancien pattern du bug)
    expect(cleaned).not.toMatch(/['"]BACS['"]\s*\n?\s*:\s*['"]APER['"]/);
  });

  it('ne contient PLUS de mapping ternaire framework→label (logique métier interdite)', () => {
    // Pattern interdit : `framework === 'X' ? 'LabelA' : ...`
    // (le mapping doit venir du backend `fw.label_fr`)
    expect(cleaned).not.toMatch(/framework\s*===\s*['"]tertiaire_operat['"]\s*\?\s*['"]/);
    expect(cleaned).not.toMatch(/fw\s*===\s*['"]tertiaire_operat['"]\s*\?\s*['"]/);
  });

  it('utilise fw.label_fr (label venant du backend)', () => {
    expect(cleaned).toMatch(/fw\.label_fr/);
  });

  it('définit un fallback NEUTRE `formatFrameworkCode` (sans logique métier)', () => {
    expect(cleaned).toMatch(/formatFrameworkCode/);
    // Le fallback doit s'appliquer aux deux blocs (breakdown + breakdown_avg)
    const matches = cleaned.match(/formatFrameworkCode\(fw\.framework\)/g) || [];
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it('formatFrameworkCode ne retourne JAMAIS un label métier hardcodé', () => {
    // Garde-fou : la fonction de format ne doit faire que du formatage
    // typographique (replace _, capitalize) — pas de mapping métier.
    const fnMatch = cleaned.match(/function formatFrameworkCode\([^)]*\)\s*\{([\s\S]*?)^\}/m);
    expect(fnMatch).not.toBeNull();
    const body = fnMatch[1];
    expect(body).not.toMatch(/['"]Décret Tertiaire['"]/);
    expect(body).not.toMatch(/['"]BACS['"]/);
    expect(body).not.toMatch(/['"]APER['"]/);
    expect(body).not.toMatch(/['"]Audit SM/);
    expect(body).not.toMatch(/['"]ISO 50001['"]/);
    expect(body).not.toMatch(/['"]BEGES['"]/);
  });
});

describe('Backend FRAMEWORK_LABELS_FR — SoT exhaustivité', () => {
  // On lit le service backend en clair pour vérifier que tous les codes
  // émis par _compute_v2_adaptive ont bien un label FR.
  let backendSrc = '';
  try {
    backendSrc = readFileSync(BACKEND_SERVICE, 'utf-8');
  } catch {
    // Si le backend n'est pas accessible depuis le contexte FE tests,
    // on skip ce describe (sera couvert par les tests backend).
  }

  it('FRAMEWORK_LABELS_FR contient les 7 frameworks attendus', () => {
    if (!backendSrc) return;
    expect(backendSrc).toMatch(/FRAMEWORK_LABELS_FR/);
    for (const code of [
      'tertiaire_operat',
      'bacs',
      'aper',
      'audit_sme',
      'iso_50001',
      'solar_toiture',
      'beges',
    ]) {
      expect(backendSrc).toMatch(new RegExp(`["']${code}["']\\s*:`));
    }
  });

  it('aucun code framework V2 sans label_fr (audit_sme, iso_50001, solar_toiture)', () => {
    if (!backendSrc) return;
    // Ces 3 codes étaient le cœur du bug : ils doivent maintenant avoir
    // un label_fr explicite dans FRAMEWORK_LABELS_FR.
    expect(backendSrc).toMatch(/["']audit_sme["']\s*:\s*["']Audit SMÉ["']/);
    expect(backendSrc).toMatch(/["']iso_50001["']\s*:\s*["']ISO 50001["']/);
    expect(backendSrc).toMatch(/["']solar_toiture["']\s*:\s*["']Solarisation toiture["']/);
  });
});
