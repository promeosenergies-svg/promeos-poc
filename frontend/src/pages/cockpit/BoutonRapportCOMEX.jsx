import { FileText } from 'lucide-react';

/**
 * Bouton "Rapport COMEX" — déclenche l'impression navigateur.
 * Pattern existant DossierPrintView : window.print()
 */
export default function BoutonRapportCOMEX() {
  return (
    <button
      onClick={() => window.print()}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-900 text-white text-xs font-medium hover:bg-gray-800 transition focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1"
      title="Exporter la vue exécutive en PDF via l'impression navigateur"
    >
      <FileText size={13} />
      Rapport COMEX ↗
    </button>
  );
}
