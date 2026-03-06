import { useEffect } from 'react';
import { useToast } from '../ui/ToastProvider';

/**
 * Wrapper autour d'un résultat API { data, loading, error, refetch }.
 * Affiche automatiquement un toast sur erreur.
 */
export function useApiWithToast(apiResult) {
  const { toast } = useToast();
  useEffect(() => {
    if (apiResult.error) {
      toast(`Erreur : ${apiResult.error.message || apiResult.error}`, 'error');
    }
  }, [apiResult.error]); // eslint-disable-line react-hooks/exhaustive-deps
  return apiResult;
}
