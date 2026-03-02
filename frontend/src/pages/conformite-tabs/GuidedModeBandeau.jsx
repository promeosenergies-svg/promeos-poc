/**
 * GuidedModeBandeau — Guided mode stepper banner for non-expert users.
 * Renders 7 steps with completion status. Visible when !isExpert.
 */
import { Lock, CheckCircle2, Circle, ArrowRight } from 'lucide-react';
import { Card, CardBody, Button } from '../../ui';
import { GUIDED_MODE_LABELS } from '../../domain/compliance/complianceLabels.fr';

const STATUS_STYLE = {
  complete:    { dot: 'bg-green-500', text: 'text-green-700', ring: 'ring-green-200', Icon: CheckCircle2 },
  in_progress: { dot: 'bg-blue-500', text: 'text-blue-700', ring: 'ring-blue-200', Icon: Circle },
  blocked:     { dot: 'bg-red-400', text: 'text-red-600', ring: 'ring-red-200', Icon: Lock },
  pending:     { dot: 'bg-gray-300', text: 'text-gray-400', ring: 'ring-gray-200', Icon: Circle },
};

const STATUS_LABEL = {
  complete: GUIDED_MODE_LABELS.complete_label,
  in_progress: GUIDED_MODE_LABELS.in_progress_label,
  blocked: GUIDED_MODE_LABELS.blocked_label,
  pending: GUIDED_MODE_LABELS.pending_label,
};

export default function GuidedModeBandeau({ steps, onStepClick }) {
  if (!steps || steps.length === 0) return null;

  // Active step = first in_progress (or first non-complete if none in_progress)
  const activeStep = steps.find(s => s.status === 'in_progress')
    || steps.find(s => s.status !== 'complete' && s.status !== 'blocked');

  return (
    <div data-testid="guided-mode-bandeau" className="mb-4">
      <Card>
        <CardBody>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            {GUIDED_MODE_LABELS.bandeau_title}
          </p>

          {/* Step pills */}
          <div className="flex items-center gap-1 mb-3 overflow-x-auto">
            {steps.map((step, i) => {
              const cfg = STATUS_STYLE[step.status] || STATUS_STYLE.pending;
              const isActive = activeStep?.id === step.id;
              const StepIcon = cfg.Icon;

              return (
                <div key={step.id} className="flex items-center" data-testid={`guided-step-${step.id}`}>
                  <button
                    onClick={() => step.status !== 'blocked' && onStepClick(step)}
                    disabled={step.status === 'blocked'}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition whitespace-nowrap
                      ${isActive ? `ring-2 ${cfg.ring} ${cfg.text} bg-white shadow-sm` : `${cfg.text} hover:bg-gray-50`}
                      ${step.status === 'blocked' ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                    `}
                  >
                    <StepIcon size={12} />
                    <span>{step.label}</span>
                  </button>
                  {i < steps.length - 1 && (
                    <ArrowRight size={10} className="text-gray-300 mx-0.5 shrink-0" />
                  )}
                </div>
              );
            })}
          </div>

          {/* Active step detail */}
          {activeStep && (
            <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
              <div>
                <p className="text-sm font-semibold text-gray-900">{activeStep.label}</p>
                <p className="text-xs text-gray-600 mt-0.5">{activeStep.description}</p>
              </div>
              <Button size="sm" onClick={() => onStepClick(activeStep)}>
                {activeStep.cta}
              </Button>
            </div>
          )}

          {/* Progress summary */}
          <div className="flex items-center gap-3 mt-3 text-[10px] text-gray-400">
            {Object.entries(STATUS_LABEL).map(([status, label]) => {
              const count = steps.filter(s => s.status === status).length;
              if (count === 0) return null;
              const cfg = STATUS_STYLE[status];
              return (
                <span key={status} className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${cfg.dot}`} />
                  {count} {label}
                </span>
              );
            })}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
