import { Component } from 'react';
import { logger } from '../services/logger';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Collect page + orgId context for structured debugging
    const page = window.location.pathname;
    let orgId = null;
    try {
      const scope = JSON.parse(localStorage.getItem('promeos_scope') || '{}');
      orgId = scope.orgId ?? null;
    } catch {
      /* ignore */
    }

    logger.error('ErrorBoundary', error.message, {
      page,
      orgId,
      stack: error.stack,
      componentStack: errorInfo?.componentStack,
    });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-8">
          <div className="text-5xl mb-4">&#9888;</div>
          <h2 className="text-xl font-bold text-gray-800 mb-2">Une erreur est survenue</h2>
          <p className="text-gray-500 text-sm mb-4 max-w-md">
            {this.state.error?.message || 'Erreur inattendue.'}
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition"
            >
              Reessayer
            </button>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.assign('/');
              }}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm hover:bg-gray-300 transition"
            >
              Retour a l'accueil
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
