/**
 * PROMEOS Design System — Explain (C.1)
 * Composant inline pédagogique : souligne un terme et affiche sa définition au survol.
 *
 * Usage :
 *   <Explain term="turpe" />            — affiche "TURPE" (label du glossaire)
 *   <Explain term="turpe">TURPE HTA</Explain>  — affiche "TURPE HTA" (texte custom)
 *   <Explain term="turpe" content="Def custom" />  — définition custom
 *
 * Props :
 *   term      : string — clé dans GLOSSARY (ex: "turpe", "shadow_billing")
 *   content   : string — définition custom (prioritaire sur glossary)
 *   children  : ReactNode — texte affiché (sinon glossary.term)
 *   position  : 'top'|'bottom' — position du tooltip (défaut: top)
 *   className : string
 */
import { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { GLOSSARY } from './glossary';
// Phase 22.3 — fallback vers SoT canonique si terme absent du glossaire legacy.
import { acronymTooltip as _soTooltip, isKnownAcronym as _soIsKnown } from '../utils/acronyms';

const DELAY_MS = 150;
const OFFSET = 6;
const MAX_W = 320;

export default function Explain({ term, content, children, position = 'top', className = '' }) {
  const entry = term ? GLOSSARY[term] : null;
  const label = children || (entry && entry.term) || term;
  // Phase 22.3 : si pas dans GLOSSARY legacy, on tente le SoT canonique.
  // Bénéfice : 5 consumers Explain (DataQualityBadge, ConformiteCard…) ont
  // désormais accès aux 45 acronymes du SoT (CRE/RTE/ATRD/CSRD/etc.).
  let definition = content || (entry && entry.short);
  if (!definition && term) {
    const sotKey = String(term).split(/\s+/)[0]?.toUpperCase();
    if (_soIsKnown(sotKey)) {
      definition = _soTooltip(sotKey);
    }
  }

  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState(null);
  const triggerRef = useRef(null);
  const timerRef = useRef(null);
  const tooltipId = useRef(`ex-${Math.random().toString(36).slice(2)}`);

  const show = useCallback(() => {
    if (!definition) return;
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (triggerRef.current) {
        const rect = triggerRef.current.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const vw = typeof window !== 'undefined' ? window.innerWidth : 1280;
        const vh = typeof window !== 'undefined' ? window.innerHeight : 800;

        let top, transform;
        if (position === 'bottom') {
          top = Math.min(rect.bottom + OFFSET, vh - 80);
          transform = 'translateX(-50%)';
        } else {
          top = Math.max(rect.top - OFFSET, 8);
          transform = 'translate(-50%, -100%)';
        }

        setCoords({
          top,
          left: Math.max(8, Math.min(cx, vw - MAX_W / 2 - 8)),
          transform,
        });
      }
      setVisible(true);
    }, DELAY_MS);
  }, [definition, position]);

  const hide = useCallback(() => {
    clearTimeout(timerRef.current);
    setVisible(false);
  }, []);

  useEffect(() => () => clearTimeout(timerRef.current), []);

  if (!definition) return <span className={className}>{label}</span>;

  return (
    <>
      <span
        ref={triggerRef}
        role="term"
        tabIndex={0}
        aria-describedby={visible ? tooltipId.current : undefined}
        data-testid="explain"
        data-glossary={term || undefined}
        className={`cursor-help border-b border-dotted border-gray-400 hover:border-blue-500
          hover:text-blue-700 transition-colors ${className}`}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        {label}
      </span>

      {visible &&
        coords &&
        createPortal(
          <div
            id={tooltipId.current}
            role="tooltip"
            className="fixed pointer-events-none z-[120]"
            style={{ top: coords.top, left: coords.left, transform: coords.transform }}
          >
            <div
              className="max-w-[320px] px-3 py-2 text-xs text-gray-700 leading-relaxed
                bg-white border border-gray-200 rounded-lg shadow-lg"
            >
              {entry && <span className="font-semibold text-gray-900">{entry.term} — </span>}
              {definition}
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
