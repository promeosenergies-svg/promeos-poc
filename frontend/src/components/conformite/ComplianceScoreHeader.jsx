/**
 * ComplianceScoreHeader — Unified compliance score display with breakdown bars.
 */
import { getComplianceScoreColor, COMPLIANCE_SCORE_THRESHOLDS } from '../../lib/constants';

export default function ComplianceScoreHeader({ complianceScore, segProfile }) {
  if (!complianceScore) return null;

  return (
    <div
      data-section="compliance-score-header"
      className="p-4 bg-white border border-gray-200 rounded-lg"
    >
      <div className="flex items-center gap-6">
        {/* Score display */}
        <div className="text-center min-w-[100px]">
          <p className="text-xs text-gray-500 mb-1">Score conformit\u00E9</p>
          <span
            className={`text-3xl font-bold ${getComplianceScoreColor(complianceScore.score ?? complianceScore.avg_score)}`}
          >
            {Math.round(complianceScore.score ?? complianceScore.avg_score ?? 0)}
          </span>
          <span className="text-lg text-gray-400">/100</span>
          {segProfile?.has_profile && Object.keys(segProfile.answers || {}).length > 0 && (
            <>
              <p className="text-[10px] text-blue-600 font-medium mt-1" data-testid="profile-badge">
                Adapt\u00E9 \u00E0 votre profil
              </p>
              <p className="text-[9px] text-gray-400 mt-0.5" data-testid="profile-explain">
                Certaines obligations et priorit\u00E9s sont ajust\u00E9es selon votre profil
                d\u00E9clar\u00E9 ou d\u00E9tect\u00E9.
              </p>
            </>
          )}
        </div>
        {/* Breakdown bars */}
        <div className="flex-1 space-y-2">
          {(complianceScore.breakdown || []).map((fw) => {
            const fwLabel =
              fw.framework === 'tertiaire_operat'
                ? 'D\u00E9cret Tertiaire'
                : fw.framework === 'bacs'
                  ? 'BACS'
                  : 'APER';
            const weightPct = fw.weight != null ? `${Math.round(fw.weight * 100)}%` : '';
            const isAvailable = fw.available !== false && fw.source !== 'default';
            return (
              <div key={fw.framework} className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-36 truncate">
                  {fwLabel}
                  {weightPct && isAvailable ? ` (${weightPct})` : ''}
                </span>
                {isAvailable ? (
                  <>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${fw.score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : fw.score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(100, fw.score)}%` }}
                      />
                    </div>
                    <span
                      className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(fw.score)}`}
                    >
                      {Math.round(fw.score)}
                    </span>
                  </>
                ) : (
                  <span className="text-xs text-gray-400 italic">Non applicable</span>
                )}
              </div>
            );
          })}
          {/* Fallback: show breakdown_avg from portfolio if no breakdown */}
          {!complianceScore.breakdown &&
            complianceScore.breakdown_avg &&
            Object.entries(complianceScore.breakdown_avg).map(([fw, score]) => {
              const fwLabel =
                fw === 'tertiaire_operat'
                  ? 'D\u00E9cret Tertiaire'
                  : fw === 'bacs'
                    ? 'BACS'
                    : 'APER';
              return (
                <div key={fw} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-36 truncate">{fwLabel}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(100, score)}%` }}
                    />
                  </div>
                  <span
                    className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(score)}`}
                  >
                    {Math.round(score)}
                  </span>
                </div>
              );
            })}
        </div>
        {/* Confidence */}
        {(complianceScore.confidence || complianceScore.high_confidence_count != null) && (
          <div className="text-center">
            <p className="text-xs text-gray-500 mb-1">Confiance</p>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                complianceScore.confidence === 'high' ||
                complianceScore.high_confidence_count > (complianceScore.total_sites || 0) * 0.6
                  ? 'bg-green-100 text-green-700'
                  : 'bg-amber-100 text-amber-700'
              }`}
            >
              {complianceScore.confidence === 'high' ||
              complianceScore.high_confidence_count > (complianceScore.total_sites || 0) * 0.6
                ? 'Donn\u00E9es fiables'
                : 'Donn\u00E9es partielles'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
