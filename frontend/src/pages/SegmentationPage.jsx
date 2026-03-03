/**
 * PROMEOS - Segmentation B2B Page
 * Affinez votre profil pour des recommandations plus precises.
 */
import { useState, useEffect } from 'react';
import { UserCheck, CheckCircle, Send } from 'lucide-react';
import {
  getSegmentationQuestions,
  getSegmentationProfile,
  submitSegmentationAnswers,
} from '../services/api';
import { PageShell, Card, CardBody, Badge, Button, EmptyState, Progress } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { useToast } from '../ui/ToastProvider';

const TYPO_LABELS = {
  tertiaire_prive: 'Tertiaire Prive',
  tertiaire_public: 'Tertiaire Public',
  industrie: 'Industrie',
  commerce_retail: 'Commerce / Retail',
  copropriete_syndic: 'Copropriete / Syndic',
  bailleur_social: 'Bailleur Social',
  collectivite: 'Collectivite',
  hotellerie_restauration: 'Hotellerie / Restauration',
  sante_medico_social: 'Sante / Medico-social',
  enseignement: 'Enseignement',
  mixte: 'Mixte (multi-activites)',
};

export default function SegmentationPage() {
  const [questions, setQuestions] = useState([]);
  const [profile, setProfile] = useState(null);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    Promise.all([
      getSegmentationQuestions(),
      getSegmentationProfile(),
    ]).then(([qData, pData]) => {
      setQuestions(qData.questions || []);
      setProfile(pData);
      if (pData.answers && Object.keys(pData.answers).length > 0) {
        setAnswers(pData.answers);
      }
    }).catch(() => {
      toast('Erreur lors du chargement de la segmentation', 'error');
    }).finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAnswer = (questionId, value) => {
    setAnswers(prev => ({ ...prev, [questionId]: value }));
    setSubmitted(false);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const result = await submitSegmentationAnswers(answers);
      setProfile(prev => ({
        ...prev,
        has_profile: true,
        typologie: result.typologie,
        confidence_score: result.confidence_score,
        reasons: result.reasons,
      }));
      setSubmitted(true);
      toast('Profil mis a jour avec succes', 'success');
    } catch {
      toast('Erreur lors de la mise a jour du profil', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const answeredCount = Object.values(answers).filter(v => v).length;
  const progressPct = questions.length > 0 ? Math.round((answeredCount / questions.length) * 100) : 0;

  if (loading) {
    return (
      <PageShell icon={UserCheck} title="Segmentation B2B" subtitle="Chargement...">
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </PageShell>
    );
  }

  return (
    <PageShell
      icon={UserCheck}
      title="Segmentation B2B"
      subtitle="Affinez votre profil pour des recommandations plus precises"
    >
      {/* Current profile card */}
      {profile && profile.has_profile && (
        <Card className="border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <CardBody>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-blue-700">Profil actuel</h2>
              {submitted && (
                <Badge status="ok">
                  <CheckCircle size={12} className="mr-1" /> Mis a jour
                </Badge>
              )}
            </div>
            <p className="text-xl font-bold text-gray-900 mb-1">
              {profile.segment_label || TYPO_LABELS[profile.typologie] || profile.typologie}
            </p>
            {profile.derived_from && (
              <p className="text-xs text-gray-500 mb-3">
                Source : {profile.derived_from === 'naf' ? 'Code NAF' : profile.derived_from === 'questionnaire' ? 'Questionnaire' : profile.derived_from === 'patrimoine' ? 'Patrimoine' : 'Detection mixte'}
              </p>
            )}
            <div className="mb-2">
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-600">Confiance</span>
                <span className="font-bold text-gray-700">{Math.round(profile.confidence_score)}%</span>
              </div>
              <Progress
                value={profile.confidence_score}
                max={100}
                color={profile.confidence_score >= 70 ? 'green' : profile.confidence_score >= 40 ? 'amber' : 'red'}
              />
            </div>
            {profile.reasons && profile.reasons.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-2">
                {profile.reasons.map((r, i) => (
                  <Badge key={i} status="neutral">{r}</Badge>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      )}

      {/* Progress bar */}
      <Card>
        <CardBody>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-base font-semibold text-gray-800">
              Questionnaire
            </h2>
            <span className="text-sm text-gray-500">{answeredCount}/{questions.length} reponses</span>
          </div>
          <Progress value={progressPct} max={100} />
        </CardBody>
      </Card>

      {/* Questions */}
      {questions.length === 0 ? (
        <EmptyState
          icon={UserCheck}
          title="Aucune question disponible"
          text="Le questionnaire de segmentation n'est pas encore configure."
        />
      ) : (
        <div className="space-y-4">
          {questions.map((q, idx) => (
            <Card
              key={q.id}
              className={answers[q.id] ? 'border-blue-200 bg-blue-50/30' : ''}
            >
              <CardBody>
                <p className="text-sm font-medium text-gray-800 mb-3">
                  <span className="text-blue-600 font-bold mr-2">{idx + 1}.</span>
                  {q.text}
                </p>
                <div className="flex flex-wrap gap-2">
                  {q.options.map(opt => (
                    <button
                      key={opt.value}
                      onClick={() => handleAnswer(q.id, opt.value)}
                      className={`px-3 py-1.5 rounded-lg text-sm border transition
                        ${answers[q.id] === opt.value
                          ? 'bg-blue-600 text-white border-blue-600'
                          : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:text-blue-600'
                        }`}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* Submit */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-500">
          {answeredCount === 0
            ? 'Repondez aux questions pour affiner votre profil.'
            : `${answeredCount} reponse${answeredCount > 1 ? 's' : ''} sur ${questions.length}`}
        </p>
        <Button
          onClick={handleSubmit}
          disabled={answeredCount === 0 || submitting}
        >
          <Send size={14} className="mr-1.5" />
          {submitting ? 'Envoi...' : 'Mettre a jour le profil'}
        </Button>
      </div>
    </PageShell>
  );
}
