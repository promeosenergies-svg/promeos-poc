/**
 * PROMEOS — Note de Decision A4 (Brique 3)
 * 1-page investor-ready summary for a single site scenario recommendation.
 * Usage: <ExportNoteDecision data={...} onClose={fn} />
 * Print via window.print() with @media print styles.
 */
import { useRef } from 'react';
import { Printer, X } from 'lucide-react';
import { fmtNum } from '../utils/format';

const STRATEGY_LABELS = {
  fixe: 'Prix Fixe',
  indexe: 'Indexe Marche',
  spot: 'Spot Temps Reel',
  reflex_solar: 'Tarif Heures Solaires',
};

export default function ExportNoteDecision({ data, onClose }) {
  const printRef = useRef();

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Veuillez autoriser les popups pour imprimer.');
      return;
    }
    // Clone DOM content safely instead of injecting raw innerHTML
    const styles = `
      @page { size: A4; margin: 20mm 15mm; }
      * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', system-ui, sans-serif; }
      body { font-size: 11pt; color: #1a1a1a; line-height: 1.5; }
      .header { border-bottom: 3px solid #2563eb; padding-bottom: 12px; margin-bottom: 16px; }
      .header h1 { font-size: 18pt; color: #1e3a5f; }
      .header .sub { font-size: 10pt; color: #6b7280; margin-top: 4px; }
      .meta { display: flex; gap: 24px; margin-bottom: 16px; font-size: 10pt; color: #374151; }
      .meta-item { }
      .meta-label { font-weight: 600; color: #6b7280; text-transform: uppercase; font-size: 8pt; }
      .section { margin-bottom: 16px; }
      .section-title { font-size: 12pt; font-weight: 700; color: #1e3a5f; border-bottom: 1px solid #e5e7eb; padding-bottom: 4px; margin-bottom: 8px; }
      table { width: 100%; border-collapse: collapse; font-size: 10pt; }
      th { background: #f3f4f6; text-align: left; padding: 6px 10px; font-weight: 600; color: #374151; border-bottom: 2px solid #d1d5db; }
      td { padding: 6px 10px; border-bottom: 1px solid #e5e7eb; }
      .reco { background: #eff6ff; }
      .reco td { font-weight: 600; }
      .highlight { font-size: 24pt; font-weight: 800; color: #2563eb; }
      .risk-bar { display: inline-block; width: 60px; height: 8px; background: #e5e7eb; border-radius: 4px; vertical-align: middle; }
      .risk-fill { height: 100%; border-radius: 4px; }
      .footer { margin-top: 24px; padding-top: 12px; border-top: 1px solid #d1d5db; font-size: 8pt; color: #9ca3af; text-align: center; }
      .kpi-grid { display: flex; gap: 16px; margin-bottom: 16px; }
      .kpi-box { flex: 1; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; text-align: center; }
      .kpi-value { font-size: 16pt; font-weight: 800; }
      .kpi-label { font-size: 8pt; color: #6b7280; text-transform: uppercase; margin-top: 2px; }
      .reasoning { background: #eff6ff; border-left: 3px solid #2563eb; padding: 10px 14px; font-size: 10pt; color: #1e40af; margin-bottom: 16px; }
    `;
    const doc = printWindow.document;
    doc.open();
    doc.write(
      '<!DOCTYPE html><html><head><title>Note de Decision</title><style>' +
        styles +
        '</style></head><body></body></html>'
    );
    doc.close();
    if (!printRef.current) return;
    const cloned = doc.importNode(printRef.current, true);
    doc.body.appendChild(cloned);
    printWindow.onload = () => {
      printWindow.print();
      printWindow.close();
    };
    // Fallback if onload already fired
    if (doc.readyState === 'complete') {
      printWindow.print();
      printWindow.close();
    }
  };

  if (!data) return null;

  const reco = data.scenarios?.find((s) => s.is_recommended) || data.scenarios?.[0];
  const today = new Date().toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  const riskColor = (score) => (score <= 30 ? '#16a34a' : score <= 60 ? '#d97706' : '#dc2626');

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Toolbar */}
        <div className="sticky top-0 bg-white border-b px-6 py-3 flex items-center justify-between z-10">
          <h3 className="font-semibold text-gray-800">Apercu — Note de Decision</h3>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition"
            >
              <Printer size={14} /> Imprimer / PDF
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition"
              aria-label="Fermer"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Printable content */}
        <div ref={printRef} className="p-8">
          <div className="header">
            <h1>Note de Décision — Achat Énergie</h1>
            <div className="sub">
              PROMEOS — Recommandation d'achat pour {data.site_nom || `Site ${data.site_id}`}
            </div>
          </div>

          <div className="meta">
            <div className="meta-item">
              <div className="meta-label">Date</div>
              <div>{today}</div>
            </div>
            <div className="meta-item">
              <div className="meta-label">Site</div>
              <div>{data.site_nom || `Site ${data.site_id}`}</div>
            </div>
            <div className="meta-item">
              <div className="meta-label">Volume</div>
              <div>{fmtNum(Math.round(data.volume_kwh_an || 0), 0)} kWh/an</div>
            </div>
            <div className="meta-item">
              <div className="meta-label">Horizon</div>
              <div>{data.horizon_months || 24} mois</div>
            </div>
          </div>

          {reco && (
            <>
              <div className="section">
                <div className="section-title">Recommandation</div>
                <div className="kpi-grid">
                  <div className="kpi-box">
                    <div className="kpi-value" style={{ color: '#2563eb' }}>
                      {STRATEGY_LABELS[reco.strategy] || reco.strategy}
                    </div>
                    <div className="kpi-label">Stratégie recommandée</div>
                  </div>
                  <div className="kpi-box">
                    <div className="kpi-value">{reco.price_eur_per_kwh?.toFixed(4)}</div>
                    <div className="kpi-label">€/kWh</div>
                  </div>
                  <div className="kpi-box">
                    <div className="kpi-value" style={{ color: '#16a34a' }}>
                      {fmtNum(Math.round(reco.total_annual_eur || 0), 0)}
                    </div>
                    <div className="kpi-label">€/an</div>
                  </div>
                  <div className="kpi-box">
                    <div
                      className="kpi-value"
                      style={{ color: reco.savings_vs_current_pct > 0 ? '#16a34a' : '#dc2626' }}
                    >
                      {reco.savings_vs_current_pct > 0 ? '-' : '+'}
                      {Math.abs(reco.savings_vs_current_pct)}%
                    </div>
                    <div className="kpi-label">vs prix actuel</div>
                  </div>
                </div>
              </div>

              {reco.reasoning && (
                <div className="reasoning">
                  <strong>Analyse :</strong> {reco.reasoning}
                </div>
              )}
            </>
          )}

          <div className="section">
            <div className="section-title">Comparaison des scénarios</div>
            <table>
              <thead>
                <tr>
                  <th>Stratégie</th>
                  <th style={{ textAlign: 'right' }}>Prix (€/kWh)</th>
                  <th style={{ textAlign: 'right' }}>Coût annuel (€)</th>
                  <th style={{ textAlign: 'right' }}>Économies</th>
                  <th style={{ textAlign: 'center' }}>Risque</th>
                  <th style={{ textAlign: 'right' }}>Fourchette (€/an)</th>
                </tr>
              </thead>
              <tbody>
                {(data.scenarios || []).map((s) => (
                  <tr key={s.strategy} className={s.is_recommended ? 'reco' : ''}>
                    <td>
                      {STRATEGY_LABELS[s.strategy] || s.strategy}
                      {s.is_recommended && ' ★'}
                    </td>
                    <td style={{ textAlign: 'right' }}>{s.price_eur_per_kwh?.toFixed(4)}</td>
                    <td style={{ textAlign: 'right' }}>
                      {fmtNum(Math.round(s.total_annual_eur), 0)}
                    </td>
                    <td
                      style={{
                        textAlign: 'right',
                        color: s.savings_vs_current_pct > 0 ? '#16a34a' : '#dc2626',
                      }}
                    >
                      {s.savings_vs_current_pct > 0 ? '-' : '+'}
                      {Math.abs(s.savings_vs_current_pct)}%
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          width: 60,
                          height: 8,
                          background: '#e5e7eb',
                          borderRadius: 4,
                          verticalAlign: 'middle',
                        }}
                      >
                        <span
                          style={{
                            display: 'block',
                            width: `${s.risk_score}%`,
                            height: '100%',
                            borderRadius: 4,
                            background: riskColor(s.risk_score),
                          }}
                        />
                      </span>
                      <span style={{ fontSize: '9pt', marginLeft: 4 }}>{s.risk_score}/100</span>
                    </td>
                    <td style={{ textAlign: 'right', fontSize: '9pt', color: '#6b7280' }}>
                      {s.p10_eur != null
                        ? `${fmtNum(Math.round(s.p10_eur), 0)} — ${fmtNum(Math.round(s.p90_eur), 0)}`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="footer">
            PROMEOS — Document généré automatiquement le {today}. Ce document ne constitue pas un
            engagement contractuel.
          </div>
        </div>
      </div>
    </div>
  );
}
