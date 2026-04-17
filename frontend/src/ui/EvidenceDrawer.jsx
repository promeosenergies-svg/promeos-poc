/**
 * PROMEOS Design System — EvidenceDrawer V0
 * Generic "Pourquoi ce chiffre ?" drawer.
 * Uses the reusable Drawer (z-[200], focus trap, ESC close).
 *
 * Props:
 *   open       {boolean}
 *   onClose    {fn}
 *   evidence   {Evidence}  — from ui/evidence.js
 */
import { useNavigate } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import Drawer from './Drawer';
import { CONFIDENCE_CFG, SOURCE_KIND } from './evidence';

function ConfidencePill({ level }) {
  const cfg = CONFIDENCE_CFG[level];
  if (!cfg) return null;
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-[11px] font-medium px-2 py-0.5 rounded-full border ${cfg.bg} ${cfg.text} ${cfg.border}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </span>
  );
}

function SourceCard({ source }) {
  const kind = SOURCE_KIND[source.kind] || SOURCE_KIND.calc;
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50/50 p-3 space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-gray-800">
          <span className="mr-1.5">{kind.emoji}</span>
          {source.label}
        </span>
        {source.confidence && <ConfidencePill level={source.confidence} />}
      </div>
      {source.details && <p className="text-xs text-gray-500 leading-relaxed">{source.details}</p>}
      {source.freshness && <p className="text-[11px] text-gray-400 italic">{source.freshness}</p>}
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2">
      {children}
    </p>
  );
}

export default function EvidenceDrawer({ open, onClose, evidence, children }) {
  const navigate = useNavigate();

  if (!evidence) return null;

  const allLinks = (evidence.sources || []).flatMap((s) => s.links || []);

  return (
    <Drawer open={open} onClose={onClose} title="Pourquoi ce chiffre ?">
      <div className="space-y-6">
        {/* Header: title + value + scope + period */}
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-gray-900">{evidence.title}</h3>
          {evidence.valueLabel && (
            <p className="text-2xl font-bold text-gray-900">{evidence.valueLabel}</p>
          )}
          <div className="flex flex-wrap gap-2 mt-1">
            {evidence.scopeLabel && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                {evidence.scopeLabel}
              </span>
            )}
            {evidence.periodLabel && (
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
                {evidence.periodLabel}
              </span>
            )}
          </div>
        </div>

        {/* Sources */}
        {evidence.sources?.length > 0 && (
          <div>
            <SectionTitle>Sources ({evidence.sources.length})</SectionTitle>
            <div className="space-y-2">
              {evidence.sources.map((src, i) => (
                <SourceCard key={i} source={src} />
              ))}
            </div>
          </div>
        )}

        {/* Method */}
        {evidence.method?.length > 0 && (
          <div>
            <SectionTitle>Méthode de calcul</SectionTitle>
            <ul className="space-y-1.5">
              {evidence.method.map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="text-gray-300 shrink-0 mt-0.5">•</span>
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Assumptions */}
        {evidence.assumptions?.length > 0 && (
          <div>
            <SectionTitle>Hypothèses</SectionTitle>
            <div className="bg-amber-50/60 border border-amber-100 rounded-lg p-3">
              <ul className="space-y-1">
                {evidence.assumptions.map((a, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-amber-800">
                    <span className="text-amber-300 shrink-0 mt-0.5">⚠</span>
                    <span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Footer: links + last computed */}
        <div className="pt-3 border-t border-gray-100 space-y-3">
          {allLinks.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {allLinks.map((link, i) => (
                <button
                  key={i}
                  onClick={() => {
                    onClose();
                    navigate(link.href);
                  }}
                  className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-800 font-medium
                    px-2.5 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 transition
                    focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                  aria-label={`Ouvrir : ${link.label}`}
                >
                  <ExternalLink size={12} />
                  {link.label}
                </button>
              ))}
            </div>
          )}
          {evidence.lastComputedAt && (
            <p className="text-[11px] text-gray-400">
              Dernier calcul : {new Date(evidence.lastComputedAt).toLocaleString('fr-FR')}
              {evidence.owner && ` — ${evidence.owner}`}
            </p>
          )}
        </div>

        {/* Slot for additional live content (e.g. ScoreBreakdownPanel) */}
        {children}
      </div>
    </Drawer>
  );
}
