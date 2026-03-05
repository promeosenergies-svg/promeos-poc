/**
 * PROMEOS — V100 SegmentationQuestionnaireModal
 * Reusable modal questionnaire for segmentation.
 * Can be opened from Patrimoine, onboarding, or Renouvellements.
 * Shows 3 priority questions (not the full 8) for quick profiling.
 */
import { useState, useEffect } from 'react';
import { UserCheck, Send, X } from 'lucide-react';
import {
  getSegmentationQuestions,
  getSegmentationProfile,
  submitSegmentationAnswers,
} from '../services/api';
import { Badge, Button } from '../ui';

const PRIORITY_QUESTIONS = ['q_operat', 'q_bacs', 'q_horaires'];

export default function SegmentationQuestionnaireModal({ onClose, onComplete }) {
  const [questions, setQuestions] = useState([]);
  const [profile, setProfile] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [submitError, setSubmitError] = useState(false);

  useEffect(() => {
    Promise.all([getSegmentationQuestions(), getSegmentationProfile()])
      .then(([qData, pData]) => {
        // Show only missing priority questions, then fill with others
        const allQ = qData.questions || [];
        const existingAnswers = pData?.answers || {};
        setProfile(pData);
        setAnswers(existingAnswers);

        // Filter to unanswered questions, prioritizing PRIORITY_QUESTIONS
        const unanswered = allQ.filter((q) => !existingAnswers[q.id]);
        const priority = unanswered.filter((q) => PRIORITY_QUESTIONS.includes(q.id));
        const others = unanswered.filter((q) => !PRIORITY_QUESTIONS.includes(q.id));
        // Show up to 4 questions: priority first, then fill with others
        setQuestions([...priority, ...others].slice(0, 4));
      })
      .catch((_err) => {
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
      if (onComplete) onComplete(result);
      onClose();
    } catch (err) {
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
            <h2 className="font-bold text-gray-900">Affinez votre profil énergie</h2>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {loading ? (
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
                Toutes les questions ont deja ete repondues.
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
                Répondez à quelques questions pour améliorer la précision de vos recommandations.
              </p>
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
            <p className="text-xs text-red-600 mt-2">Erreur lors de l'envoi. Reessayez.</p>
          )}
        </div>

        {/* Footer */}
        {questions.length > 0 && (
          <div className="px-6 py-3 border-t flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {answeredCount}/{questions.length} reponse{answeredCount > 1 ? 's' : ''}
            </span>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={onClose}>
                Plus tard
              </Button>
              <Button size="sm" onClick={handleSubmit} disabled={answeredCount === 0 || submitting}>
                <Send size={12} className="mr-1" />
                {submitting ? 'Envoi...' : 'Valider'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
