/**
 * AuditSmeCard - Carte Audit Energetique / SME
 *
 * Source : Loi n 2025-391 du 30 avril 2025 (art. L.233-1 code de l'energie)
 * Deadline : 11 octobre 2026 (premier audit entreprises existantes)
 *
 * REGLE ABSOLUE : zero calcul metier. Display-only.
 * Toutes les valeurs viennent de GET /api/regops/organisations/{id}/audit-sme
 */

import React from 'react';
import { FileCheck, AlertTriangle, Clock, CheckCircle, XCircle, Shield } from 'lucide-react';

const STATUT_CONFIG = {
  CONFORME: {
    icon: CheckCircle,
    label: 'Conforme',
    bg: 'bg-green-50',
    border: 'border-green-200',
    text: 'text-green-700',
    badge: 'bg-green-100 text-green-800',
  },
  EN_COURS: {
    icon: Clock,
    label: 'En cours',
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-700',
    badge: 'bg-blue-100 text-blue-800',
  },
  A_REALISER: {
    icon: AlertTriangle,
    label: 'A realiser',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-700',
    badge: 'bg-amber-100 text-amber-800',
  },
  EN_RETARD: {
    icon: XCircle,
    label: 'En retard',
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-700',
    badge: 'bg-red-100 text-red-800',
  },
  NON_CONCERNE: {
    icon: Shield,
    label: 'Non concerne',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-500',
    badge: 'bg-gray-100 text-gray-500',
  },
  NON_DETERMINE: {
    icon: Shield,
    label: 'Non determine',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-500',
    badge: 'bg-gray-100 text-gray-500',
  },
};

const OBLIGATION_LABELS = {
  SME_ISO50001: 'SME ISO 50001 (>= 23.6 GWh/an)',
  AUDIT_4ANS: 'Audit energetique tous les 4 ans (2.75-23.6 GWh/an)',
  AUCUNE: 'Aucune obligation (< 2.75 GWh/an)',
};

function ChecklistIcon({ ok, bloquant }) {
  if (ok) return <CheckCircle size={13} className="text-green-600" />;
  if (bloquant) return <XCircle size={13} className="text-red-500" />;
  return <AlertTriangle size={13} className="text-amber-500" />;
}

export default function AuditSmeCard({ assessment, onUpdateStatus }) {
  if (!assessment) return null;

  const cfg = STATUT_CONFIG[assessment.statut] || STATUT_CONFIG.NON_DETERMINE;
  const StatusIcon = cfg.icon;
  const isUrgent = assessment.urgence === 'CRITIQUE' || assessment.urgence === 'ELEVEE';

  return (
    <div
      className={`rounded-xl border ${isUrgent ? 'border-red-300 ring-1 ring-red-200' : cfg.border} ${cfg.bg} p-4 space-y-4`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileCheck size={18} className={cfg.text} />
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Audit Energetique / SME</h3>
            <p className="text-[10px] text-gray-500">Loi 2025-391 - art. L.233-1</p>
          </div>
        </div>
        <span
          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.badge}`}
        >
          <StatusIcon size={12} />
          {cfg.label}
        </span>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-gray-500">Conso moy. 3 ans</span>
          <p className="font-semibold text-gray-900">
            {assessment.conso?.annuelle_moy_gwh?.toFixed(2) ?? '—'} GWh/an
          </p>
        </div>
        <div>
          <span className="text-gray-500">Obligation</span>
          <p className="font-medium text-gray-900 text-[11px]">
            {OBLIGATION_LABELS[assessment.obligation] || assessment.obligation}
          </p>
        </div>
        {assessment.jours_restants != null && (
          <div className={isUrgent ? 'text-red-700' : ''}>
            <span className="text-gray-500">Deadline</span>
            <p className="font-semibold">
              {assessment.deadline
                ? new Date(assessment.deadline).toLocaleDateString('fr-FR')
                : '—'}{' '}
              (
              {assessment.jours_restants < 0
                ? `J+${Math.abs(assessment.jours_restants)} — EN RETARD`
                : `J-${assessment.jours_restants}`}
              )
            </p>
          </div>
        )}
        <div>
          <span className="text-gray-500">Score RegOps</span>
          <p className="font-semibold text-gray-900">
            {assessment.score_audit_sme != null
              ? `${Math.round(assessment.score_audit_sme * 100)}/100`
              : '—'}
          </p>
        </div>
      </div>

      {/* Checklist */}
      {assessment.checklist?.length > 0 && (
        <div className="space-y-1.5">
          {assessment.checklist.map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-xs">
              <span className="mt-0.5 shrink-0">
                <ChecklistIcon ok={item.ok} bloquant={item.bloquant} />
              </span>
              <span className={item.ok ? 'text-gray-600' : 'text-gray-900 font-medium'}>
                {item.critere}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Actions recommandees */}
      {assessment.actions_recommandees?.length > 0 && (
        <div className="space-y-1.5 pt-2 border-t border-gray-200/50">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
            Actions recommandees
          </p>
          {assessment.actions_recommandees.map((action, i) => (
            <div key={i} className="flex items-center justify-between gap-2 text-xs">
              <span className="text-gray-800">{action.label}</span>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-gray-500">{action.echeance_jours}j</span>
                {onUpdateStatus && (
                  <button
                    className="text-blue-600 hover:text-blue-800 font-medium"
                    onClick={() => onUpdateStatus(action.code)}
                  >
                    Planifier
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Source */}
      <p className="text-[9px] text-gray-400 pt-1">
        Loi 2025-391 — seuils : 2.75 GWh (audit) / 23.6 GWh (SME)
      </p>
    </div>
  );
}
