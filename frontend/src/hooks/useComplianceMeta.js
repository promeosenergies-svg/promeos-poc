/**
 * PROMEOS — useComplianceMeta
 * Charge la configuration publique du scoring conformité depuis /api/compliance/meta.
 * Retourne null pendant le chargement ou en cas d'erreur (le frontend doit avoir un fallback).
 */
import { useState, useEffect } from 'react';
import api from '../services/api';

let _cachedMeta = null;

export function useComplianceMeta() {
  const [meta, setMeta] = useState(_cachedMeta);

  useEffect(() => {
    if (_cachedMeta) {
      setMeta(_cachedMeta);
      return;
    }
    api
      .get('/compliance/meta')
      .then((r) => {
        _cachedMeta = r.data;
        setMeta(r.data);
      })
      .catch(() => null); // silently fail — evidence.fixtures.js a des valeurs par défaut
  }, []);

  return meta;
}
