/**
 * PROMEOS — CsatModal (CX Gap #7)
 * Modale CSAT déclenchée automatiquement J+14 après création de l'org.
 * 1 question (1-5) + verbatim optionnel. Dismiss persistant en localStorage.
 */
import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import api from '../services/api';

const DISMISS_KEY_PREFIX = 'promeos.csat_dismissed_';

const SCORES = [
  { value: 1, emoji: '😞', label: 'Pas utile' },
  { value: 2, emoji: '😐', label: 'Peu utile' },
  { value: 3, emoji: '🙂', label: 'Utile' },
  { value: 4, emoji: '😊', label: 'Très utile' },
  { value: 5, emoji: '🤩', label: 'Indispensable' },
];

export default function CsatModal({ orgId }) {
  const [shouldShow, setShouldShow] = useState(false);
  const [selected, setSelected] = useState(null);
  const [verbatim, setVerbatim] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  useEffect(() => {
    if (!orgId) return;
    if (localStorage.getItem(DISMISS_KEY_PREFIX + orgId) === 'true') return;

    api
      .get('/feedback/csat/should-show', { params: { org_id: orgId } })
      .then((r) => {
        if (r.data?.show) {
          setTimeout(() => setShouldShow(true), 3000);
        }
      })
      .catch(() => {});
  }, [orgId]);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY_PREFIX + orgId, 'true');
    setShouldShow(false);
  };

  const submit = async () => {
    if (selected == null) return;
    setSubmitting(true);
    try {
      await api.post(
        '/feedback/csat',
        { score: selected, verbatim: verbatim || null, trigger_type: 'j14_auto' },
        { params: { org_id: orgId } }
      );
      setSubmitted(true);
      localStorage.setItem(DISMISS_KEY_PREFIX + orgId, 'true');
      setTimeout(() => setShouldShow(false), 1500);
    } catch {
      // Silent fail — ne bloque pas l'utilisateur
    } finally {
      setSubmitting(false);
    }
  };

  if (!shouldShow) return null;

  return (
    <div className="fixed bottom-6 right-6 w-[360px] bg-white rounded-lg shadow-xl border border-gray-200 p-4 z-50">
      <button
        onClick={dismiss}
        className="absolute top-2 right-2 text-gray-300 hover:text-gray-500"
        aria-label="Fermer"
      >
        <X size={16} />
      </button>
      {submitted ? (
        <div className="py-2 text-center text-sm text-emerald-700 font-medium">
          Merci pour votre retour !
        </div>
      ) : (
        <>
          <h3 className="text-sm font-semibold text-gray-900 mb-1">
            À quel point PROMEOS vous est utile ?
          </h3>
          <p className="text-[11px] text-gray-500 mb-3">
            Votre avis nous aide à améliorer le produit.
          </p>
          <div className="flex justify-between mb-3">
            {SCORES.map((s) => (
              <button
                key={s.value}
                onClick={() => setSelected(s.value)}
                className={`flex flex-col items-center gap-1 p-2 rounded-lg transition ${
                  selected === s.value ? 'bg-blue-50 ring-2 ring-blue-400' : 'hover:bg-gray-50'
                }`}
                aria-label={s.label}
              >
                <span className="text-xl">{s.emoji}</span>
                <span className="text-[9px] text-gray-500">{s.value}</span>
              </button>
            ))}
          </div>
          {selected != null && (
            <>
              <textarea
                value={verbatim}
                onChange={(e) => setVerbatim(e.target.value.slice(0, 500))}
                placeholder="Un mot à ajouter ? (optionnel)"
                className="w-full text-xs border border-gray-200 rounded-md p-2 mb-2 resize-none"
                rows={2}
              />
              <button
                onClick={submit}
                disabled={submitting}
                className="w-full py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
              >
                {submitting ? 'Envoi...' : 'Envoyer'}
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
