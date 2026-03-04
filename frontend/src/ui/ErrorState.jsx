import { AlertTriangle } from 'lucide-react';
import Button from './Button';

export default function ErrorState({ title = 'Erreur', message, onRetry, debug, actions }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <AlertTriangle size={28} className="text-red-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-700 mb-1">{title}</h3>
      {message && <p className="text-sm text-gray-500 mb-6 max-w-md">{message}</p>}
      <div className="flex items-center gap-3">
        {onRetry && (
          <Button variant="secondary" onClick={onRetry}>
            Reessayer
          </Button>
        )}
        {actions}
      </div>
      {debug && (
        <div className="mt-4 px-4 py-2 bg-gray-100 rounded text-xs text-gray-500 font-mono max-w-md text-left">
          {debug.status && <div>status: {debug.status}</div>}
          {debug.error_code && <div>error_code: {debug.error_code}</div>}
          {debug.trace_id && <div>trace_id: {debug.trace_id}</div>}
          {debug.hint && <div>hint: {debug.hint}</div>}
          {debug.request_url && <div className="truncate">request_url: {debug.request_url}</div>}
        </div>
      )}
    </div>
  );
}
