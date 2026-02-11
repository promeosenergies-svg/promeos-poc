import { AlertTriangle } from 'lucide-react';
import Button from './Button';

export default function ErrorState({ title = 'Erreur', message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <AlertTriangle size={28} className="text-red-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-700 mb-1">{title}</h3>
      {message && <p className="text-sm text-gray-500 mb-6 max-w-md">{message}</p>}
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>Reessayer</Button>
      )}
    </div>
  );
}
