/**
 * PROMEOS - Mémobox (/kb) — V38
 * FTS5 search KB items + Documents tab (upload, lifecycle badges)
 * Deep-link support: /kb?context=proof&domain=X&hint=Y
 */
import { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search, BookOpen, ShieldCheck, Zap, Sun, Receipt, Wind,
  ChevronDown, ChevronUp, ExternalLink, Filter, AlertTriangle,
  Upload, FileText, CheckCircle, X,
} from 'lucide-react';
import { PageShell, Card, CardBody, Badge, Button, TrustBadge, EmptyState } from '../ui';
import { SkeletonCard } from '../ui/Skeleton';
import { searchKBItems, getKBFullStats, uploadKBDoc, getKBDocs, changeKBDocStatus, linkTertiaireProof } from '../services/api';
import { DOC_STATUS_LABELS, DOC_STATUS_BADGE } from '../models/proofLinkModel';

const DOMAIN_TABS = [
  { key: null, label: 'Tout', icon: BookOpen },
  { key: 'reglementaire', label: 'Réglementaire', icon: ShieldCheck },
  { key: 'usages', label: 'Usages', icon: Zap },
  { key: 'acc', label: 'ACC', icon: Sun },
  { key: 'facturation', label: 'Facturation', icon: Receipt },
  { key: 'flex', label: 'Flex', icon: Wind },
];

const TYPE_LABELS = {
  rule: 'Regle', knowledge: 'Connaissance', checklist: 'Checklist', calc: 'Calcul',
};
const TYPE_BADGE = {
  rule: 'crit', knowledge: 'info', checklist: 'warn', calc: 'neutral',
};
const CONFIDENCE_BADGE = {
  high: 'ok', medium: 'warn', low: 'neutral',
};
const DOMAIN_COLORS = {
  reglementaire: 'bg-red-50 text-red-700',
  usages: 'bg-blue-50 text-blue-700',
  acc: 'bg-green-50 text-green-700',
  facturation: 'bg-purple-50 text-purple-700',
  flex: 'bg-amber-50 text-amber-700',
};

export default function KBExplorerPage() {
  const [searchParams] = useSearchParams();
  const [query, setQuery] = useState('');
  const [domain, setDomain] = useState(null);
  const [typeFilter, setTypeFilter] = useState(null);
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState(null);
  const [kbError, setKbError] = useState(null);
  const debounceRef = useRef(null);

  // V38: Docs tab
  const [activeTab, setActiveTab] = useState(searchParams.get('context') === 'proof' ? 'docs' : 'items');
  const [docs, setDocs] = useState([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState(null);

  // V39.1: Proof context banner state
  const [proofContext, setProofContext] = useState(null);
  const [statusFilter, setStatusFilter] = useState(null);

  // V38+V39.1: Deep-link from proof context
  useEffect(() => {
    const urlDomain = searchParams.get('domain');
    if (urlDomain) setDomain(urlDomain);
    const urlHint = searchParams.get('hint');
    if (urlHint) setQuery(urlHint);
    const urlStatus = searchParams.get('status');
    if (urlStatus) setStatusFilter(urlStatus);
    // V39.1+V45: Build proof context for banner
    if (searchParams.get('context') === 'proof') {
      setProofContext({
        hint: urlHint || null,
        domain: urlDomain || null,
        lever: searchParams.get('lever') || null,
        status: urlStatus || null,
        proof_type: searchParams.get('proof_type') || null,
        efa_id: searchParams.get('efa_id') || null,
      });
    }
  }, []);

  // Load stats on mount
  useEffect(() => {
    getKBFullStats().then((s) => { setStats(s); setKbError(null); }).catch(() => {
      setKbError('kb_unavailable');
    });
  }, []);

  // Search with debounce (items tab)
  useEffect(() => {
    if (activeTab !== 'items') return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      doSearch();
    }, 300);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, domain, typeFilter, activeTab]);

  // V38: Load docs when switching to docs tab
  useEffect(() => {
    if (activeTab === 'docs') loadDocs();
  }, [activeTab, domain, statusFilter]);

  async function doSearch() {
    setLoading(true);
    try {
      const body = {
        q: query || '*',
        include_drafts: true,
        limit: 50,
      };
      if (domain) body.domain = domain;
      if (typeFilter) body.type = typeFilter;

      const data = await searchKBItems(body);
      setResults(data.results || data || []);
      setKbError(null);
    } catch (err) {
      setResults([]);
      if (err?.response?.status === 404 || err?.response?.status >= 500) {
        setKbError('kb_unavailable');
      }
    }
    setLoading(false);
  }

  async function loadDocs() {
    setDocsLoading(true);
    try {
      const params = {};
      if (domain) params.domain = domain;
      if (statusFilter) params.status = statusFilter;
      const data = await getKBDocs(params);
      setDocs(data.docs || []);
    } catch {
      setDocs([]);
    }
    setDocsLoading(false);
  }

  async function handleUpload(e) {
    const f = e.target.files?.[0];
    if (!f) return;
    setUploadMsg(null);
    try {
      const result = await uploadKBDoc(f, f.name, domain);
      if (result.status === 'already_exists') {
        setUploadMsg({ type: 'info', text: 'Document déjà présent (contenu identique)' });
      } else {
        setUploadMsg({ type: 'ok', text: `Document ingéré : ${result.doc_id} (${result.nb_chunks} chunks)` });
      }
      loadDocs();
    } catch (err) {
      setUploadMsg({ type: 'error', text: err?.response?.data?.detail || 'Erreur lors de l\u2019upload' });
    }
    // Reset input to allow re-uploading same file
    e.target.value = '';
  }

  async function handleStatusChange(docId, newStatus) {
    try {
      await changeKBDocStatus(docId, newStatus);
      loadDocs();
    } catch (err) {
      setUploadMsg({ type: 'error', text: err?.response?.data?.detail || 'Erreur changement de statut' });
    }
  }

  // V39.1: Clear proof context filters
  function clearProofContext() {
    setProofContext(null);
    setDomain(null);
    setStatusFilter(null);
    setQuery('');
    setActiveTab('items');
  }

  function toggleExpand(id) {
    setExpandedId(expandedId === id ? null : id);
  }

  return (
    <PageShell
      icon={BookOpen}
      title="Mémobox"
      subtitle={stats ? `${stats.total_items} items — Règles, documents & preuves` : 'Règles, documents & preuves'}
      actions={stats && (
        <div className="flex items-center gap-2">
          <Badge status="ok">{stats.by_status?.validated || 0} validés</Badge>
          <Badge status="neutral">{stats.by_status?.draft || 0} brouillons</Badge>
        </div>
      )}
    >

      {/* KB unavailable fallback banner */}
      {kbError === 'kb_unavailable' && (
        <Card className="bg-amber-50 border-amber-200">
          <CardBody className="flex items-center gap-3 py-3">
            <AlertTriangle size={20} className="text-amber-600 shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800">KB locale chargée</p>
              <p className="text-xs text-amber-600">Le service Mémobox n&apos;est pas disponible. Les données locales sont affichées.</p>
            </div>
          </CardBody>
        </Card>
      )}

      {/* V39.1: Proof context banner */}
      {proofContext && (
        <div
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg border border-indigo-200 bg-indigo-50/60"
          data-testid="proof-context-banner"
        >
          <Upload size={16} className="text-indigo-500 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-indigo-800">
              Preuve attendue
              {proofContext.domain && (
                <span className="text-indigo-500 font-normal"> — Domaine : {proofContext.domain.replace('conformite/', 'Conformité / ').replace('tertiaire-operat', 'Tertiaire OPERAT')}</span>
              )}
            </p>
            {proofContext.proof_type && (
              <p className="text-[11px] text-indigo-700 font-medium mt-0.5" data-testid="proof-type-label">
                Type : {proofContext.proof_type.replace(/_/g, ' ')}
                {proofContext.efa_id && <span className="text-indigo-500 font-normal"> · EFA #{proofContext.efa_id}</span>}
              </p>
            )}
            {proofContext.hint && (
              <p className="text-[11px] text-indigo-600 truncate mt-0.5">{proofContext.hint}</p>
            )}
          </div>
          <button
            onClick={clearProofContext}
            className="flex items-center gap-1 text-[11px] text-indigo-600 hover:text-indigo-800 shrink-0"
            aria-label="Effacer les filtres de preuve"
          >
            <X size={12} />
            Effacer filtres
          </button>
        </div>
      )}

      {/* V38: Tab switcher — Items vs Documents */}
      <div className="flex border-b border-gray-200" data-testid="memobox-tabs">
        <button
          onClick={() => setActiveTab('items')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeTab === 'items'
              ? 'border-b-2 border-blue-500 text-blue-700'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Règles & Connaissances
        </button>
        <button
          onClick={() => setActiveTab('docs')}
          className={`px-4 py-2 text-sm font-medium transition ${
            activeTab === 'docs'
              ? 'border-b-2 border-blue-500 text-blue-700'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          Documents
        </button>
      </div>

      {/* ═══ Items Tab ═══ */}
      {activeTab === 'items' && (
        <>
          {/* Search bar */}
          <div className="relative">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher : BACS 290 kW, décret tertiaire, autoconsommation..."
              className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white shadow-sm"
            />
          </div>

          {/* Domain tabs */}
          <div className="flex items-center gap-1 flex-wrap">
            {DOMAIN_TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => setDomain(key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition
                  ${domain === key
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  }`}
              >
                <Icon size={14} />
                {label}
                {stats && key && (
                  <span className="text-xs opacity-60">({stats.by_domain?.[key] || 0})</span>
                )}
              </button>
            ))}

            {/* Type filter */}
            <div className="ml-auto flex items-center gap-1">
              <Filter size={14} className="text-gray-400" />
              {Object.entries(TYPE_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setTypeFilter(typeFilter === key ? null : key)}
                  className={`px-2 py-1 rounded text-xs font-medium transition
                    ${typeFilter === key
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
                    }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Results */}
          {loading && (
            <div className="text-center py-8 text-gray-400 text-sm">Recherche en cours...</div>
          )}

          {!loading && results.length === 0 && query && (
            <Card>
              <CardBody className="text-center py-8">
                <BookOpen size={32} className="text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">Aucun résultat pour &quot;{query}&quot;</p>
              </CardBody>
            </Card>
          )}

          {!loading && results.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-400">{results.length} résultats</p>
              {results.map((item) => (
                <KBItemCard
                  key={item.id}
                  item={item}
                  expanded={expandedId === item.id}
                  onToggle={() => toggleExpand(item.id)}
                />
              ))}
            </div>
          )}

          {/* Initial state */}
          {!loading && results.length === 0 && !query && (
            <Card>
              <CardBody className="text-center py-12">
                <BookOpen size={40} className="text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Explorez la base de connaissances</h3>
                <p className="text-sm text-gray-500 mb-4">
                  Recherchez par mot-clé ou filtrez par domaine pour découvrir les règles, obligations et recommandations.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2">
                  {['BACS 290 kW', 'décret tertiaire', 'autoconsommation', 'OPERAT', 'flexibilité', 'ARENH'].map((q) => (
                    <button
                      key={q}
                      onClick={() => setQuery(q)}
                      className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium hover:bg-blue-100 transition"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </CardBody>
            </Card>
          )}
        </>
      )}

      {/* ═══ Documents Tab (V38) ═══ */}
      {activeTab === 'docs' && (
        <div className="space-y-3" data-testid="docs-tab">
          {/* Upload zone */}
          <label className="flex items-center justify-center gap-2 border-2 border-dashed border-gray-300 rounded-xl p-6 cursor-pointer hover:border-blue-400 transition bg-white">
            <Upload size={20} className="text-gray-400" />
            <span className="text-sm text-gray-500">
              Déposer un document (PDF, HTML, MD, TXT — max 10 Mo)
            </span>
            <input
              type="file"
              className="hidden"
              accept=".pdf,.html,.htm,.md,.txt"
              onChange={handleUpload}
              data-testid="upload-input"
            />
          </label>

          {/* Upload feedback */}
          {uploadMsg && (
            <div className={`text-xs px-3 py-2 rounded-lg ${
              uploadMsg.type === 'ok' ? 'bg-green-50 text-green-700' :
              uploadMsg.type === 'info' ? 'bg-blue-50 text-blue-700' :
              'bg-red-50 text-red-700'
            }`}>
              {uploadMsg.text}
            </div>
          )}

          {/* Domain filter for docs */}
          <div className="flex items-center gap-1 flex-wrap">
            {DOMAIN_TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => setDomain(key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition
                  ${domain === key
                    ? 'bg-blue-100 text-blue-700'
                    : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
                  }`}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </div>

          {/* Docs list */}
          {docsLoading && (
            <div className="text-center py-8 text-gray-400 text-sm">Chargement des documents...</div>
          )}

          {!docsLoading && docs.length === 0 && (
            <Card>
              <CardBody className="text-center py-8">
                <FileText size={32} className="text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">Aucun document déposé</p>
                <p className="text-xs text-gray-400 mt-1">Utilisez la zone ci-dessus pour déposer un fichier</p>
              </CardBody>
            </Card>
          )}

          {!docsLoading && docs.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-gray-400">{docs.length} document{docs.length > 1 ? 's' : ''}</p>
              {docs.map((doc) => (
                <DocCard key={doc.doc_id} doc={doc} onStatusChange={handleStatusChange} proofContext={proofContext} onLinkMsg={setUploadMsg} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <TrustBadge source="PROMEOS Mémobox" period="457 items ingeres" confidence="high" />
    </PageShell>
  );
}


// ── Doc Card (V38) ───────────────────────────────────────────────────────────

const NEXT_STATUS = {
  draft: 'review',
  review: 'validated',
  validated: 'decisional',
};
const NEXT_STATUS_LABEL = {
  draft: 'Soumettre en revue',
  review: 'Valider',
  validated: 'Marquer décisionnel',
};

function DocCard({ doc, onStatusChange, proofContext, onLinkMsg }) {
  const status = doc.status || 'draft';
  const next = NEXT_STATUS[status];
  const domainColor = DOMAIN_COLORS[doc.domain] || '';

  // V45: Link doc as proof to EFA
  const canLink = proofContext?.efa_id && proofContext?.proof_type;
  const [linking, setLinking] = useState(false);

  async function handleLinkProof() {
    if (!canLink) return;
    setLinking(true);
    try {
      const result = await linkTertiaireProof(proofContext.efa_id, {
        kb_doc_id: doc.doc_id,
        proof_type: proofContext.proof_type,
        year: new Date().getFullYear(),
      });
      const msg = result.status === 'already_linked'
        ? 'Preuve déjà liée à cette EFA'
        : `Preuve liée à l'EFA #${proofContext.efa_id}`;
      if (onLinkMsg) onLinkMsg({ type: result.status === 'already_linked' ? 'info' : 'ok', text: msg });
    } catch {
      if (onLinkMsg) onLinkMsg({ type: 'error', text: 'Erreur lors du rattachement de la preuve' });
    }
    setLinking(false);
  }

  return (
    <Card>
      <CardBody className="py-3">
        <div className="flex items-center gap-3">
          <FileText size={16} className="text-gray-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-800 truncate">{doc.title}</p>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <span className="text-[11px] text-gray-400">{doc.source_type}</span>
              <span className="text-[11px] text-gray-400">•</span>
              <span className="text-[11px] text-gray-400">{doc.nb_chunks ?? 0} chunks</span>
              <span className="text-[11px] text-gray-400">•</span>
              <span className="text-[11px] text-gray-400 font-mono">{doc.content_hash?.slice(0, 8)}</span>
              {doc.domain && (
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${domainColor}`}>{doc.domain}</span>
              )}
            </div>
          </div>
          <Badge status={DOC_STATUS_BADGE[status] || 'neutral'}>
            {DOC_STATUS_LABELS[status] || status}
          </Badge>
          {next && (
            <button
              onClick={() => onStatusChange(doc.doc_id, next)}
              className="text-[10px] text-blue-600 hover:text-blue-800 underline shrink-0"
              aria-label={NEXT_STATUS_LABEL[status]}
            >
              {NEXT_STATUS_LABEL[status]}
            </button>
          )}
          {/* V45: Link as proof to EFA */}
          {canLink && (
            <button
              onClick={handleLinkProof}
              disabled={linking}
              className="text-[10px] text-indigo-600 hover:text-indigo-800 underline shrink-0"
              data-testid="btn-link-proof-efa"
            >
              {linking ? 'Liaison…' : 'Lier à l\u2019EFA'}
            </button>
          )}
        </div>
        {/* V38: Gating warning for non-deterministic docs */}
        {(status === 'draft' || status === 'review') && (
          <div className="flex items-center gap-1.5 mt-2 px-2 py-1 bg-amber-50 rounded text-[10px] text-amber-700" data-testid="gating-warning">
            <AlertTriangle size={12} className="shrink-0" />
            <span>Document non utilisable pour le calcul déterministe (statut{'\u00a0'}: {DOC_STATUS_LABELS[status]})</span>
          </div>
        )}
      </CardBody>
    </Card>
  );
}


// ── KB Item Card (unchanged) ─────────────────────────────────────────────────

function KBItemCard({ item, expanded, onToggle }) {
  const domainColor = DOMAIN_COLORS[item.domain] || 'bg-gray-50 text-gray-700';

  return (
    <Card className={item.status === 'validated' ? 'border-l-4 border-l-blue-400' : ''}>
      <CardBody className="py-3">
        {/* Header row */}
        <div className="flex items-start gap-3 cursor-pointer" onClick={onToggle}>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${domainColor}`}>
                {item.domain}
              </span>
              <Badge status={TYPE_BADGE[item.type] || 'neutral'}>
                {TYPE_LABELS[item.type] || item.type}
              </Badge>
              <Badge status={CONFIDENCE_BADGE[item.confidence] || 'neutral'}>
                {item.confidence}
              </Badge>
              {item.status === 'validated' && (
                <Badge status="ok">Validé</Badge>
              )}
            </div>
            <h4 className="text-sm font-semibold text-gray-900 leading-tight">{item.title}</h4>
            {!expanded && item.summary && (
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{item.summary.slice(0, 200)}</p>
            )}
          </div>
          <button className="p-1 text-gray-400 hover:text-gray-600 shrink-0">
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>

        {/* Expanded content */}
        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-100 space-y-3">
            {/* Full content */}
            {item.content_md && (
              <div className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed max-h-96 overflow-y-auto bg-gray-50 rounded-lg p-4">
                {item.content_md}
              </div>
            )}

            {/* Tags */}
            {item.tags && (
              <div className="flex flex-wrap gap-1">
                {Object.entries(item.tags).map(([cat, values]) =>
                  Array.isArray(values) && values.length > 0 && values.map((v) => (
                    <span key={`${cat}-${v}`} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                      {cat}:{v}
                    </span>
                  ))
                )}
              </div>
            )}

            {/* Logic/scope */}
            {item.logic && (
              <div className="bg-blue-50 rounded-lg p-3">
                <p className="text-xs font-semibold text-blue-700 mb-1">Logique d&apos;évaluation</p>
                {item.logic.then?.outputs?.map((output, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-blue-800 mt-1">
                    <span className={`inline-block w-2 h-2 rounded-full ${output.severity === 'critical' ? 'bg-red-500' : output.severity === 'high' ? 'bg-orange-500' : 'bg-blue-500'}`} />
                    <span className="font-medium">{output.label}</span>
                    {output.deadline && <span className="text-blue-600">({output.deadline})</span>}
                  </div>
                ))}
              </div>
            )}

            {/* Sources */}
            {item.sources && item.sources.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1">Sources</p>
                {item.sources.map((src, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs text-gray-600">
                    <ExternalLink size={12} />
                    <span>{src.label} - {src.section}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Meta */}
            <div className="flex items-center gap-4 text-xs text-gray-400">
              <span>ID: {item.id}</span>
              <span>Maj: {item.updated_at}</span>
              {item.priority && <span>Priorité: {item.priority}</span>}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
