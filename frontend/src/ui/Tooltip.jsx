/**
 * PROMEOS Design System — Tooltip (backward-compatible wrapper)
 *
 * Delegates to TooltipPortal (portal-based, z-[120]) to avoid clipping
 * by ancestor overflow-hidden / backdrop-blur stacking contexts.
 *
 * Accepts both `text` and `content` props for backward compatibility.
 * If resolved text is empty → renders children only (no tooltip DOM).
 */
import TooltipPortal from './TooltipPortal';

export default function Tooltip({ text, content, children, position = 'top', className = '' }) {
  const resolved = text ?? content ?? '';
  const trimmed = typeof resolved === 'string' ? resolved.trim() : resolved;

  // Guard: no text → render children as-is, no invisible tooltip bubble
  if (!trimmed) return <span className={`inline-flex ${className}`}>{children}</span>;

  return (
    <TooltipPortal text={trimmed} position={position} className={className}>
      {children}
    </TooltipPortal>
  );
}
