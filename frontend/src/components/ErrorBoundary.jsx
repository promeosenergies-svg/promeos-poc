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
    logger.error('ErrorBoundary', error.message, {
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
          <button
            onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/'; }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition"
          >
            Retour a l'accueil
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
