/**
 * PROMEOS — RegOps loader (Lot 3 Phase 3 refactor)
 *
 * Data loader + handoff vers RegOpsSol (Pattern C fiche dossier).
 * Le rendu Sol vit dans RegOpsSol.jsx — ce fichier garde uniquement :
 *   1. useParams (site_id depuis /regops/:id)
 *   2. fetch en parallèle : assessment + aiExplanation + aiRecommendations
 *      + dataQuality
 *   3. lookup site dans scopedSites pour passer le nom en prop
 *   4. handoff vers <RegOpsSol ... />
 *
 * Le legacy 374 LOC (dual panel Audit/IA) est remplacé intégralement —
 * la Synthèse IA vit maintenant en section optionnelle à l'intérieur
 * de RegOpsSol (pas de dual tab). Les 4 endpoints AI sont toujours
 * appelés pour alimenter la synthèse.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  getRegOpsAssessment,
  getAiExplanation,
  getAiRecommendations,
  getAiDataQuality,
} from '../services/api';
import { useToast } from '../ui/ToastProvider';
import { useScope } from '../contexts/ScopeContext';
import { useActionDrawer } from '../contexts/ActionDrawerContext';
import RegOpsSol from './RegOpsSol';
import { normalizeAssessment } from './regops/sol_presenters';

export default function RegOps() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { scopedSites, sitesLoading } = useScope();
  const actionDrawer = useActionDrawer?.() ?? null;

  const [assessment, setAssessment] = useState(null);
  const [aiExplanation, setAiExplanation] = useState(null);
  const [aiRecommendations, setAiRecommendations] = useState(null);
  const [dataQuality, setDataQuality] = useState(null); // eslint-disable-line no-unused-vars
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    // Priorité : récupérer l'assessment déterministe pour pouvoir rendre la
    // fiche tout de suite. Les 3 endpoints AI sont lents (LLM) mais non
    // bloquants pour la première render — fire-and-forget, hydratation au
    // retour.
    async function loadAssessment() {
      setLoading(true);
      try {
        const a = await getRegOpsAssessment(id);
        if (!cancelled) setAssessment(normalizeAssessment(a));
      } catch {
        if (!cancelled) toast('Erreur lors du chargement des données RegOps', 'error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadAssessment();

    // AI (non-bloquant)
    getAiExplanation(id).then((d) => { if (!cancelled) setAiExplanation(d); }).catch(() => {});
    getAiRecommendations(id).then((d) => { if (!cancelled) setAiRecommendations(d); }).catch(() => {});
    getAiDataQuality(id).then((d) => { if (!cancelled) setDataQuality(d); }).catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [id, toast]);

  if (loading || sitesLoading) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div
          style={{
            width: 48,
            height: 48,
            borderRadius: '50%',
            border: '3px solid var(--sol-ink-200)',
            borderTopColor: 'var(--sol-calme-fg)',
            animation: 'spin 900ms linear infinite',
          }}
        />
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>
    );
  }

  if (!assessment) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: 'var(--sol-ink-500)', marginBottom: 16 }}>
            Évaluation réglementaire non disponible pour ce site.
          </p>
          <button
            type="button"
            onClick={() => navigate('/patrimoine')}
            className="sol-btn sol-btn--secondary"
          >
            Retour au patrimoine
          </button>
        </div>
      </div>
    );
  }

  const site = scopedSites?.find((s) => String(s.id) === String(id)) || null;

  const handleOpenAction = (finding) => {
    if (actionDrawer?.openActionDrawer) {
      actionDrawer.openActionDrawer({
        prefill: {
          title: finding?.title || finding?.label || 'Action RegOps',
          description: finding?.explanation || finding?.urgency_reason || finding?.description,
        },
        siteId: String(id),
        sourceType: 'regops_finding',
        sourceId: finding?.rule_id || finding?.action_code || finding?.type || 'unknown',
      });
      return;
    }
    toast(finding?.title || finding?.label || 'Action en cours de développement', 'info');
  };

  const handleBackToSite = (siteId) => {
    navigate(`/sites/${siteId}`);
  };

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1280, margin: '0 auto' }}>
      <RegOpsSol
        assessment={assessment}
        site={site}
        aiExplanation={aiExplanation}
        aiRecommendations={aiRecommendations}
        onOpenAction={handleOpenAction}
        onBackToSite={handleBackToSite}
      />
    </div>
  );
}
