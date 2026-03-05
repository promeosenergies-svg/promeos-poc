/**
 * PROMEOS - IntakeWizard (Smart Intake DIAMANT)
 * Wizard max 8 questions with before/after compliance preview.
 * Modes: WIZARD (step-by-step), DEMO (auto-fill 10s).
 */
import { useState, useCallback } from 'react';
import {
  X,
  ChevronRight,
  ChevronLeft,
  Check,
  Zap,
  ClipboardCheck,
  HelpCircle,
  ArrowRight,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import {
  getIntakeQuestions,
  submitIntakeAnswer,
  completeIntake,
  intakeDemoAutofill,
} from '../services/api';

const SEVERITY_COLORS = {
  critical: 'bg-red-100 text-red-700',
  high: 'bg-orange-100 text-orange-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-blue-100 text-blue-700',
  info: 'bg-gray-100 text-gray-600',
};

function ScoreBadge({ score, size = 'md' }) {
  const color = score >= 70 ? 'text-green-600' : score >= 40 ? 'text-amber-600' : 'text-red-600';
  const sz = size === 'lg' ? 'text-3xl' : 'text-lg';
  return <span className={`font-bold ${color} ${sz}`}>{score?.toFixed(0) ?? '—'}%</span>;
}

function DeltaBadge({ delta }) {
  if (!delta || delta === 0) return null;
  const positive = delta > 0;
  return (
    <span className={`text-sm font-medium ${positive ? 'text-green-600' : 'text-red-600'}`}>
      {positive ? '+' : ''}
      {delta.toFixed(1)}%
    </span>
  );
}

export default function IntakeWizard({ siteId, onClose }) {
  const [mode, setMode] = useState(null); // null = intro, 'wizard', 'demo'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Data from API
  const [_sessionId, setSessionId] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [prefills, setPrefills] = useState({});

  // Wizard state
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState({}); // {field_path: value}
  const [diffs, setDiffs] = useState({}); // {field_path: diff_preview}

  // Result
  const [result, setResult] = useState(null);

  // Phase: 'intro' | 'questions' | 'review' | 'result'
  const phase = result
    ? 'result'
    : mode === null
      ? 'intro'
      : questions.length === 0 || currentQ >= questions.length
        ? 'review'
        : 'questions';

  // Load questions on start
  const loadQuestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getIntakeQuestions(siteId);
      setSessionId(data.session_id);
      setQuestions(data.questions || []);
      setPrefills(data.prefills || {});
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors du chargement des questions');
    }
    setLoading(false);
  }, [siteId]);

  // Start wizard mode
  const startWizard = async () => {
    setMode('wizard');
    await loadQuestions();
  };

  // Start demo mode
  const startDemo = async () => {
    setMode('demo');
    setLoading(true);
    setError(null);
    try {
      const data = await intakeDemoAutofill(siteId);
      setResult({
        score_before: data.score_before,
        score_after: data.score_after,
        delta: data.delta,
        answers_count: data.answers_created,
        mode: 'demo',
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur mode demo');
    }
    setLoading(false);
  };

  // Submit one answer
  const handleAnswer = async (fieldPath, value) => {
    setAnswers((prev) => ({ ...prev, [fieldPath]: value }));
    try {
      const data = await submitIntakeAnswer(siteId, fieldPath, value);
      setDiffs((prev) => ({ ...prev, [fieldPath]: data.diff_preview }));
    } catch (err) {
      // Non-blocking: answer saved locally even if diff fails
    }
  };

  // Complete
  const handleComplete = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await completeIntake(siteId);
      setResult({
        score_before: data.score_before,
        score_after: data.score_after,
        delta: data.delta,
        fields_applied: data.fields_applied,
        mode: 'wizard',
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de la validation');
    }
    setLoading(false);
  };

  // Current question
  const q = questions[currentQ];
  const answeredCount = Object.keys(answers).length;
  const totalSteps = questions.length + 2; // intro + questions + review
  const currentStep = phase === 'intro' ? 0 : phase === 'questions' ? currentQ + 1 : totalSteps - 1;

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <ClipboardCheck size={20} className="text-blue-600" />
            <h3 className="font-semibold text-gray-900">Smart Intake</h3>
            {phase !== 'intro' && phase !== 'result' && (
              <span className="text-xs text-gray-400">
                Etape {currentStep}/{totalSteps - 1}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600"
          >
            <X size={18} />
          </button>
        </div>

        {/* Progress bar */}
        {phase !== 'intro' && phase !== 'result' && (
          <div className="h-1 bg-gray-100">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${(currentStep / (totalSteps - 1)) * 100}%` }}
            />
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
              <AlertTriangle size={16} /> {error}
            </div>
          )}

          {/* INTRO */}
          {phase === 'intro' && (
            <div className="space-y-6">
              <div className="text-center">
                <h4 className="text-lg font-semibold text-gray-900 mb-2">
                  Compléter les données réglementaires
                </h4>
                <p className="text-sm text-gray-500">
                  Répondez à quelques questions pour améliorer votre score de conformité. Les
                  résultats sont déterminés par les règles réglementaires, pas par l'IA.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={startWizard}
                  disabled={loading}
                  className="p-5 border-2 border-gray-200 rounded-xl hover:border-blue-400 hover:bg-blue-50 transition text-left group"
                >
                  <ClipboardCheck
                    size={24}
                    className="text-blue-500 mb-3 group-hover:text-blue-600"
                  />
                  <div className="font-medium text-gray-900">Wizard</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Répondez étape par étape (max 8 questions)
                  </div>
                  <div className="text-xs text-blue-600 mt-2">~3 min</div>
                </button>

                <button
                  onClick={startDemo}
                  disabled={loading}
                  className="p-5 border-2 border-gray-200 rounded-xl hover:border-green-400 hover:bg-green-50 transition text-left group"
                >
                  <Zap size={24} className="text-green-500 mb-3 group-hover:text-green-600" />
                  <div className="font-medium text-gray-900">Demo</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Remplissage automatique avec valeurs demo
                  </div>
                  <div className="text-xs text-green-600 mt-2">~10 sec</div>
                </button>
              </div>
            </div>
          )}

          {/* QUESTIONS */}
          {phase === 'questions' && q && (
            <div className="space-y-6">
              {/* Question header */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${SEVERITY_COLORS[q.severity] || SEVERITY_COLORS.info}`}
                  >
                    {q.severity}
                  </span>
                  {q.regulations?.map((r) => (
                    <span key={r} className="text-xs text-gray-400">
                      {r}
                    </span>
                  ))}
                </div>
                <h4 className="text-lg font-medium text-gray-900">{q.question}</h4>
                {q.help && (
                  <p className="text-sm text-gray-500 mt-1 flex items-start gap-1">
                    <HelpCircle size={14} className="mt-0.5 flex-shrink-0" /> {q.help}
                  </p>
                )}
              </div>

              {/* Input */}
              <QuestionInput
                question={q}
                value={answers[q.field_path]}
                prefill={prefills[q.field_path] ?? q.prefill_value}
                onChange={(val) => handleAnswer(q.field_path, val)}
              />

              {/* Diff preview */}
              {diffs[q.field_path] && (
                <div className="p-3 bg-gray-50 rounded-lg text-sm">
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500">Score conformite:</span>
                    <ScoreBadge score={diffs[q.field_path].score_before} />
                    <ArrowRight size={14} className="text-gray-400" />
                    <ScoreBadge score={diffs[q.field_path].score_after} />
                    <DeltaBadge delta={diffs[q.field_path].delta} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* REVIEW */}
          {phase === 'review' && !result && (
            <div className="space-y-6">
              <h4 className="text-lg font-semibold text-gray-900">Recapitulatif</h4>

              {answeredCount === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <CheckCircle2 size={40} className="mx-auto mb-3 text-green-400" />
                  <p className="font-medium text-gray-600">Aucune question a completer</p>
                  <p className="text-sm">
                    Toutes les données réglementaires sont déjà renseignées.
                  </p>
                </div>
              ) : (
                <>
                  <div className="divide-y divide-gray-100">
                    {Object.entries(answers).map(([fp, val]) => {
                      const qDef = questions.find((q) => q.field_path === fp);
                      return (
                        <div key={fp} className="py-3 flex items-center justify-between">
                          <div>
                            <div className="text-sm font-medium text-gray-800">
                              {qDef?.question || fp}
                            </div>
                            <div className="text-xs text-gray-400">{fp}</div>
                          </div>
                          <div className="text-sm font-medium text-gray-900">
                            {typeof val === 'boolean' ? (val ? 'Oui' : 'Non') : String(val)}
                            {qDef?.unit && <span className="text-gray-400 ml-1">{qDef.unit}</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Final diff */}
                  {Object.values(diffs).length > 0 &&
                    (() => {
                      const lastDiff = Object.values(diffs)[Object.values(diffs).length - 1];
                      return (
                        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-blue-700">
                              Impact sur la conformite
                            </span>
                            <div className="flex items-center gap-3">
                              <ScoreBadge score={lastDiff.score_before} />
                              <ArrowRight size={16} className="text-blue-400" />
                              <ScoreBadge score={lastDiff.score_after} />
                              <DeltaBadge delta={lastDiff.delta} />
                            </div>
                          </div>
                        </div>
                      );
                    })()}
                </>
              )}
            </div>
          )}

          {/* RESULT */}
          {phase === 'result' && result && (
            <div className="space-y-6 text-center py-4">
              <CheckCircle2 size={48} className="mx-auto text-green-500" />
              <h4 className="text-lg font-semibold text-gray-900">Intake termine !</h4>

              <div className="flex items-center justify-center gap-6">
                <div>
                  <div className="text-xs text-gray-400 uppercase mb-1">Avant</div>
                  <ScoreBadge score={result.score_before} size="lg" />
                </div>
                <ArrowRight size={20} className="text-gray-300" />
                <div>
                  <div className="text-xs text-gray-400 uppercase mb-1">Apres</div>
                  <ScoreBadge score={result.score_after} size="lg" />
                </div>
              </div>

              <DeltaBadge delta={result.delta} />

              <div className="text-sm text-gray-500">
                {result.mode === 'demo'
                  ? `${result.answers_count} champ(s) rempli(s) en mode demo`
                  : `${result.fields_applied} champ(s) appliqué(s)`}
              </div>
            </div>
          )}

          {loading && !result && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin h-6 w-6 border-2 border-blue-500 border-t-transparent rounded-full" />
              <span className="ml-3 text-sm text-gray-500">Chargement...</span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-100 bg-gray-50">
          {phase === 'intro' && <div />}

          {phase === 'questions' && (
            <button
              onClick={() => setCurrentQ(Math.max(0, currentQ - 1))}
              disabled={currentQ === 0}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40"
            >
              <ChevronLeft size={16} /> Précédent
            </button>
          )}

          {phase === 'review' && !result && (
            <button
              onClick={() => setCurrentQ(Math.max(0, questions.length - 1))}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
            >
              <ChevronLeft size={16} /> Retour
            </button>
          )}

          {phase === 'result' && <div />}

          <div className="flex items-center gap-2">
            {phase === 'questions' && (
              <>
                <button
                  onClick={() => setCurrentQ(currentQ + 1)}
                  className="text-sm text-gray-400 hover:text-gray-600 px-3 py-2"
                >
                  Passer
                </button>
                <button
                  onClick={() => {
                    if (answers[q?.field_path] !== undefined) setCurrentQ(currentQ + 1);
                  }}
                  disabled={answers[q?.field_path] === undefined}
                  className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Suivant <ChevronRight size={16} />
                </button>
              </>
            )}

            {phase === 'review' && !result && answeredCount > 0 && (
              <button
                onClick={handleComplete}
                disabled={loading}
                className="flex items-center gap-1 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-60"
              >
                <Check size={16} /> Appliquer ({answeredCount} réponse{answeredCount > 1 ? 's' : ''}
                )
              </button>
            )}

            {phase === 'result' && (
              <button
                onClick={onClose}
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
              >
                Fermer
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Dynamic input based on question type.
 */
function QuestionInput({ question, value, prefill, onChange }) {
  const { input_type, options, unit } = question;

  if (input_type === 'boolean') {
    return (
      <div className="flex gap-3">
        {[
          { val: true, label: 'Oui' },
          { val: false, label: 'Non' },
        ].map(({ val, label }) => (
          <button
            key={label}
            onClick={() => onChange(val)}
            className={`flex-1 py-3 rounded-lg border-2 text-sm font-medium transition ${
              value === val
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-600 hover:border-gray-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    );
  }

  if (input_type === 'select' && options) {
    return (
      <div className="grid grid-cols-2 gap-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className={`py-3 px-4 rounded-lg border-2 text-sm font-medium text-left transition ${
              value === opt.value
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-200 text-gray-600 hover:border-gray-300'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  // number or text
  return (
    <div className="space-y-2">
      <div className="relative">
        <input
          type={input_type === 'number' ? 'number' : 'text'}
          value={value ?? ''}
          onChange={(e) => {
            const v =
              input_type === 'number'
                ? e.target.value
                  ? parseFloat(e.target.value)
                  : ''
                : e.target.value;
            onChange(v);
          }}
          placeholder={prefill != null ? `Suggestion: ${prefill}` : ''}
          className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {unit && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">
            {unit}
          </span>
        )}
      </div>
      {prefill != null && value !== prefill && (
        <button
          onClick={() => onChange(prefill)}
          className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700"
        >
          <Sparkles size={12} /> Utiliser la suggestion: {prefill} {unit || ''}
        </button>
      )}
    </div>
  );
}
