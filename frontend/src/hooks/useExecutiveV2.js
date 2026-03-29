/**
 * useExecutiveV2 — Fetch unique pour la vue exécutive V1+.
 * Aucun calcul métier — le backend fait tout.
 */
import { useState, useEffect, useRef } from 'react';
import api from '../services/api/core';

export function useExecutiveV2() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    api
      .get('/cockpit/executive-v2')
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Erreur chargement vue exécutive');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, []);

  return { data, loading, error };
}
