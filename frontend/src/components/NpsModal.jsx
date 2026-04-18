/**
 * PROMEOS — NpsModal (Sprint CX P1 residual)
 *
 * Micro-survey NPS (Net Promoter Score) — instrumente la mesure scorecard
 * "NPS/CES" (10% du score) orpheline avant ce sprint.
 *
 * Pattern industry-standard :
 *   - Question : "Dans quelle mesure recommanderiez-vous PROMEOS à un collègue ?"
 *   - Échelle 0-10 (11 boutons cliquables)
 *   - Verbatim optionnel
 *   - Classification promoter (9-10) / passive (7-8) / detractor (0-6)
 *
 * Self-contained : la modale décide elle-même de s'afficher (trigger J+30 via
 * shouldShowNps + délai 5 s non-intrusif), align avec CsatModal. Le caller
 * n'a qu'à mount <NpsModal orgId={...} userCreatedAt={...} /> — aucun état
 * externe.
 *
 * Anti-flood 90j côté front (localStorage) + côté back (AuditLog).
 */
import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { submitNps } from '../services/api/nps';
import { markNpsSubmitted, markNpsDismissed, shouldShowNps } from '../utils/nps';

const SCORES = Array.from({ length: 11 }, (_, i) => i); // 0..10

function categoryOf(score) {
  if (score >= 9) return 'promoter';
  if (score >= 7) return 'passive';
  return 'detractor';
}

function scoreColor(score, selected) {
  const base = 'w-8 h-8 text-xs font-medium rounded-md border transition';
  const cat = categoryOf(score);
  if (selected) {
    if (cat === 'promoter') return `${base} bg-emerald-600 text-white border-emerald-600`;
    if (cat === 'passive') return `${base} bg-amber-500 text-white border-amber-500`;
    return `${base} bg-rose-600 text-white border-rose-600`;
  }
  return `${base} bg-white text-gray-700 border-gray-200 hover:border-gray-400`;
}

export default function NpsModal({ orgId, userCreatedAt, onSubmit }) {
  const [isOpen, setIsOpen] = useState(false);
  const [score, setScore] = useState(null);
  const [verbatim, setVerbatim] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (!userCreatedAt) return;
    if (!shouldShowNps(userCreatedAt)) return;
    const timer = setTimeout(() => setIsOpen(true), 5000);
    return () => clearTimeout(timer);
  }, [userCreatedAt]);

  if (!isOpen) return null;

  const dismiss = () => {
    markNpsDismissed(30);
    setIsOpen(false);
  };

  const handleSubmit = async () => {
    if (score == null) return;
    setSubmitting(true);
    try {
      const res = await submitNps({ score, verbatim: verbatim.trim() || undefined, orgId });
      markNpsSubmitted();
      setSubmitted(true);
      onSubmit?.(res);
      setTimeout(() => setIsOpen(false), 1500);
    } catch {
      // Silent fail — on marque quand même pour éviter boucle immédiate
      markNpsSubmitted();
      setIsOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Enquête de satisfaction NPS"
      className="fixed bottom-6 right-6 w-[380px] bg-white rounded-lg shadow-xl border border-gray-200 p-4 z-50"
    >
      <button
        onClick={dismiss}
        className="absolute top-2 right-2 text-gray-300 hover:text-gray-600"
        aria-label="Ignorer pour l'instant"
      >
        <X size={16} />
      </button>

      {submitted ? (
        <div className="py-4 text-center text-sm text-emerald-700 font-medium">
          Merci pour votre retour !
        </div>
      ) : (
        <>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            Dans quelle mesure recommanderiez-vous PROMEOS à un collègue ?
          </h3>
          <p className="text-[11px] text-gray-500 mb-3">0 = Pas du tout · 10 = Absolument</p>

          <div role="radiogroup" aria-label="Note NPS 0 à 10" className="flex flex-wrap gap-1 mb-3">
            {SCORES.map((s) => (
              <button
                key={s}
                type="button"
                role="radio"
                aria-checked={score === s}
                aria-label={`Note ${s}`}
                onClick={() => setScore(s)}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowLeft' && s > 0) {
                    e.preventDefault();
                    setScore(s - 1);
                  } else if (e.key === 'ArrowRight' && s < 10) {
                    e.preventDefault();
                    setScore(s + 1);
                  }
                }}
                className={scoreColor(s, score === s)}
              >
                {s}
              </button>
            ))}
          </div>

          {score != null && (
            <>
              <label htmlFor="nps-verbatim" className="block text-[11px] text-gray-600 mb-1">
                Qu'est-ce qui a le plus pesé dans votre note ? (optionnel)
              </label>
              <textarea
                id="nps-verbatim"
                value={verbatim}
                onChange={(e) => setVerbatim(e.target.value.slice(0, 1000))}
                placeholder="Quelques mots libres..."
                className="w-full text-xs border border-gray-200 rounded-md p-2 mb-2 resize-none"
                rows={2}
              />
              <div className="flex gap-2">
                <button
                  onClick={dismiss}
                  type="button"
                  className="flex-1 py-1.5 text-xs text-gray-600 border border-gray-200 rounded-md hover:bg-gray-50"
                >
                  Ignorer pour l'instant
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  type="button"
                  className="flex-1 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
                >
                  {submitting ? 'Envoi...' : 'Envoyer'}
                </button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
