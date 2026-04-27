/**
 * MethodologiePage — page lazy qui rend les documents méthodologiques Sol.
 *
 * Sprint 1.3bis P0-A (audit fin S1) : SolPageFooter cite
 * `methodology_url` mais aucune route React ne pointait vers ces docs
 * → cliquer = page 404 (NotFound). Trust signal §5 cassé.
 *
 * Cette page rend les fichiers `docs/methodologie/*.md` du repo via
 * fetch + parsing markdown léger (pas de dépendance externe lourde —
 * react-markdown serait idéal mais on garde MVP simple).
 *
 * Doctrine §5 grammaire : kicker + titre Fraunces + body éditorial +
 * footer SCM cohérent avec page d'origine.
 */
import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, FileText } from 'lucide-react';
import { PageShell } from '../ui';
import SolPageHeader from '../ui/sol/SolPageHeader';

// Catalogue des docs méthodologie disponibles. Doit refléter le contenu
// du dossier `docs/methodologie/` du repo (servi statiquement via Vite
// public/docs/ ou fetch direct selon la config).
const METHODOLOGIE_CATALOG = Object.freeze({
  'conformite-regops': {
    title: 'Score conformité RegOps',
    italicHook: 'pondérations DT / BACS / APER / Audit énergétique',
    kicker: 'MÉTHODOLOGIE · CONFORMITÉ',
    publicPath: '/docs/methodologie/conformite-regops.md',
  },
  'cockpit-comex': {
    title: 'Vue COMEX (cockpit Jean-Marc CFO)',
    italicHook: 'trajectoire 2030, exposition financière, leviers économies',
    kicker: 'MÉTHODOLOGIE · COCKPIT COMEX',
    publicPath: '/docs/methodologie/cockpit-comex.md',
  },
  'patrimoine-mutualisation': {
    title: 'Mutualisation Décret Tertiaire',
    italicHook: 'différenciateur §4.1 multisite chiffré €/an',
    kicker: 'MÉTHODOLOGIE · PATRIMOINE',
    publicPath: '/docs/methodologie/patrimoine-mutualisation.md',
  },
  'bill-intel-shadow': {
    title: 'Shadow Billing v4.2',
    italicHook: 'audit factures TURPE 7 / ATRD / accise / CTA / TVA',
    kicker: 'MÉTHODOLOGIE · BILL-INTEL',
    publicPath: '/docs/methodologie/bill-intel-shadow.md',
  },
  'achat-post-arenh': {
    title: 'Achat énergie post-ARENH',
    italicHook: 'neutralité fournisseur · 30+ offres CRE · shadow 6 composantes',
    kicker: 'MÉTHODOLOGIE · ACHAT',
    publicPath: '/docs/methodologie/achat-post-arenh.md',
  },
  'performance-monitoring': {
    title: 'Monitoring Performance Électrique',
    italicHook: 'pilotage temps réel · ISO 50001 · COSTIC · alertes auto',
    kicker: 'MÉTHODOLOGIE · MONITORING',
    publicPath: '/docs/methodologie/performance-monitoring.md',
  },
  'diagnostic-conso': {
    title: 'Diagnostic Consommation',
    italicHook: '5 catégories · CUSUM ISO 50001 · DJU COSTIC · plan priorisé',
    kicker: 'MÉTHODOLOGIE · DIAGNOSTIC',
    publicPath: '/docs/methodologie/diagnostic-conso.md',
  },
  'centre-actions': {
    title: "Centre d'actions cross-pillar",
    italicHook: 'orchestration · ActionItem unifié · workflow lifecycle',
    kicker: "MÉTHODOLOGIE · CENTRE D'ACTIONS",
    publicPath: '/docs/methodologie/centre-actions.md',
  },
});

// Mini-renderer markdown : titre, paragraphes, listes, tables, code,
// blockquotes. Volontairement minimal — pas de XSS car contenu interne
// statique du repo, mais on échappe le HTML quand même.
function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderMarkdown(md) {
  // Convertit le markdown en blocs HTML stylisés Sol. Approche ligne-à-ligne
  // simple — suffisant pour les docs méthodologie internes structurés.
  const lines = md.split('\n');
  const out = [];
  let inTable = false;
  let tableRows = [];
  let inCode = false;
  let codeLines = [];

  const flushTable = () => {
    if (tableRows.length === 0) return;
    const [head, , ...rows] = tableRows;
    const headers = head
      .split('|')
      .filter((c) => c.trim())
      .map((c) => c.trim());
    out.push(
      `<div class="overflow-x-auto my-4"><table class="w-full text-sm"><thead><tr>${headers
        .map(
          (h) =>
            `<th class="text-left font-semibold px-3 py-2 border-b border-[var(--sol-line)] text-[var(--sol-ink-700)]">${escapeHtml(h)}</th>`
        )
        .join('')}</tr></thead><tbody>${rows
        .map(
          (r) =>
            `<tr>${r
              .split('|')
              .filter((c) => c.trim())
              .map(
                (c) =>
                  `<td class="px-3 py-2 border-b border-[var(--sol-line)]/40 text-[var(--sol-ink-700)]">${escapeHtml(c.trim())}</td>`
              )
              .join('')}</tr>`
        )
        .join('')}</tbody></table></div>`
    );
    tableRows = [];
    inTable = false;
  };

  const flushCode = () => {
    if (codeLines.length === 0) return;
    out.push(
      `<pre class="bg-[var(--sol-bg-panel)] border border-[var(--sol-line)] rounded p-3 my-3 text-xs font-mono overflow-x-auto text-[var(--sol-ink-700)]">${escapeHtml(codeLines.join('\n'))}</pre>`
    );
    codeLines = [];
    inCode = false;
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith('```')) {
      if (inCode) flushCode();
      else inCode = true;
      continue;
    }
    if (inCode) {
      codeLines.push(raw);
      continue;
    }
    if (line.startsWith('|')) {
      tableRows.push(line);
      inTable = true;
      continue;
    }
    if (inTable) flushTable();

    if (line.startsWith('# ')) {
      // h1 ignoré — on a déjà le titre dans SolPageHeader
      continue;
    }
    if (line.startsWith('## ')) {
      out.push(
        `<h2 class="text-xl font-semibold text-[var(--sol-ink-900)] mt-6 mb-2 sol-page-title" style="font-size:22px">${escapeHtml(line.slice(3))}</h2>`
      );
    } else if (line.startsWith('### ')) {
      out.push(
        `<h3 class="text-base font-semibold text-[var(--sol-ink-900)] mt-4 mb-2">${escapeHtml(line.slice(4))}</h3>`
      );
    } else if (line.startsWith('> ')) {
      out.push(
        `<blockquote class="border-l-4 border-[var(--sol-attention-line)] pl-4 italic text-[var(--sol-ink-700)] my-3">${escapeHtml(line.slice(2))}</blockquote>`
      );
    } else if (line.startsWith('- ')) {
      out.push(
        `<li class="ml-5 list-disc text-[var(--sol-ink-700)] leading-relaxed">${parseInline(line.slice(2))}</li>`
      );
    } else if (line.trim()) {
      out.push(
        `<p class="text-[15px] leading-relaxed text-[var(--sol-ink-700)] my-2">${parseInline(line)}</p>`
      );
    }
  }
  flushTable();
  flushCode();
  return out.join('\n');
}

function parseInline(text) {
  let s = escapeHtml(text);
  // Bold **x**
  s = s.replace(
    /\*\*([^*]+)\*\*/g,
    '<strong class="font-semibold text-[var(--sol-ink-900)]">$1</strong>'
  );
  // Italic *x*
  s = s.replace(/\*([^*]+)\*/g, '<em class="italic">$1</em>');
  // Inline code `x`
  s = s.replace(
    /`([^`]+)`/g,
    '<code class="px-1 py-0.5 bg-[var(--sol-bg-panel)] rounded text-[13px] font-mono text-[var(--sol-ink-900)]">$1</code>'
  );
  // Links [text](url) — externes uniquement (commencent par http)
  s = s.replace(
    /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-[var(--sol-calme-fg)] underline-offset-2 hover:underline">$1</a>'
  );
  return s;
}

export default function MethodologiePage() {
  const { docKey } = useParams();
  const [content, setContent] = useState(null);
  const [error, setError] = useState(null);

  const meta = METHODOLOGIE_CATALOG[docKey];

  useEffect(() => {
    let cancelled = false;
    if (!meta) {
      setError('Document non répertorié.');
      return;
    }
    setContent(null);
    setError(null);
    fetch(meta.publicPath)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((md) => {
        if (!cancelled) setContent(md);
      })
      .catch((e) => {
        if (!cancelled) setError(e.message || 'Erreur de chargement');
      });
    return () => {
      cancelled = true;
    };
  }, [docKey, meta]);

  if (!meta) {
    return (
      <PageShell
        editorialHeader={
          <SolPageHeader
            kicker="MÉTHODOLOGIE · INTROUVABLE"
            title="Document non répertorié"
            subtitle={`Clé demandée : ${docKey}`}
          />
        }
      >
        <Link
          to="/"
          className="inline-flex items-center gap-1 text-[var(--sol-calme-fg)] hover:underline"
        >
          <ArrowLeft size={14} aria-hidden="true" />
          Retour au tableau de bord
        </Link>
      </PageShell>
    );
  }

  return (
    <PageShell
      editorialHeader={
        <SolPageHeader
          kicker={meta.kicker}
          title={meta.title}
          italicHook={meta.italicHook}
          subtitle="Document méthodologique de référence — toute citation backend pointe ici."
        />
      }
    >
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-[13px] text-[var(--sol-ink-500)] hover:text-[var(--sol-ink-900)] mb-2"
      >
        <ArrowLeft size={13} aria-hidden="true" />
        Retour au tableau de bord
      </Link>

      {error && (
        <div className="rounded-lg border border-[var(--sol-refuse-line)] bg-[var(--sol-refuse-bg)] p-4 text-sm text-[var(--sol-refuse-fg)] my-4">
          <FileText size={14} className="inline mr-1.5" aria-hidden="true" />
          Erreur de chargement de la méthodologie : {error}
        </div>
      )}

      {!content && !error && (
        <div className="text-sm text-[var(--sol-ink-500)] my-4">Chargement de la méthodologie…</div>
      )}

      {content && (
        <article
          className="max-w-3xl prose-sol"
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
        />
      )}
    </PageShell>
  );
}
