/**
 * TabPuissance — Onglet Puissance du Site360.
 * Compose PowerPanel + FlexScoreCard + FlexNebcoCard.
 * RÈGLE ABSOLUE : zéro calcul métier. 100% display-only.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import PowerPanel from './PowerPanel';
import FlexNebcoCard from '../usages/FlexNebcoCard';
import { FlexScoreCard } from '../flex';
import { getPowerNebco, createPowerAction, createAction } from '../../services/api';

export default function TabPuissance({ site }) {
  const navigate = useNavigate();
  const siteId = site?.id;
  const [nebco, setNebco] = useState(null);
  const [nebcoLoading, setNebcoLoading] = useState(true);

  useEffect(() => {
    if (!siteId) {
      setNebcoLoading(false);
      return;
    }
    let cancelled = false;
    setNebcoLoading(true);
    getPowerNebco(siteId)
      .then((data) => {
        if (!cancelled) setNebco(data);
      })
      .catch(() => {
        if (!cancelled) setNebco(null);
      })
      .finally(() => {
        if (!cancelled) setNebcoLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  const handlePlanifier = (actionType) => {
    if (!siteId) return;
    createPowerAction(siteId, actionType)
      .then((data) => {
        if (data?.status === 'created') navigate('/actions');
      })
      .catch(() => {});
  };

  const handlePlanifierFlex = useCallback(
    (usageCode) => {
      createAction({
        site_id: siteId,
        title: `Optimiser flexibilite — ${usageCode} — ${site?.nom || ''}`,
        source_type: 'manual',
        source_id: `flex:${siteId}:${usageCode}`,
        category: 'ECONOMIE',
        severity: 'medium',
        priority: 3,
        idempotency_key: `flex:${siteId}:${usageCode}`,
      })
        .then(() => navigate('/actions'))
        .catch(() => navigate('/actions'));
    },
    [siteId, site?.nom, navigate]
  );

  if (!siteId) return null;

  return (
    <div className="space-y-6 p-6">
      <PowerPanel siteId={siteId} />

      <FlexScoreCard siteId={siteId} onPlanifier={handlePlanifierFlex} />

      {nebcoLoading ? (
        <div className="text-sm text-gray-400 py-4 text-center">Chargement analyse NEBCO...</div>
      ) : nebco && !nebco.error ? (
        <FlexNebcoCard data={nebco} />
      ) : null}

      {nebco?.eligible_technique && (
        <div className="flex gap-2">
          <button
            className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700"
            onClick={() => handlePlanifier('POWER_NEBCO')}
          >
            Initier démarche NEBCO
          </button>
          {nebco?.potentiel && (
            <span className="text-xs text-gray-500 self-center">
              Potentiel : {nebco.potentiel.revenu_central_eur_an?.toLocaleString()} €/an
            </span>
          )}
        </div>
      )}
    </div>
  );
}
