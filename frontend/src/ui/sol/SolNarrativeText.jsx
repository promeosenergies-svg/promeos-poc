/**
 * SolNarrativeText — wrap automatique des acronymes du GLOSSARY dans un texte.
 *
 * Sprint 2 Vague H (post-audit Vague G P2 #1) : permet de glosser
 * automatiquement les acronymes connus dans tout texte narratif (briefs
 * CODIR, descriptions Site360, narratives Flex/Achat, etc.) sans
 * refactoriser le code amont qui produit le texte.
 *
 * Algorithme :
 *   1. Construit une regex à partir des clés du GLOSSARY (sorted by length
 *      descendant pour matcher « Décret Tertiaire » avant « DT »)
 *   2. Split le texte sur cette regex en gardant les groupes
 *   3. Pour chaque match, rend `<SolAcronym>` ; sinon texte brut
 *   4. Préserve les retours à la ligne via `whitespace-pre-wrap`
 *
 * Usage :
 *   <SolNarrativeText text="Notre score Décret Tertiaire est..." />
 *
 * Performance : regex compilée une seule fois (memo module-level).
 * Side-effect-free, idempotent, safe pour rendu serveur.
 */
import { useMemo } from 'react';
import SolAcronym from './SolAcronym';
import { GLOSSARY } from '../../domain/glossary';

// Regex compilée une seule fois — clés triées par longueur descendante pour
// matcher « Décret Tertiaire » avant « DT » (greedy ne suffirait pas car
// l'alternation regex est gauche→droite, pas longest-match).
const GLOSSARY_KEYS = Object.keys(GLOSSARY).sort((a, b) => b.length - a.length);

// Échappement des caractères spéciaux regex dans les clés (ex: « / », « . »).
function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Capture la position des matches : `\b` aux bords pour éviter de matcher
// dans un mot (ex: ne pas glosser « bacs » dans « bacsim »). Insensible
// au plural (acronymes invariables).
const ACRONYM_PATTERN = new RegExp(`\\b(${GLOSSARY_KEYS.map(escapeRegex).join('|')})\\b`, 'g');

export default function SolNarrativeText({ text, className = '' }) {
  const segments = useMemo(() => {
    if (!text || typeof text !== 'string') return [];
    // String.split avec capture group → garde les acronymes dans l'array.
    // [text_avant, acronyme1, text_après, acronyme2, ...]
    const parts = text.split(ACRONYM_PATTERN);
    return parts;
  }, [text]);

  if (!text) return null;

  return (
    <span className={`whitespace-pre-wrap ${className}`}>
      {segments.map((segment, idx) => {
        // Indices impairs = acronymes capturés ; pairs = texte brut entre.
        if (idx % 2 === 1 && GLOSSARY[segment]) {
          return <SolAcronym key={idx} code={segment} />;
        }
        return segment;
      })}
    </span>
  );
}
