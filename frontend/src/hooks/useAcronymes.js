/**
 * useAcronymes — Hook qui consomme l'API /api/v1/doctrine/acronymes
 * (SoT YAML backend — Sprint Grammaire v1 Phase 1.1, 2026-05-09).
 *
 * Cache module-scope : 1 fetch par session navigateur. Les données sont
 * statiques (définitions réglementaires) — pas de refresh périodique requis.
 *
 * Usage :
 *   const { data, loading, error } = useAcronymes();
 *   const entry = data?.TURPE;  // { short, long, narrative, source, ... }
 *
 * Zéro logique métier dans ce hook — affichage uniquement.
 * Les calculs (transform_acronym, has_forbidden_acronym) restent côté backend.
 */

import { useEffect, useState } from 'react';
import axios from 'axios';

// Cache module-scope : partagé entre toutes les instances du hook.
// Audit Phase 1.7 P1 : `_lastError` partagé entre instances Term montées en
// parallèle (closure locale `fetchError` ne se propageait qu'au 1er .then).
let _cache = null;
let _pending = null;
let _lastError = null;

/**
 * Réinitialise le cache (utile dans les tests unitaires).
 * @internal
 */
export function _resetAcronymesCache() {
  _cache = null;
  _pending = null;
  _lastError = null;
}

/**
 * @returns {{ data: Record<string, object>|null, loading: boolean, error: Error|null }}
 */
export function useAcronymes() {
  const [data, setData] = useState(_cache);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(_cache === null);

  useEffect(() => {
    // Déjà en cache — rien à faire
    if (_cache !== null) {
      setData(_cache);
      setLoading(false);
      return;
    }

    // Déduplique les fetch parallèles (promise partagée).
    // Audit Phase 1.7 P1 : l'erreur est désormais stockée dans `_lastError`
    // module-scope (la closure locale `fetchError` ne propageait qu'au 1er
    // composant ayant souscrit au .then() partagé).
    if (!_pending) {
      _pending = axios
        .get('/api/v1/doctrine/acronymes')
        .then((response) => {
          // Le payload est soit { acronymes: {...}, version: ..., ... }
          // soit directement un dict acronymes selon la version de l'API
          _cache = response.data?.acronymes ?? response.data ?? {};
          _lastError = null;
          return _cache;
        })
        .catch((err) => {
          console.warn('[useAcronymes] fetch /api/v1/doctrine/acronymes failed', err);
          _lastError = err;
          // Fallback silencieux : dict vide — ne bloque pas le rendu
          _cache = {};
          return _cache;
        })
        .finally(() => {
          // Permet une nouvelle tentative future si reset cache
          _pending = null;
        });
    }

    _pending?.then((resolved) => {
      setData(resolved);
      setLoading(false);
      // Propage l'erreur module-scope (partagée entre toutes les instances).
      if (_lastError) setError(_lastError);
    });
  }, []); // pas de dépendance : données statiques, 1 seul fetch

  return { data, loading, error };
}
