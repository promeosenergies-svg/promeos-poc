import { Inbox } from 'lucide-react';
import Button from './Button';

export default function EmptyState({ icon: Icon = Inbox, title, text, ctaLabel, onCta }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Icon size={48} className="text-gray-300 mb-4" />
      <h3 className="text-lg font-semibold text-gray-700 mb-1">{title}</h3>
      {text && <p className="text-sm text-gray-500 mb-6 max-w-md">{text}</p>}
      {ctaLabel && onCta && (
        <Button onClick={onCta}>{ctaLabel}</Button>
      )}
    </div>
  );
}
