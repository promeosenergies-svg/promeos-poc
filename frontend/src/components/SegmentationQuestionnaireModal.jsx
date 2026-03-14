/**
 * PROMEOS — V1.3 SegmentationQuestionnaireModal
 * Reusable modal questionnaire for segmentation.
 * Can be opened from Patrimoine, onboarding, or Renouvellements.
 * V1.3: new title/subtitle, q_surface_seuil priority, confirmation message,
 *        pre-fill from patrimoine, "Personnalise" badge concept.
 */
import { useState, useEffect } from 'react';
import { UserCheck, Send, X, CheckCircle } from 'lucide-react';
import {
  getSegmentationQuestions,
  getSegmentationProfile,
  submitSegmentationAnswers,
} from '../services/api';
import { Badge, Button } from '../ui';

const PRIORITY_QUESTIONS = ['q_surface_seuil', 'q_gtb', 'q_chauffage', 'q_irve'];

export default function SegmentationQuestionnaireModal({ onClose, onComplete }) {
  const [questions, setQuestions] = useState([]);
  const [profile, setProfile] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [submitError, setSubmitError] = useState(false);

  useEffect(() => {
    Promise.all([getSegmentationQuestions(), getSegmentationProfile()])
      .then(([qData, pData]) => {
        const allQ = qData.questions || [];
        const existingAnswers = pData?.answers || {};
        setProfile(pData);
        setAnswers(existingAnswers);

        // Pre-fill q_surface_seuil from patrimoine if available
        if (!existingAnswers.q_surface_seuil && pData?.organisation) {
          // If patrimoine has sites with known surface > 1000m2, we could pre-fill
          // For now we just prioritize the question
        }

        // Filter to unanswered questions, prioritizing PRIORITY_QUESTIONS
        const unanswered = allQ.filter((q) => !existingAnswers[q.id]);
        const priority = unanswered.filter((q) => PRIORITY_QUESTIONS.includes(q.id));
        const others = unanswered.filter((q) => !PRIORITY_QUESTIONS.includes(q.id));
        // Show up to 4 questions: priority first, then fill with others
        setQuestions([...priority, ...others].slice(0, 4));
      })
      .catch(() => {
        setLoadError(true);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleAnswer = (qid, value) => {
    setAnswers((prev) => ({ ...prev, [qid]: value }));
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError(false);
    try {
      const result = await submitSegmentationAnswers(answers);
      setSubmitted(true);
      if (onComplete) onComplete(result);
      // Auto-close after 3 seconds
      setTimeout(() => onClose(), 3000);
    } catch {
      setSubmitError(true);
    } finally {
      setSubmitting(false);
    }
  };

  const answeredCount = questions.filter((q) => answers[q.id]).length;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[85vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <UserCheck size={18} className="text-blue-600" />
            <h2 className="font-bold text-gray-900">Personnalisez votre cockpit énergie</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {submitted ? (
            <div className="py-8 text-center" data-testid="segmentation-confirmation">
              <div className="mx-auto w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mb-3">
                <CheckCircle size={24} className="text-green-600" />
              </div>
              <p className="text-base font-semibold text-gray-900 mb-2">Profil mis à jour</p>
              <p className="text-sm text-gray-600">
                PROMEOS adapte désormais vos recommandations et obligations à votre situation.
              </p>
              <Button size="sm" className="mt-4" onClick={onClose}>
                Fermer
              </Button>
            </div>
          ) : loading ? (
            <div className="py-8 text-center text-sm text-gray-400">Chargement...</div>
          ) : loadError ? (
            <div className="py-6 text-center">
              <p className="text-sm text-red-600">
                Impossible de charger le questionnaire. Vérifiez votre connexion.
              </p>
              <button onClick={onClose} className="mt-3 text-xs text-blue-600 hover:underline">
                Fermer
              </button>
            </div>
          ) : questions.length === 0 ? (
            <div className="py-6 text-center">
              <p className="text-sm text-gray-600 mb-2">
                Toutes les questions ont déjà été répondues.
              </p>
              {profile && (
                <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 rounded-lg">
                  <span className="text-sm font-medium text-blue-700">
                    {profile.segment_label || profile.typologie}
                  </span>
                  <Badge status={profile.confidence_score >= 70 ? 'ok' : 'warn'}>
                    {Math.round(profile.confidence_score)}%
                  </Badge>
                </div>
              )}
            </div>
          ) : (
            <>
              <p className="text-sm text-gray-500">
                Quelques réponses rapides pour adapter vos recommandations, obligations et priorités
                énergétiques.
              </p>
              {profile?.segment_label && (
                <div
                  className="flex items-center gap-2 px-3 py-2 bg-blue-50 rounded-lg"
                  data-testid="detected-profile"
                >
                  <span className="text-xs text-blue-700">
                    Secteur détecté : <strong>{profile.segment_label}</strong>
                  </span>
                </div>
              )}
              {questions.map((q, idx) => (
                <div key={q.id} className="space-y-2">
                  <p className="text-sm font-medium text-gray-800">
                    <span className="text-blue-600 font-bold mr-1.5">{idx + 1}.</span>
                    {q.text}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {q.options.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => handleAnswer(q.id, opt.value)}
                        className={`px-3 py-1.5 rounded-lg text-xs border transition
                          ${
                            answers[q.id] === opt.value
                              ? 'bg-blue-600 text-white border-blue-600'
                              : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:text-blue-600'
                          }`}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </>
          )}
          {submitError && (
            <p className="text-xs text-red-600 mt-2">Erreur lors de l'envoi. Réessayez.</p>
          )}
        </div>

        {/* Footer */}
        {questions.length > 0 && !submitted && (
          <div className="px-6 py-3 border-t flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {answeredCount}/{questions.length} réponse{answeredCount > 1 ? 's' : ''}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={onClose}>
                Plus tard
              </Button>
              <Button size="sm" onClick={handleSubmit} disabled={answeredCount === 0 || submitting}>
                <Send size={12} className="mr-1" />
                {submitting ? 'Envoi...' : 'Valider mon profil'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
