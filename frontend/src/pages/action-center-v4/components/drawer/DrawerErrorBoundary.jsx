/**
 * Action Center V4 P0 fix (2026-05-25) — error boundary local autour du
 * drawer V4 (audit deep §3.3 P0-2). Avant ce composant, toute exception
 * runtime dans un onglet ou une mutation faisait crasher silencieusement
 * le drawer sans signal côté utilisateur ; ici on attrape, on logge et on
 * rend ItemNotFoundState variant='unexpected' avec CTA retour au hub.
 *
 * Class component obligatoire car React 18 hooks ne supportent pas encore
 * getDerivedStateFromError. Couvre toute la sous-arbre passée en children.
 */
import { Component } from 'react';

import { ItemNotFoundState } from './ItemNotFoundState';

export class DrawerErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    // Le drawer reste fonctionnel : on log mais on ne casse pas le hub
    // parent. La console error est captée par le smoke Playwright pour
    // qualifier la régression.
    // eslint-disable-next-line no-console
    console.error('[DrawerErrorBoundary] runtime error caught', error, info);
  }

  handleReset = () => {
    this.setState({ hasError: false });
    this.props.onClose?.();
  };

  render() {
    if (this.state.hasError) {
      return <ItemNotFoundState variant="unexpected" onClose={this.handleReset} />;
    }
    return this.props.children;
  }
}
