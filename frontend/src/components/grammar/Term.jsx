/**
 * grammar/Term — Acronyme avec tooltip narratif riche (primitif grammaire §6.4).
 *
 * Consomme le hook `useAcronymes` (Phase 1.1) si disponible.
 * Si le hook n'existe pas encore, utilise le glossaire statique
 * `utils/acronyms.js` + `domain/glossary.js` en fallback stand-alone.
 *
 * Comportement par variant :
 *   - 'inline-tooltip' (defaut) : acronyme avec tooltip accessible via SolTooltip
 *   - 'narrative' : forme longue + "(short)" en texte simple
 *   - 'short' : forme courte seulement
 *
 * Si chargement : rend l'acronyme brut.
 * Si inconnu : rend l'acronyme brut + console.warn en dev.
 *
 * @param {Object} props
 * @param {string} props.acronyme - Code acronyme (ex. "BACS", "TURPE")
 * @param {'inline-tooltip'|'narrative'|'short'} [props.variant='inline-tooltip'] - Mode de rendu
 * @param {string} [props.className=''] - Classes CSS supplementaires
 */
import SolTooltip from '../../ui/sol/SolTooltip';
import { acronymTooltip, isKnownAcronym } from '../../utils/acronyms';
import { GLOSSARY } from '../../domain/glossary';
import { useAcronymes } from '../../hooks/useAcronymes';

/**
 * Resout depuis le SoT YAML backend (Phase 1.1) charge via useAcronymes.
 * Le payload backend a la structure {short, long, narrative, source, ...}.
 */
function resolveFromBackend(dict, code) {
  if (!dict || !code) return null;
  const key = code.toUpperCase();
  const entry = dict[key];
  if (!entry) return null;
  return {
    short: entry.short || key,
    long: entry.long || key,
    narrative: entry.narrative || entry.long || '',
    source: entry.source || null,
  };
}

/**
 * Resout un acronyme vers ses champs (long, short, narrative, source).
 * Cascade : backend YAML SoT -> utils/acronyms.js -> domain/glossary.js.
 * Retourne null si inconnu.
 */
function resolveAcronyme(code, backendDict) {
  if (!code) return null;
  const key = code.toUpperCase();

  // Priorite 1 : YAML SoT backend (Phase 1.1) — autorite reglementaire avec
  // sources legales tracees (CRE, JORFTEXT, decret, NOR).
  const backendHit = resolveFromBackend(backendDict, key);
  if (backendHit) return backendHit;

  // Priorite 2 : utils/acronyms.js (ACRONYM_GLOSSARY avec long/meaning/source)
  if (isKnownAcronym(key)) {
    const tooltip = acronymTooltip(key);
    return { short: key, long: key, narrative: tooltip, source: null };
  }

  // Priorite 3 : domain/glossary.js (fallback final)
  const glossEntry = GLOSSARY[key] || GLOSSARY[code];
  if (glossEntry) {
    const narrative =
      typeof glossEntry === 'string'
        ? glossEntry
        : glossEntry.short || glossEntry.term || String(glossEntry);
    const long = typeof glossEntry === 'object' && glossEntry.term ? glossEntry.term : key;
    return { short: key, long, narrative, source: null };
  }

  return null;
}

export default function Term({ acronyme, variant = 'inline-tooltip', className = '' }) {
  // Hook useAcronymes (Phase 1.1) — cache module-scope, 1 fetch / session.
  // Si la SoT backend n'est pas encore chargee (loading) ou indisponible
  // (erreur reseau), Term tombe sur le fallback statique sans bloquer.
  const { data: backendDict } = useAcronymes();
  const resolved = resolveAcronyme(acronyme, backendDict);

  // Acronyme inconnu : rendu brut + warn en dev
  if (!resolved) {
    if (typeof process !== 'undefined' && process.env?.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.warn(
        `[grammar/Term] Acronyme inconnu : "${acronyme}" — pas de definition dans le glossaire.`
      );
    }
    return (
      <span data-testid="term-unknown" className={className}>
        {acronyme}
      </span>
    );
  }

  if (variant === 'short') {
    return (
      <span data-testid="term-short" className={className}>
        {resolved.short}
      </span>
    );
  }

  if (variant === 'narrative') {
    return (
      <span data-testid="term-narrative" className={className}>
        {resolved.narrative}
        {resolved.short && resolved.short !== resolved.narrative && <> ({resolved.short})</>}
      </span>
    );
  }

  // variant 'inline-tooltip' (defaut) — delegue a SolTooltip pour WCAG 1.4.13
  return (
    <SolTooltip content={resolved.narrative} className={className}>
      <span data-testid="term-inline" aria-label={resolved.long}>
        {resolved.short}
      </span>
    </SolTooltip>
  );
}
