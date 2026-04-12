/**
 * PROMEOS - Onboarding depuis Sirene
 * Flow 3 etapes : Recherche → Selection → Confirmation
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Building2,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Loader2,
  MapPin,
  Hash,
  X,
} from 'lucide-react';
import { searchSirene, getEtablissements, createClientFromSirene } from '../services/api/sirene';
import { useToast } from '../ui/ToastProvider';
import { PageShell } from '../ui';
import Badge from '../ui/Badge';

const STEPS = [
  { id: 'search', label: 'Rechercher', icon: Search },
  { id: 'select', label: 'Selectionner', icon: Building2 },
  { id: 'confirm', label: 'Confirmer', icon: CheckCircle2 },
];

// ── Step indicator ──
function StepIndicator({ steps, current }) {
  return (
    <nav className="flex items-center gap-2 mb-8">
      {steps.map((step, i) => {
        const Icon = step.icon;
        const isCurrent = step.id === current;
        const isDone = steps.findIndex((s) => s.id === current) > i;
        return (
          <div key={step.id} className="flex items-center gap-2">
            {i > 0 && <div className={`h-px w-8 ${isDone ? 'bg-indigo-400' : 'bg-gray-200'}`} />}
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors
              ${isCurrent ? 'bg-indigo-50 text-indigo-700 ring-1 ring-indigo-200' : isDone ? 'bg-indigo-100 text-indigo-600' : 'text-gray-400'}`}
            >
              <Icon size={14} />
              {step.label}
            </div>
          </div>
        );
      })}
    </nav>
  );
}

// ══════════════════════════════════════════════════════════════════════
// ETAPE 1 — Recherche
// ══════════════════════════════════════════════════════════════════════
function SearchStep({ onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const doSearch = useCallback(async () => {
    if (query.trim().length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchSirene(query.trim());
      setResults(data);
    } catch (err) {
      setError(err.response?.data?.message || err.message || 'Erreur de recherche');
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') doSearch();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Rechercher une entreprise</h2>
        <p className="text-sm text-gray-500">
          Recherchez par nom, SIREN, SIRET, code postal ou commune dans la base Sirene officielle.
        </p>
      </div>

      {/* Champ de recherche */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ex: Carrefour, 552032534, 75015..."
            className="w-full pl-10 pr-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
            autoFocus
          />
        </div>
        <button
          onClick={doSearch}
          disabled={loading || query.trim().length < 2}
          className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          Rechercher
        </button>
      </div>

      {/* Erreur */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Resultats */}
      {results && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">
            {results.total} resultat{results.total > 1 ? 's' : ''} pour « {results.query} »
          </p>

          {results.total === 0 && (
            <div className="p-8 text-center text-gray-400">
              <Building2 size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">Aucune entreprise trouvee</p>
              <p className="text-xs mt-1">Verifiez l'orthographe ou essayez un SIREN/SIRET</p>
            </div>
          )}

          {results.results.map((ul) => (
            <button
              key={ul.siren}
              onClick={() => onSelect(ul)}
              className="w-full text-left p-4 border border-gray-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-gray-900 truncate">
                    {ul.denomination || ul.nom_unite_legale || `SIREN ${ul.siren}`}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Hash size={10} />
                      SIREN {ul.siren}
                    </span>
                    {ul.activite_principale && <span>NAF {ul.activite_principale}</span>}
                    {ul.categorie_entreprise && <span>{ul.categorie_entreprise}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  {ul.etat_administratif === 'A' ? (
                    <Badge status="ok">Actif</Badge>
                  ) : (
                    <Badge status="crit">Cesse</Badge>
                  )}
                  {ul.statut_diffusion === 'P' && <Badge status="warn">Diffusion restreinte</Badge>}
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════
// ETAPE 2 — Selection
// ══════════════════════════════════════════════════════════════════════
function SelectStep({ uniteLegale, onConfirm, onBack }) {
  const [etabs, setEtabs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());

  useEffect(() => {
    (async () => {
      try {
        const data = await getEtablissements(uniteLegale.siren);
        setEtabs(data.etablissements || []);
        // Pre-selectionner les etablissements actifs
        const actifs = (data.etablissements || [])
          .filter((e) => e.etat_administratif === 'A')
          .map((e) => e.siret);
        setSelected(new Set(actifs));
      } catch (err) {
        setEtabs([]);
      } finally {
        setLoading(false);
      }
    })();
  }, [uniteLegale.siren]);

  const toggle = useCallback((siret) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(siret)) next.delete(siret);
      else next.add(siret);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelected((prev) => {
      if (prev.size === etabs.length) return new Set();
      return new Set(etabs.map((e) => e.siret));
    });
  }, [etabs]);

  return (
    <div className="space-y-6">
      {/* UL selectionnee */}
      <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
        <div className="flex items-center gap-2 mb-1">
          <Building2 size={16} className="text-indigo-600" />
          <span className="font-semibold text-indigo-900">
            {uniteLegale.denomination || uniteLegale.siren}
          </span>
        </div>
        <div className="text-xs text-indigo-600">
          SIREN {uniteLegale.siren}
          {uniteLegale.activite_principale && ` · NAF ${uniteLegale.activite_principale}`}
          {uniteLegale.categorie_entreprise && ` · ${uniteLegale.categorie_entreprise}`}
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-900">
            Etablissements a integrer ({selected.size}/{etabs.length})
          </h3>
          <button onClick={toggleAll} className="text-xs text-indigo-600 hover:underline">
            {selected.size === etabs.length ? 'Tout deselectionner' : 'Tout selectionner'}
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="animate-spin text-indigo-500" />
            <span className="ml-2 text-sm text-gray-500">Chargement des etablissements...</span>
          </div>
        ) : etabs.length === 0 ? (
          <div className="p-6 text-center text-gray-400 text-sm">
            Aucun etablissement trouve pour ce SIREN
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {etabs.map((e) => {
              const isSelected = selected.has(e.siret);
              const isFerme = e.etat_administratif === 'F';
              return (
                <label
                  key={e.siret}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors
                    ${isSelected ? 'border-indigo-300 bg-indigo-50/40' : 'border-gray-200 hover:bg-gray-50'}
                    ${isFerme ? 'opacity-60' : ''}`}
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggle(e.siret)}
                    className="mt-1 rounded border-gray-300 text-indigo-600 focus:ring-indigo-200"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-900 truncate">
                        {e.enseigne || e.denomination_usuelle || `NIC ${e.nic}`}
                      </span>
                      {e.etablissement_siege && <Badge status="info">Siege</Badge>}
                      {isFerme && <Badge status="crit">Ferme</Badge>}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                      <span>SIRET {e.siret}</span>
                      {e.code_postal && e.libelle_commune && (
                        <span className="flex items-center gap-0.5">
                          <MapPin size={10} />
                          {e.code_postal} {e.libelle_commune}
                        </span>
                      )}
                      {e.activite_principale && <span>NAF {e.activite_principale}</span>}
                    </div>
                  </div>
                </label>
              );
            })}
          </div>
        )}
      </div>

      {/* Resume mapping */}
      {selected.size > 0 && (
        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm space-y-1">
          <p className="font-medium text-gray-700">Resume de la creation :</p>
          <p className="text-gray-600">
            1 Organisation · 1 Entite juridique · 1 Portefeuille · {selected.size} site
            {selected.size > 1 ? 's' : ''}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Les batiments, compteurs et contrats seront ajoutes ensuite.
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft size={14} /> Retour
        </button>
        <button
          onClick={() => onConfirm(Array.from(selected))}
          disabled={selected.size === 0}
          className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Confirmer la selection <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════
// ETAPE 3 — Confirmation
// ══════════════════════════════════════════════════════════════════════
function ConfirmStep({ uniteLegale, selectedSirets, onBack }) {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [typeClient, setTypeClient] = useState('');

  const orgNom = uniteLegale.denomination || uniteLegale.siren;

  const handleCreate = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await createClientFromSirene({
        siren: uniteLegale.siren,
        etablissement_sirets: selectedSirets,
        type_client: typeClient || null,
      });
      setResult(data);
      toast('Client cree avec succes', 'success');
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        setError(`${detail.message}${detail.hint ? ` — ${detail.hint}` : ''}`);
      } else {
        setError(err.response?.data?.message || err.message || 'Erreur lors de la creation');
      }
    } finally {
      setLoading(false);
    }
  };

  // Succes → afficher resultat
  if (result) {
    return (
      <div className="space-y-6">
        <div className="p-6 bg-emerald-50 border border-emerald-200 rounded-lg text-center">
          <CheckCircle2 size={32} className="mx-auto mb-3 text-emerald-500" />
          <h3 className="text-lg font-semibold text-emerald-900">Client cree avec succes</h3>
          <p className="text-sm text-emerald-700 mt-1">
            {result.sites.length} site{result.sites.length > 1 ? 's' : ''} integre
            {result.sites.length > 1 ? 's' : ''} au patrimoine
          </p>
        </div>

        {result.warnings?.length > 0 && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle size={14} className="text-amber-600" />
              <span className="text-sm font-medium text-amber-800">Avertissements</span>
            </div>
            <ul className="text-xs text-amber-700 space-y-1">
              {result.warnings.map((w, i) => (
                <li key={i}>· {w.message}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm space-y-1">
          <p>
            <span className="font-medium">Organisation :</span> #{result.organisation_id}
          </p>
          <p>
            <span className="font-medium">Entite juridique :</span> #{result.entite_juridique_id}
          </p>
          <p>
            <span className="font-medium">Portefeuille :</span> #{result.portefeuille_id}
          </p>
          <p>
            <span className="font-medium">Sites :</span>{' '}
            {result.sites.map((s) => `${s.nom} (${s.code_postal})`).join(', ')}
          </p>
        </div>

        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
          <p className="font-medium mb-1">Prochaines etapes</p>
          <ul className="text-xs space-y-0.5">
            <li>· Completez les batiments et compteurs dans le patrimoine</li>
            <li>· Connectez les donnees energie (Enedis, GRDF)</li>
            <li>· Ajoutez les contrats et factures</li>
            <li>· Verifiez la conformite reglementaire</li>
          </ul>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={() => navigate('/patrimoine')}
            className="flex-1 px-4 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 text-center"
          >
            Aller au patrimoine
          </button>
          {result.sites.length > 0 && (
            <button
              onClick={() => navigate(`/sites/${result.sites[0].id}`)}
              className="px-4 py-2.5 border border-gray-200 text-sm font-medium rounded-lg hover:bg-gray-50 text-center"
            >
              Voir le premier site
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-1">Confirmer la creation</h2>
        <p className="text-sm text-gray-500">
          Donnees preremplies depuis la base Sirene officielle. Verifiez avant de confirmer.
        </p>
      </div>

      {/* Recap */}
      <div className="divide-y divide-gray-100 border border-gray-200 rounded-lg overflow-hidden">
        <div className="p-4 bg-gray-50">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">Organisation</p>
          <p className="text-sm font-medium text-gray-900 mt-0.5">{orgNom}</p>
          <p className="text-xs text-gray-500">SIREN {uniteLegale.siren}</p>
        </div>
        <div className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">
            Entite juridique
          </p>
          <p className="text-sm text-gray-900 mt-0.5">{orgNom}</p>
          {uniteLegale.activite_principale && (
            <p className="text-xs text-gray-500">NAF {uniteLegale.activite_principale}</p>
          )}
        </div>
        <div className="p-4">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-medium">
            {selectedSirets.length} site{selectedSirets.length > 1 ? 's' : ''}
          </p>
          <ul className="mt-1 space-y-0.5">
            {selectedSirets.map((s) => (
              <li key={s} className="text-xs text-gray-600">
                SIRET {s}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Type client optionnel */}
      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">
          Type de client (optionnel)
        </label>
        <select
          value={typeClient}
          onChange={(e) => setTypeClient(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-200 focus:border-indigo-400 outline-none"
        >
          <option value="">— Auto-detecter depuis NAF —</option>
          <option value="tertiaire">Tertiaire</option>
          <option value="industrie">Industrie</option>
          <option value="retail">Retail / Commerce</option>
          <option value="collectivite">Collectivite</option>
        </select>
      </div>

      <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-xs text-gray-500">
        Les batiments, compteurs et contrats ne seront pas crees automatiquement. Vous les ajouterez
        ensuite dans le patrimoine.
      </div>

      {/* Erreur */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft size={14} /> Retour
        </button>
        <button
          onClick={handleCreate}
          disabled={loading}
          className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
          Creer le client
        </button>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════════════
// Page principale
// ══════════════════════════════════════════════════════════════════════
export default function SireneOnboardingPage() {
  const [step, setStep] = useState('search');
  const [uniteLegale, setUniteLegale] = useState(null);
  const [selectedSirets, setSelectedSirets] = useState([]);

  const handleSelectUL = (ul) => {
    setUniteLegale(ul);
    setStep('select');
  };

  const handleConfirmSelection = (sirets) => {
    setSelectedSirets(sirets);
    setStep('confirm');
  };

  return (
    <PageShell>
      <div className="max-w-2xl mx-auto py-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Nouveau client depuis Sirene</h1>
        <p className="text-sm text-gray-500 mb-6">
          Creez un client PROMEOS a partir de la base Sirene officielle (INSEE)
        </p>

        <StepIndicator steps={STEPS} current={step} />

        {step === 'search' && <SearchStep onSelect={handleSelectUL} />}

        {step === 'select' && uniteLegale && (
          <SelectStep
            uniteLegale={uniteLegale}
            onConfirm={handleConfirmSelection}
            onBack={() => setStep('search')}
          />
        )}

        {step === 'confirm' && uniteLegale && (
          <ConfirmStep
            uniteLegale={uniteLegale}
            selectedSirets={selectedSirets}
            onBack={() => setStep('select')}
          />
        )}
      </div>
    </PageShell>
  );
}
