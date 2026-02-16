/**
 * PROMEOS — Purchase Error Boundary (Brique 3)
 * Local error boundary for PurchasePage wizard that allows retry without full page reload.
 */
import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class PurchaseErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // Log to console in dev
    if (import.meta.env.DEV) {
      console.error('[PurchaseErrorBoundary]', error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center">
          <AlertTriangle size={40} className="text-red-500 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-red-800 mb-2">Erreur dans le module Achat</h3>
          <p className="text-sm text-red-600 mb-4 max-w-md mx-auto">
            {this.state.error?.message || 'Une erreur inattendue est survenue dans le simulateur.'}
          </p>
          <button
            onClick={this.handleRetry}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-600 text-white rounded-lg text-sm font-semibold hover:bg-red-700 transition"
          >
            <RefreshCw size={14} /> Reessayer
          </button>
          {import.meta.env.DEV && this.state.errorInfo && (
            <details className="mt-4 text-left bg-red-100 rounded-lg p-4 text-xs text-red-800 max-h-40 overflow-auto">
              <summary className="cursor-pointer font-medium">Stack trace (dev only)</summary>
              <pre className="mt-2 whitespace-pre-wrap">{this.state.errorInfo.componentStack}</pre>
            </details>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
