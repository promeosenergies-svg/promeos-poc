/**
 * grammar/AutoTerm — Tokeniseur de chaîne avec auto-wrap des acronymes connus.
 *
 * Sprint Grammaire v1.2 / Phase 3.4 / Phase F.5 — résout les critères audit
 * 1.4 (vocabulaire acronymes sans tooltip) et 3.8 (tooltip natif HTML au lieu
 * de Tooltip Sol) pour les chaînes rendues depuis le payload backend
 * (`hero.title`, `hero.sub`, `kpi.label`, `highlight.evidence`, etc.).
 *
 * Cas d'usage cible :
 *   <SolHeroPremiumNight title={<AutoTerm text={hero.title} />} />
 *   <HubHighlight evidence={<AutoTerm text={highlight.evidence} />} />
 *
 * Tokenisation : régex dynamique générée depuis le dictionnaire backend
 * (useAcronymes) — la SoT YAML acronymes_doctrine.yaml est l'autorité.
 *
 *   "Site assujetti au décret BACS" →
 *     [ "Site assujetti au décret ", <Term acronyme="BACS"/> ]
 *
 * Performance : la regex est mémoisée par référence du dictionnaire backend
 * (rebuild seulement si le dict change — cas rare : 1 fois au mount).
 *
 * Fallback : si le hook n'a pas chargé (loading) ou retourne un dict vide
 * (erreur réseau), le texte est rendu tel quel (defensive null-render).
 *
 * Source-guards : `data-component="AutoTerm"` `data-acronyms-count` (nombre
 * d'acronymes wrappés dans le texte).
 *
 * @typedef {Object} AutoTermProps
 * @property {string} text       - Texte source à tokeniser
 * @property {'preserve-text'|'inline-tooltip'|'short'|'narrative'} [variant='preserve-text']
 *   Variant passé à <Term>. Default = 'preserve-text' (Phase F.5.1) : préserve
 *   la clé brute pour éviter le doublon de mots (eg "le décret BACS" → "le
 *   décret Décret BACS" si BACS.short = "Décret BACS"). Utiliser 'inline-tooltip'
 *   uniquement si le rendu standalone est souhaité (sans contexte de phrase).
 * @property {string} [className='']
 *
 * @param {AutoTermProps} props
 */
import { useMemo } from 'react';
import { useAcronymes } from '../../hooks/useAcronymes';
import Term from './Term';

/** Cache module-scope de la régex compilée par référence du dict.
 *  Map<dictRef, RegExp>. Garbage-collected si le dict change (Map clé = WeakRef-like).
 */
const _regexCache = new WeakMap();

function buildAcronymRegex(dict) {
  if (!dict || typeof dict !== 'object') return null;
  const cached = _regexCache.get(dict);
  if (cached) return cached;
  const keys = Object.keys(dict).filter((k) => /^[A-Z][A-Z0-9]+$/.test(k));
  if (keys.length === 0) return null;
  // Trie par longueur décroissante pour matcher "TURPE" avant "TUR" (greedy correct).
  keys.sort((a, b) => b.length - a.length);
  const escaped = keys.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  // Word-boundary strict : on ne wrap PAS "BACS" dans "BACSeed" ou "TURPEbar".
  const pattern = new RegExp(`\\b(${escaped.join('|')})\\b`, 'g');
  _regexCache.set(dict, pattern);
  return pattern;
}

export default function AutoTerm({ text, variant = 'preserve-text', className = '' }) {
  const { data: dict } = useAcronymes();

  const segments = useMemo(() => {
    if (typeof text !== 'string' || text.length === 0) return null;
    const pattern = buildAcronymRegex(dict);
    if (!pattern) return [{ kind: 'text', value: text }];
    const out = [];
    let lastIndex = 0;
    pattern.lastIndex = 0;
    let match;
    while ((match = pattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        out.push({ kind: 'text', value: text.slice(lastIndex, match.index) });
      }
      out.push({ kind: 'acronym', value: match[1] });
      lastIndex = match.index + match[1].length;
    }
    if (lastIndex < text.length) {
      out.push({ kind: 'text', value: text.slice(lastIndex) });
    }
    return out;
  }, [text, dict]);

  if (!segments) return null;
  const acronymCount = segments.filter((s) => s.kind === 'acronym').length;

  return (
    <span data-component="AutoTerm" data-acronyms-count={acronymCount} className={className}>
      {segments.map((s, i) =>
        s.kind === 'text' ? (
          // eslint-disable-next-line react/no-array-index-key -- segments are positional,
          // index is the only stable key (text content can repeat across the string).
          <span key={`t-${i}`}>{s.value}</span>
        ) : (
          // eslint-disable-next-line react/no-array-index-key -- même raison
          <Term key={`a-${i}`} acronyme={s.value} variant={variant} />
        )
      )}
    </span>
  );
}
