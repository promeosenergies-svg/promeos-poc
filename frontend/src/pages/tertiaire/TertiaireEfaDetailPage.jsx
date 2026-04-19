/**
 * PROMEOS — TertiaireEfaDetailPage loader (Lot 3 Phase 4 refactor)
 *
 * Thin loader qui fetch l'EFA + sa trajectoire + sa dernière déclaration,
 * puis délègue le rendu Sol à EfaSol.jsx (Pattern C).
 *
 * Scope Phase 4 :
 *   - EFA data : getTertiaireEfa(id)
 *   - Trajectoire : validateEfaTrajectory(id, currentYear)
 *   - Pièces justificatives : embedded dans efa.proofs (pas de fetch séparé)
 *   - Drawers legacy préservés :
 *       ProofDepositCTA → via toast + navigate fallback (le composant
 *         complet peut être ré-intégré Phase 6 si nécessaire)
 *       ModulationDrawer → préservé via state local + render conditionnel
 *   - Actions legacy simplifiées :
 *       Précheck / Export pack / Run controls sont retirés de la fiche
 *       (Pattern C ne les expose pas). Accès via /conformite/tertiaire
 *       liste ou Phase 6 addition.
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useToast } from '../../ui/ToastProvider';
import { getTertiaireEfa, validateEfaTrajectory } from '../../services/api';
import ModulationDrawer from '../../components/conformite/ModulationDrawer';
import ProofDepositCTA from './components/ProofDepositCTA';
import EfaSol from '../EfaSol';
import {
  normalizeEfa,
  totalSurface as computeTotalSurface,
  ownerFromEfa,
} from '../efa/sol_presenters';

export default function TertiaireEfaDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [efa, setEfa] = useState(null);
  const [trajectoryInfo, setTrajectoryInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showModulation, setShowModulation] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getTertiaireEfa(id)
      .then((data) => {
        if (!cancelled) setEfa(normalizeEfa(data));
      })
      .catch(() => {
        if (!cancelled) toast("Erreur lors du chargement de l'EFA", 'error');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    // Trajectoire en non-bloquant (endpoint séparé)
    validateEfaTrajectory(id, new Date().getFullYear())
      .then((data) => { if (!cancelled) setTrajectoryInfo(data); })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, [id, toast]);

  // Proof hint enrichi pour ProofDepositCTA (exigé par proofBridgeV39_1 guard)
  const proofHint = useMemo(() => {
    if (!efa) return 'Preuves documentaires OPERAT';
    const totalSurface = computeTotalSurface(efa);
    const bits = [`EFA:${efa.nom}`, `efa_id:${efa.id}`];
    const owner = ownerFromEfa(efa);
    if (owner) bits.push(`Responsable:${owner}`);
    bits.push(`Surface:${Math.round(totalSurface)} m²`);
    return bits.join(' | ');
  }, [efa]);

  // Le bouton "Déposer pièce" de EntityCard redirige vers le même lien
  // que ProofDepositCTA — on utilise le handler généré par ce composant
  // côté DOM (clic déclenché par ref). Fallback : toast explicatif.
  const handleOpenProofs = useCallback(() => {
    toast('Utilisez le bouton "Déposer une preuve" dans la section Preuves documentaires ci-dessous.', 'info');
  }, [toast]);

  const handleOpenModulation = useCallback(() => {
    setShowModulation(true);
  }, []);

  const handleExportOperat = useCallback(() => {
    navigate(`/conformite/tertiaire?efa_id=${id}&action=export`);
  }, [id, navigate]);

  if (loading) {
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

  if (!efa) {
    return (
      <div style={{ minHeight: '60vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: 'var(--sol-ink-500)', marginBottom: 16 }}>
            EFA introuvable ou accès restreint.
          </p>
          <button
            type="button"
            onClick={() => navigate('/conformite/tertiaire')}
            className="sol-btn sol-btn--secondary"
          >
            Retour à la liste
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 1280, margin: '0 auto' }}>
      <EfaSol
        efa={efa}
        trajectoryInfo={trajectoryInfo}
        onOpenProofs={handleOpenProofs}
        onOpenModulation={handleOpenModulation}
        onExportOperat={handleExportOperat}
      />
      {showModulation && (
        <ModulationDrawer
          open={showModulation}
          onClose={() => setShowModulation(false)}
          efaId={id}
        />
      )}

      {/* Banner aide a la conformite OPERAT (Aide à la conformité · dossier
          préparatoire) — garde-fou légal : PROMEOS ne fait PAS le dépôt
          réel à ADEME, uniquement un pack preparatoire (Generer le pack).
          Le dépôt officiel passe par operat.ademe.fr. */}
      <aside
        style={{
          marginTop: 24,
          padding: '14px 18px',
          background: 'var(--sol-attention-bg)',
          border: '1px solid var(--sol-attention-fg)',
          borderRadius: 6,
          display: 'flex',
          gap: 14,
          alignItems: 'flex-start',
        }}
        role="note"
        aria-label="Aide à la conformité OPERAT"
      >
        <span
          aria-hidden="true"
          style={{
            fontSize: 18,
            color: 'var(--sol-attention-fg)',
            lineHeight: 1,
            flexShrink: 0,
          }}
        >
          ⚠
        </span>
        <div style={{ minWidth: 0 }}>
          <p
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13,
              fontWeight: 600,
              color: 'var(--sol-attention-fg)',
              margin: 0,
              marginBottom: 4,
            }}
          >
            Aide à la conformité · Préparation de dossier
          </p>
          <p
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 12.5,
              color: 'var(--sol-ink-700)',
              margin: 0,
              lineHeight: 1.45,
            }}
          >
            PROMEOS génère un pack préparatoire OPERAT (simulation). Le dépôt
            officiel doit toujours être effectué via la plateforme de l’ADEME
            sur <strong>operat.ademe.fr</strong> — cette fiche ne se substitue
            pas à la déclaration légale. Le bouton « Générer le pack
            préparatoire » produit uniquement le dossier documentaire destiné
            au dépôt manuel.
          </p>
        </div>
      </aside>

      {/* Preuves documentaires — ProofDepositCTA préservé legacy */}
      <section
        style={{
          marginTop: 32,
          padding: '20px 24px',
          background: 'var(--sol-bg-paper)',
          border: '1px solid var(--sol-ink-200)',
          borderRadius: 6,
        }}
      >
        <h3
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 16,
            fontWeight: 600,
            color: 'var(--sol-ink-900)',
            margin: 0,
            marginBottom: 12,
          }}
        >
          Preuves documentaires
        </h3>
        <p
          style={{
            fontFamily: 'var(--sol-font-body)',
            fontSize: 13,
            color: 'var(--sol-ink-500)',
            margin: '0 0 14px',
            lineHeight: 1.5,
          }}
        >
          Déposez les factures, relevés et attestations associés à cette EFA
          pour alimenter le dossier OPERAT. Le hint est pré-rempli avec le
          contexte (EFA, responsable, surface).
        </p>
        <ProofDepositCTA hint={proofHint} />
      </section>
    </div>
  );
}
