import { useState, useEffect } from 'react';
import { Upload, BarChart3, AlertTriangle, Lightbulb, Database, Search, RefreshCw, CheckCircle } from 'lucide-react';
import {
  getSites, getMeters, createMeter, uploadConsumptionData,
  runAnalysis, getAnalysisSummary, generateDemoEnergy,
  getKBStats, getKBArchetypes, getKBRules, getKBRecommendations, reloadKB
} from '../services/api';

// ---- Import Wizard (7 steps) ----
function ImportWizard({ onComplete }) {
  const [step, setStep] = useState(1);
  const [sites, setSites] = useState([]);
  const [selectedSite, setSelectedSite] = useState(null);
  const [meterName, setMeterName] = useState('Compteur Principal');
  const [file, setFile] = useState(null);
  const [frequency, setFrequency] = useState('hourly');
  const [archetype, setArchetype] = useState('BUREAU_STANDARD');
  const [importResult, setImportResult] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [useDemo, setUseDemo] = useState(false);

  useEffect(() => {
    getSites({ limit: 200 }).then(data => setSites(data.sites || [])).catch(() => {});
  }, []);

  const handleImport = async () => {
    setLoading(true);
    setError(null);
    try {
      if (useDemo) {
        // Generate demo data
        const result = await generateDemoEnergy({
          site_id: selectedSite.id,
          meter_name: meterName,
          days: 365,
          archetype: archetype
        });
        setImportResult({
          status: 'completed',
          rows_imported: result.readings_generated,
          rows_skipped: 0,
          rows_errored: 0,
          meter_id: result.meter_id
        });
      } else {
        // Upload real file
        const meters = await getMeters(selectedSite.id);
        let meter = meters.find(m => m.name === meterName);
        if (!meter) {
          meter = await createMeter({
            meter_id: `PRM-${selectedSite.id.toString().padStart(6, '0')}`,
            name: meterName,
            site_id: selectedSite.id
          });
        }
        const result = await uploadConsumptionData(file, meter.meter_id, frequency);
        setImportResult({ ...result, meter_id: meter.meter_id });
      }
      setStep(6);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  const handleAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const meterId = importResult?.meter_id || `PRM-${selectedSite.id.toString().padStart(6, '0')}`;
      const result = await runAnalysis(meterId);
      setAnalysisResult(result);
      setStep(7);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Progress bar */}
      <div className="flex items-center mb-8">
        {[1,2,3,4,5,6,7].map(s => (
          <div key={s} className="flex-1 flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              s < step ? 'bg-green-500 text-white' :
              s === step ? 'bg-blue-600 text-white' :
              'bg-gray-200 text-gray-500'
            }`}>{s < step ? '\u2713' : s}</div>
            {s < 7 && <div className={`flex-1 h-1 mx-1 ${s < step ? 'bg-green-400' : 'bg-gray-200'}`} />}
          </div>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">{error}</div>
      )}

      {/* Step 1: Select site */}
      {step === 1 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">1. Selectionner un site</h3>
          <div className="grid grid-cols-2 gap-3 max-h-60 overflow-y-auto">
            {sites.map(site => (
              <button
                key={site.id}
                onClick={() => { setSelectedSite(site); setStep(2); }}
                className={`p-3 border rounded text-left hover:border-blue-400 transition ${
                  selectedSite?.id === site.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'
                }`}
              >
                <div className="font-medium text-sm">{site.nom}</div>
                <div className="text-xs text-gray-500">{site.ville} - {site.surface_m2 || '?'} m2</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step 2: Data source */}
      {step === 2 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">2. Source des donnees</h3>
          <p className="text-sm text-gray-600 mb-4">Site: <strong>{selectedSite?.nom}</strong></p>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => { setUseDemo(false); setStep(3); }}
              className="p-6 border-2 rounded-lg hover:border-blue-400 transition text-center"
            >
              <Upload className="mx-auto mb-2 text-blue-500" size={32} />
              <div className="font-semibold">Importer un fichier</div>
              <div className="text-sm text-gray-500 mt-1">CSV, XLSX, JSON</div>
            </button>
            <button
              onClick={() => { setUseDemo(true); setStep(4); }}
              className="p-6 border-2 rounded-lg hover:border-green-400 transition text-center"
            >
              <Database className="mx-auto mb-2 text-green-500" size={32} />
              <div className="font-semibold">Donnees de demo</div>
              <div className="text-sm text-gray-500 mt-1">365j synthetiques</div>
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Upload file */}
      {step === 3 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">3. Configuration de l'import</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nom du compteur</label>
              <input
                type="text"
                value={meterName}
                onChange={e => setMeterName(e.target.value)}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Frequence</label>
              <select value={frequency} onChange={e => setFrequency(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="15min">15 minutes</option>
                <option value="30min">30 minutes</option>
                <option value="hourly">Horaire</option>
                <option value="daily">Journalier</option>
                <option value="monthly">Mensuel</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Fichier</label>
              <input
                type="file"
                accept=".csv,.xlsx,.json"
                onChange={e => setFile(e.target.files[0])}
                className="w-full border rounded px-3 py-2 text-sm"
              />
            </div>
            <p className="text-xs text-gray-500">
              Format CSV attendu: colonnes 'timestamp' ou 'date' + 'value_kwh' ou 'kwh' (separateur: ;)
            </p>
            <button
              onClick={() => setStep(5)}
              disabled={!file}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition"
            >Suivant</button>
          </div>
        </div>
      )}

      {/* Step 4: Demo config */}
      {step === 4 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">4. Configuration demo</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Archetype de consommation</label>
              <select value={archetype} onChange={e => setArchetype(e.target.value)} className="w-full border rounded px-3 py-2 text-sm">
                <option value="BUREAU_STANDARD">Bureau Standard (150-250 kWh/m2/an)</option>
                <option value="COMMERCE_ALIMENTAIRE">Commerce Alimentaire (400-800 kWh/m2/an)</option>
                <option value="RESTAURATION_SERVICE">Restauration (250-450 kWh/m2/an)</option>
                <option value="INDUSTRIE_LEGERE">Industrie Legere (80-200 kWh/m2/an)</option>
              </select>
            </div>
            <button
              onClick={() => setStep(5)}
              className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
            >Suivant</button>
          </div>
        </div>
      )}

      {/* Step 5: Confirm & import */}
      {step === 5 && (
        <div>
          <h3 className="text-lg font-semibold mb-4">5. Confirmation</h3>
          <div className="bg-gray-50 rounded p-4 space-y-2 text-sm">
            <p><strong>Site:</strong> {selectedSite?.nom} ({selectedSite?.ville})</p>
            <p><strong>Surface:</strong> {selectedSite?.surface_m2 || 'Non renseignee'} m2</p>
            <p><strong>Source:</strong> {useDemo ? `Demo ${archetype}` : file?.name}</p>
            {!useDemo && <p><strong>Frequence:</strong> {frequency}</p>}
          </div>
          <button
            onClick={handleImport}
            disabled={loading}
            className="mt-4 px-6 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 transition"
          >{loading ? 'Import en cours...' : 'Lancer l\'import'}</button>
        </div>
      )}

      {/* Step 6: Import result */}
      {step === 6 && importResult && (
        <div>
          <h3 className="text-lg font-semibold mb-4">6. Import termine</h3>
          <div className="bg-green-50 border border-green-200 rounded p-4 space-y-2 text-sm">
            <div className="flex items-center gap-2 text-green-700 font-semibold">
              <CheckCircle size={18} /> Import reussi
            </div>
            <p><strong>Lignes importees:</strong> {importResult.rows_imported?.toLocaleString()}</p>
            {importResult.rows_skipped > 0 && <p><strong>Ignorees:</strong> {importResult.rows_skipped}</p>}
            {importResult.rows_errored > 0 && <p className="text-red-600"><strong>Erreurs:</strong> {importResult.rows_errored}</p>}
          </div>
          <button
            onClick={handleAnalysis}
            disabled={loading}
            className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition"
          >{loading ? 'Analyse KB en cours...' : 'Lancer l\'analyse KB-driven'}</button>
        </div>
      )}

      {/* Step 7: Analysis results */}
      {step === 7 && analysisResult && (
        <div>
          <h3 className="text-lg font-semibold mb-4">7. Resultats de l'analyse</h3>
          <AnalysisResultView result={analysisResult} onComplete={onComplete} />
        </div>
      )}
    </div>
  );
}

// ---- Analysis Result View ----
function AnalysisResultView({ result, onComplete }) {
  if (!result || result.status !== 'ok') {
    return <div className="text-red-600">Analyse echouee: {result?.message || 'Erreur inconnue'}</div>;
  }

  return (
    <div className="space-y-6">
      {/* Archetype */}
      <div className="bg-blue-50 border border-blue-200 rounded p-4">
        <h4 className="font-semibold text-blue-800 flex items-center gap-2">
          <BarChart3 size={18} /> Archetype detecte
        </h4>
        <div className="mt-2 grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-500">Code</div>
            <div className="font-bold">{result.archetype?.code || 'Non determine'}</div>
          </div>
          <div>
            <div className="text-gray-500">Confiance</div>
            <div className="font-bold">{((result.archetype?.match_score || 0) * 100).toFixed(0)}%</div>
          </div>
          <div>
            <div className="text-gray-500">kWh/m2/an</div>
            <div className="font-bold">{result.features?.kwh_m2_year || 'N/A'}</div>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'kWh total', value: result.features?.kwh_total?.toLocaleString() || '0' },
          { label: 'Base nuit', value: `${((result.features?.base_nuit_ratio || 0) * 100).toFixed(1)}%` },
          { label: 'Weekend ratio', value: `${((result.features?.weekend_ratio || 0) * 100).toFixed(1)}%` },
          { label: 'Load factor', value: `${((result.features?.load_factor || 0) * 100).toFixed(1)}%` },
        ].map((kpi, i) => (
          <div key={i} className="bg-white border rounded p-3 text-center">
            <div className="text-xs text-gray-500">{kpi.label}</div>
            <div className="text-lg font-bold">{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Anomalies */}
      <div>
        <h4 className="font-semibold text-red-700 flex items-center gap-2 mb-3">
          <AlertTriangle size={18} /> Anomalies detectees ({result.anomalies?.length || 0})
        </h4>
        {result.anomalies?.length > 0 ? (
          <div className="space-y-2">
            {result.anomalies.map((a, i) => (
              <div key={i} className={`border rounded p-3 ${
                a.severity === 'high' ? 'border-red-300 bg-red-50' :
                a.severity === 'medium' ? 'border-orange-300 bg-orange-50' :
                'border-yellow-300 bg-yellow-50'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="font-medium text-sm">{a.title}</div>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                    a.severity === 'high' ? 'bg-red-200 text-red-800' :
                    a.severity === 'medium' ? 'bg-orange-200 text-orange-800' :
                    'bg-yellow-200 text-yellow-800'
                  }`}>{a.severity}</span>
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  Mesure: {a.measured} | Seuil: {a.threshold} | KB Rule: {a.code}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-green-600 bg-green-50 p-3 rounded">Aucune anomalie detectee</div>
        )}
      </div>

      {/* Recommendations */}
      <div>
        <h4 className="font-semibold text-green-700 flex items-center gap-2 mb-3">
          <Lightbulb size={18} /> Recommandations KB ({result.recommendations?.length || 0})
        </h4>
        {result.recommendations?.length > 0 ? (
          <div className="space-y-2">
            {result.recommendations.map((r, i) => (
              <div key={i} className="border border-green-200 bg-green-50 rounded p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-sm">{r.title}</div>
                  <div className="flex items-center gap-2">
                    {r.savings_pct && (
                      <span className="px-2 py-0.5 bg-green-200 text-green-800 rounded text-xs font-bold">
                        -{r.savings_pct}%
                      </span>
                    )}
                    <span className="px-2 py-0.5 bg-blue-200 text-blue-800 rounded text-xs font-bold">
                      ICE: {r.ice_score?.toFixed(3)}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-gray-600 mt-1">
                  Declenchee par: {r.triggered_by} | KB: {r.code}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-sm text-gray-500 bg-gray-50 p-3 rounded">Aucune recommandation</div>
        )}
      </div>

      {onComplete && (
        <button
          onClick={onComplete}
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >Terminer</button>
      )}
    </div>
  );
}

// ---- KB Admin Panel ----
function KBAdminPanel() {
  const [stats, setStats] = useState(null);
  const [archetypes, setArchetypes] = useState([]);
  const [rules, setRules] = useState([]);
  const [recos, setRecos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reloadResult, setReloadResult] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [s, a, r, rec] = await Promise.all([
        getKBStats(),
        getKBArchetypes(),
        getKBRules(),
        getKBRecommendations()
      ]);
      setStats(s);
      setArchetypes(a);
      setRules(r);
      setRecos(rec);
    } catch (err) {
      console.error('KB load error:', err);
    }
  };

  const handleReload = async () => {
    setLoading(true);
    try {
      const result = await reloadKB();
      setReloadResult(result);
      await loadData();
    } catch (err) {
      setReloadResult({ status: 'error', message: err.message });
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Knowledge Base</h3>
          <button
            onClick={handleReload}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm transition"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Reload KB
          </button>
        </div>

        {reloadResult && (
          <div className={`mb-4 p-3 rounded text-sm ${
            reloadResult.status === 'ok' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>{reloadResult.message}</div>
        )}

        {stats && (
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center p-3 bg-blue-50 rounded">
              <div className="text-2xl font-bold text-blue-700">{stats.archetypes_count}</div>
              <div className="text-xs text-gray-500">Archetypes</div>
            </div>
            <div className="text-center p-3 bg-red-50 rounded">
              <div className="text-2xl font-bold text-red-700">{stats.anomaly_rules_count}</div>
              <div className="text-xs text-gray-500">Regles anomalie</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded">
              <div className="text-2xl font-bold text-green-700">{stats.recommendations_count}</div>
              <div className="text-xs text-gray-500">Recommandations</div>
            </div>
            <div className="text-center p-3 bg-purple-50 rounded">
              <div className="text-2xl font-bold text-purple-700">{stats.naf_mappings_count}</div>
              <div className="text-xs text-gray-500">Mappings NAF</div>
            </div>
          </div>
        )}

        {stats?.kb_doc_id && (
          <div className="mt-3 text-xs text-gray-500">
            Source: {stats.kb_doc_id} v{stats.kb_version} | SHA256: {stats.kb_sha256?.slice(0, 16)}...
          </div>
        )}
      </div>

      {/* Archetypes */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Archetypes ({archetypes.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 px-3">Code</th>
                <th className="py-2 px-3">kWh/m2/an</th>
                <th className="py-2 px-3">Codes NAF</th>
                <th className="py-2 px-3">Confiance</th>
              </tr>
            </thead>
            <tbody>
              {archetypes.map(a => (
                <tr key={a.code} className="border-b hover:bg-gray-50">
                  <td className="py-2 px-3 font-medium">{a.code}</td>
                  <td className="py-2 px-3">{a.kwh_m2_min}-{a.kwh_m2_max}</td>
                  <td className="py-2 px-3 text-xs">{a.naf_codes?.join(', ') || '-'}</td>
                  <td className="py-2 px-3">
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      a.confidence === 'high' ? 'bg-green-100 text-green-700' :
                      a.confidence === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                      'bg-red-100 text-red-700'
                    }`}>{a.confidence}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Rules */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Regles d'Anomalie ({rules.length})</h3>
        <div className="space-y-2">
          {rules.map(r => (
            <div key={r.code} className="flex items-center justify-between border rounded p-3">
              <div>
                <div className="font-medium text-sm">{r.title}</div>
                <div className="text-xs text-gray-500">{r.rule_type} | {r.source_section}</div>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                r.severity === 'high' ? 'bg-red-200 text-red-800' :
                r.severity === 'medium' ? 'bg-orange-200 text-orange-800' :
                'bg-yellow-200 text-yellow-800'
              }`}>{r.severity}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-3">Recommandations ({recos.length})</h3>
        <div className="space-y-2">
          {recos.map(r => (
            <div key={r.code} className="flex items-center justify-between border rounded p-3">
              <div>
                <div className="font-medium text-sm">{r.title}</div>
                <div className="text-xs text-gray-500">{r.action_type} | {r.target_asset}</div>
              </div>
              <div className="flex items-center gap-2">
                {r.savings_min_pct && r.savings_max_pct && (
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">
                    {r.savings_min_pct}-{r.savings_max_pct}%
                  </span>
                )}
                {r.ice_score && (
                  <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-bold">
                    ICE: {r.ice_score.toFixed(3)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---- Main Page ----
export default function ConsommationsUsages() {
  const [tab, setTab] = useState('import');
  const [analysisComplete, setAnalysisComplete] = useState(false);

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      <h2 className="text-2xl font-bold mb-6">Consommations</h2>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {[
          { key: 'import', label: 'Import & Analyse', icon: Upload },
          { key: 'kb', label: 'Knowledge Base', icon: Database },
        ].map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
              tab === t.key
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-100 border'
            }`}
          >
            <t.icon size={16} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'import' && (
        <ImportWizard onComplete={() => setAnalysisComplete(true)} />
      )}

      {tab === 'kb' && (
        <KBAdminPanel />
      )}
    </div>
  );
}
