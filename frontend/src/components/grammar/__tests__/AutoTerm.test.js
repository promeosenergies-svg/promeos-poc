/**
 * grammar/AutoTerm — source-guards Vitest (Phase F.5)
 *
 * Pattern pure-grep readFileSync (env=node, aligne sur HubKpiCard.test.js).
 *
 * 7 tests couvrent :
 *   1. data-component="AutoTerm" + data-acronyms-count
 *   2. consume useAcronymes hook (dict backend SoT)
 *   3. compose <Term acronyme="..."/> pour chaque match
 *   4. regex word-boundary strict (\\b prevent "BACSeed")
 *   5. tri longueur decroissante (greedy correct : "TURPE" avant "TUR")
 *   6. defensive : null si text vide ou non-string
 *   7. JSDoc @typedef AutoTermProps + zero hex hardcoded
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = resolve(__dirname, '../AutoTerm.jsx');
const read = () => readFileSync(SRC, 'utf-8');

describe('grammar/AutoTerm', () => {
  it('AutoTerm.jsx existe sur disque', () => {
    expect(existsSync(SRC)).toBe(true);
  });

  it('data-component="AutoTerm" + data-acronyms-count poses au root', () => {
    const src = read();
    expect(src).toContain('data-component="AutoTerm"');
    expect(src).toContain('data-acronyms-count={acronymCount}');
  });

  it('consume useAcronymes hook (dict backend SoT)', () => {
    const src = read();
    expect(src).toContain("import { useAcronymes } from '../../hooks/useAcronymes'");
    expect(src).toContain('useAcronymes()');
  });

  it('compose <Term acronyme="..."/> pour chaque match', () => {
    const src = read();
    expect(src).toMatch(/import\s+Term\s+from\s+['"]\.\/Term['"]/);
    expect(src).toContain('acronyme={s.value}');
    expect(src).toContain('variant={variant}');
  });

  it("default variant='preserve-text' (Phase F.5.1 — eviter doublon mots)", () => {
    const src = read();
    // Phase F.5.1 — par defaut AutoTerm utilise Term variant='preserve-text'
    // qui affiche la cle brute (eg "BACS") au lieu de resolved.short (eg
    // "Décret BACS") pour eviter "le décret BACS" → "le décret Décret BACS".
    expect(src).toMatch(/variant\s*=\s*['"]preserve-text['"]/);
  });

  it('regex word-boundary strict + tri longueur decroissante (greedy correct)', () => {
    const src = read();
    // Word-boundary `\\b` autour de l'alternative — empeche les faux positifs
    // ("BACSeed", "TURPEbar"). On verifie la presence des fragments cles
    // dans la chaine source (pas le regex match exact pour eviter les
    // problemes d'escape multi-niveau).
    expect(src).toContain('\\\\b');
    expect(src).toContain("escaped.join('|')");
    expect(src).toContain('new RegExp');
    // Tri longueur decroissante pour matcher "TURPE" avant "TUR"
    expect(src).toMatch(/sort\(\(a,\s*b\)\s*=>\s*b\.length\s*-\s*a\.length\)/);
  });

  it('defensive : null si text vide ou non-string', () => {
    const src = read();
    expect(src).toContain("if (typeof text !== 'string' || text.length === 0) return null;");
    expect(src).toContain('if (!segments) return null;');
  });

  it('JSDoc @typedef AutoTermProps + zero hex hardcoded', () => {
    const src = read();
    expect(src).toContain('@typedef {Object} AutoTermProps');
    expect(src).toContain('@param {AutoTermProps} props');
    // Aucune couleur hex hardcodee
    expect(src).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    expect(src).not.toMatch(/#[0-9A-Fa-f]{3}\b/);
  });
});
