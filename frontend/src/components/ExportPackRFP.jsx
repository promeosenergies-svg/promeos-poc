/**
 * PROMEOS — Pack RFP A4 (Brique 3)
 * 2-3 page investor-ready portfolio export for RFP/procurement process.
 * Usage: <ExportPackRFP portfolio={...} sites={[...]} onClose={fn} />
 */
import { useRef } from 'react';
import { Printer, X } from 'lucide-react';

const STRATEGY_LABELS = { fixe: 'Prix Fixe', indexe: 'Indexe', spot: 'Spot', reflex_solar: 'Tarif Heures Solaires' };

export default function ExportPackRFP({ portfolio, sites, orgName, onClose }) {
  const printRef = useRef();

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Veuillez autoriser les popups pour imprimer.');
      return;
    }
    // Clone DOM content safely instead of injecting raw innerHTML
    const styles = `
      @page { size: A4; margin: 18mm 15mm; }
      * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', system-ui, sans-serif; }
      body { font-size: 10pt; color: #1a1a1a; line-height: 1.4; }
      .page-break { page-break-after: always; }
      .header { border-bottom: 3px solid #2563eb; padding-bottom: 10px; margin-bottom: 14px; }
      .header h1 { font-size: 16pt; color: #1e3a5f; }
      .header .sub { font-size: 9pt; color: #6b7280; margin-top: 2px; }
      .section { margin-bottom: 14px; }
      .section-title { font-size: 11pt; font-weight: 700; color: #1e3a5f; border-bottom: 1px solid #e5e7eb; padding-bottom: 3px; margin-bottom: 8px; }
      .kpi-strip { display: flex; gap: 12px; margin-bottom: 14px; }
      .kpi { flex: 1; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px; text-align: center; }
      .kpi-val { font-size: 18pt; font-weight: 800; }
      .kpi-lbl { font-size: 7pt; color: #6b7280; text-transform: uppercase; margin-top: 2px; }
      table { width: 100%; border-collapse: collapse; font-size: 9pt; margin-bottom: 12px; }
      th { background: #f3f4f6; text-align: left; padding: 5px 8px; font-weight: 600; color: #374151; border-bottom: 2px solid #d1d5db; }
      td { padding: 5px 8px; border-bottom: 1px solid #e5e7eb; }
      .reco td { background: #eff6ff; font-weight: 600; }
      .risk-badge { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 8pt; font-weight: 600; }
      .risk-low { background: #dcfce7; color: #166534; }
      .risk-med { background: #fef3c7; color: #92400e; }
      .risk-high { background: #fee2e2; color: #991b1b; }
      .footer { margin-top: 20px; padding-top: 10px; border-top: 1px solid #d1d5db; font-size: 7pt; color: #9ca3af; text-align: center; }
      .page-num { text-align: right; font-size: 8pt; color: #9ca3af; margin-bottom: 8px; }
      .summary-box { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 12px; margin-bottom: 14px; }
      .summary-box p { font-size: 10pt; color: #1e40af; }
    `;
    const doc = printWindow.document;
    doc.open();
    doc.write('<!DOCTYPE html><html><head><title>Pack RFP</title><style>' + styles + '</style></head><body></body></html>');
    doc.close();
    if (!printRef.current) return;
    const cloned = doc.importNode(printRef.current, true);
    doc.body.appendChild(cloned);
    printWindow.onload = () => { printWindow.print(); printWindow.close(); };
    if (doc.readyState === 'complete') { printWindow.print(); printWindow.close(); }
  };

  if (!portfolio) return null;

  const today = new Date().toLocaleDateString('fr-FR', { year: 'numeric', month: 'long', day: 'numeric' });
  const riskBadge = (score) => {
    if (score <= 30) return { cls: 'risk-low', label: 'Faible' };
    if (score <= 60) return { cls: 'risk-med', label: 'Moyen' };
    return { cls: 'risk-high', label: 'Eleve' };
  };

  const totalVolume = portfolio.total_volume_kwh_an || sites?.reduce((s, si) => s + (si.volume_kwh_an || 0), 0) || 0;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Toolbar */}
        <div className="sticky top-0 bg-white border-b px-6 py-3 flex items-center justify-between z-10">
          <h3 className="font-semibold text-gray-800">Apercu — Pack RFP</h3>
          <div className="flex items-center gap-2">
            <button onClick={handlePrint}
              className="flex items-center gap-1.5 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition">
              <Printer size={14} /> Imprimer / PDF
            </button>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition" aria-label="Fermer">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Printable content */}
        <div ref={printRef} className="p-8">
          {/* ═══ PAGE 1: Executive Summary ═══ */}
          <div className="header">
            <h1>Pack RFP — Portefeuille Energie</h1>
            <div className="sub">PROMEOS — {orgName || 'Organisation'} — {today}</div>
          </div>

          <div className="section">
            <div className="section-title">Synthese du portefeuille</div>
            <div className="kpi-strip">
              <div className="kpi">
                <div className="kpi-val" style={{ color: '#2563eb' }}>{portfolio.sites_count}</div>
                <div className="kpi-lbl">Sites analyses</div>
              </div>
              <div className="kpi">
                <div className="kpi-val">{Math.round(totalVolume / 1_000_000 * 10) / 10} GWh</div>
                <div className="kpi-lbl">Volume total annuel</div>
              </div>
              <div className="kpi">
                <div className="kpi-val" style={{ color: '#2563eb' }}>{Math.round(portfolio.total_annual_cost_eur || 0).toLocaleString()}</div>
                <div className="kpi-lbl">Cout annuel (EUR)</div>
              </div>
              <div className="kpi">
                <div className="kpi-val" style={{ color: portfolio.weighted_savings_pct > 0 ? '#16a34a' : '#dc2626' }}>
                  {portfolio.weighted_savings_pct > 0 ? '-' : ''}{portfolio.weighted_savings_pct}%
                </div>
                <div className="kpi-lbl">Economies potentielles</div>
              </div>
            </div>
          </div>

          <div className="summary-box">
            <p>
              Ce pack presente l'analyse comparative de <strong>{portfolio.sites_count} sites</strong> electricite
              pour un volume total de <strong>{Math.round(totalVolume).toLocaleString()} kWh/an</strong>.
              Le risque moyen pondere du portefeuille est de <strong>{portfolio.weighted_risk_score}/100</strong> avec
              un potentiel d'economies de <strong>{Math.abs(portfolio.weighted_savings_pct)}%</strong> par rapport aux tarifs actuels.
              Toutes les recommandations portent sur l'electricite (contexte post-ARENH).
            </p>
          </div>

          <div className="section">
            <div className="section-title">Recommandations par site</div>
            <table>
              <thead>
                <tr>
                  <th>Site</th>
                  <th style={{ textAlign: 'right' }}>Volume (kWh/an)</th>
                  <th>Strategie</th>
                  <th style={{ textAlign: 'right' }}>Prix (EUR/kWh)</th>
                  <th style={{ textAlign: 'right' }}>Cout annuel</th>
                  <th style={{ textAlign: 'right' }}>Economies</th>
                  <th style={{ textAlign: 'center' }}>Risque</th>
                </tr>
              </thead>
              <tbody>
                {(sites || []).map(site => {
                  const reco = site.scenarios?.find(s => s.is_recommended);
                  if (!reco) return null;
                  const rb = riskBadge(reco.risk_score);
                  return (
                    <tr key={site.site_id} className="reco">
                      <td>{site.site_nom || `Site ${site.site_id}`}</td>
                      <td style={{ textAlign: 'right' }}>{Math.round(site.volume_kwh_an || 0).toLocaleString()}</td>
                      <td>{STRATEGY_LABELS[reco.strategy] || reco.strategy}</td>
                      <td style={{ textAlign: 'right' }}>{reco.price_eur_per_kwh?.toFixed(4)}</td>
                      <td style={{ textAlign: 'right' }}>{Math.round(reco.total_annual_eur).toLocaleString()} EUR</td>
                      <td style={{ textAlign: 'right', color: reco.savings_vs_current_pct > 0 ? '#16a34a' : '#dc2626' }}>
                        {reco.savings_vs_current_pct > 0 ? '-' : '+'}{Math.abs(reco.savings_vs_current_pct)}%
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <span className={`risk-badge ${rb.cls}`}>{rb.label} ({reco.risk_score})</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="page-break" />

          {/* ═══ PAGE 2: Detail par site ═══ */}
          <div className="page-num">Page 2</div>
          <div className="section">
            <div className="section-title">Detail des scenarios par site</div>
          </div>

          {(sites || []).map(site => (
            <div key={site.site_id} className="section" style={{ marginBottom: 18 }}>
              <div style={{ fontWeight: 700, fontSize: '10pt', color: '#1e3a5f', marginBottom: 4 }}>
                {site.site_nom || `Site ${site.site_id}`}
                <span style={{ fontWeight: 400, color: '#6b7280', marginLeft: 8, fontSize: '9pt' }}>
                  {Math.round(site.volume_kwh_an || 0).toLocaleString()} kWh/an
                </span>
              </div>
              <table>
                <thead>
                  <tr>
                    <th>Strategie</th>
                    <th style={{ textAlign: 'right' }}>Prix</th>
                    <th style={{ textAlign: 'right' }}>Cout annuel</th>
                    <th style={{ textAlign: 'right' }}>Economies</th>
                    <th style={{ textAlign: 'center' }}>Risque</th>
                    <th style={{ textAlign: 'right' }}>P10 — P90</th>
                  </tr>
                </thead>
                <tbody>
                  {(site.scenarios || []).map(s => {
                    const rb = riskBadge(s.risk_score);
                    return (
                      <tr key={s.strategy || s.id} className={s.is_recommended ? 'reco' : ''}>
                        <td>
                          {STRATEGY_LABELS[s.strategy] || s.strategy}
                          {s.is_recommended && ' ★'}
                        </td>
                        <td style={{ textAlign: 'right' }}>{s.price_eur_per_kwh?.toFixed(4)}</td>
                        <td style={{ textAlign: 'right' }}>{Math.round(s.total_annual_eur).toLocaleString()} EUR</td>
                        <td style={{ textAlign: 'right', color: s.savings_vs_current_pct > 0 ? '#16a34a' : '#dc2626' }}>
                          {s.savings_vs_current_pct > 0 ? '-' : '+'}{Math.abs(s.savings_vs_current_pct)}%
                        </td>
                        <td style={{ textAlign: 'center' }}>
                          <span className={`risk-badge ${rb.cls}`}>{s.risk_score}</span>
                        </td>
                        <td style={{ textAlign: 'right', fontSize: '8pt', color: '#6b7280' }}>
                          {s.p10_eur != null ? `${Math.round(s.p10_eur).toLocaleString()} — ${Math.round(s.p90_eur).toLocaleString()}` : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ))}

          <div className="footer">
            PROMEOS — Pack RFP genere le {today}. Document confidentiel — {orgName || 'Organisation'}.
            Ce document ne constitue pas un engagement contractuel.
          </div>
        </div>
      </div>
    </div>
  );
}
