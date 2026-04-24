/**
 * SolAppShell — mobile drawer integration source-guards (Sprint 1 Vague B · B4)
 *
 * Vigilance V2 : 4 patterns a11y cumulés doivent être vérifiés.
 *   - role="dialog" (Drawer wrapper)
 *   - aria-modal="true" (Drawer wrapper)
 *   - Escape handler (Drawer hook)
 *   - body scroll lock (Drawer hook)
 *
 * Drawer.jsx est un composant existant qui implémente les 4 patterns +
 * focus trap Tab/Shift+Tab. Ce test vérifie le wiring côté SolAppShell.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const shellSrc = readFileSync(join(__dirname, '..', 'SolAppShell.jsx'), 'utf-8');
const drawerSrc = readFileSync(join(__dirname, '..', '..', 'ui', 'Drawer.jsx'), 'utf-8');

describe('SolAppShell mobile drawer wiring (B4)', () => {
  it('imports useMediaQuery from hooks', () => {
    expect(shellSrc).toMatch(/import\s+useMediaQuery\s+from\s+['"]\.\.\/hooks\/useMediaQuery['"]/);
  });

  it('imports Drawer from ui/Drawer', () => {
    expect(shellSrc).toMatch(/import\s+Drawer\s+from\s+['"]\.\.\/ui\/Drawer['"]/);
  });

  it('imports Menu icon (hamburger)', () => {
    expect(shellSrc).toMatch(/import\s*\{[^}]*\bMenu\b[^}]*\}\s*from\s*['"]lucide-react['"]/);
  });

  it('uses useMediaQuery breakpoint 767px (mobile <=)', () => {
    expect(shellSrc).toMatch(/useMediaQuery\(['"]\(max-width:\s*767px\)['"]\)/);
  });

  it('declares mobileDrawerOpen state', () => {
    expect(shellSrc).toMatch(/\[mobileDrawerOpen,\s*setMobileDrawerOpen\]\s*=\s*useState\(false\)/);
  });

  it('closes drawer on pathname change (navigation UX)', () => {
    expect(shellSrc).toMatch(/setMobileDrawerOpen\(false\)/);
    expect(shellSrc).toMatch(/\[location\.pathname\]/);
  });

  it('renders SolPanel only on desktop (!isMobile)', () => {
    expect(shellSrc).toMatch(/\{!isMobile && <SolPanel/);
  });

  it('renders Drawer wrapping SolPanel on mobile', () => {
    expect(shellSrc).toMatch(/\{isMobile && \(\s*<Drawer/);
    expect(shellSrc).toMatch(/side=["']left["']/);
  });

  it('hamburger rendered only on mobile with 44x44 hit area (WCAG 2.5.5)', () => {
    expect(shellSrc).toMatch(/\{isMobile && \(\s*<button/);
    expect(shellSrc).toMatch(/width:\s*44/);
    expect(shellSrc).toMatch(/height:\s*44/);
  });

  it('hamburger has aria-label FR + aria-expanded + aria-controls', () => {
    expect(shellSrc).toMatch(/aria-label=["']Ouvrir le menu de navigation["']/);
    expect(shellSrc).toMatch(/aria-expanded=\{mobileDrawerOpen\}/);
    expect(shellSrc).toMatch(/aria-controls=["']sol-panel-mobile-drawer["']/);
  });

  it('hamburger uses FOCUS_RING_SOL constant', () => {
    expect(shellSrc).toMatch(/\$\{FOCUS_RING_SOL\}/);
  });

  it('grid template adapts : 2-col on mobile, 3-col on desktop', () => {
    expect(shellSrc).toMatch(/isMobile \? '56px 1fr' : '56px 240px 1fr'/);
    expect(shellSrc).toMatch(/isMobile[\s\S]*?['"]"rail main" "rail timerail"['"]/);
  });
});

describe('SolAppShell — F2 fixes (aria-controls, double h2, header overflow)', () => {
  it('F2 : Drawer reçoit un id="sol-panel-mobile-drawer" (aria-controls match)', () => {
    expect(shellSrc).toMatch(/id=["']sol-panel-mobile-drawer["']/);
  });

  it('F2 : Drawer utilise ariaLabel="Navigation" au lieu de title (évite double h2)', () => {
    expect(shellSrc).toMatch(/ariaLabel=["']Navigation["']/);
    // title="Navigation" ne doit PAS apparaître dans le <Drawer> mobile
    const drawerBlock = shellSrc.match(/<Drawer[\s\S]*?<\/Drawer>/);
    if (drawerBlock) {
      expect(drawerBlock[0]).not.toMatch(/title="Navigation"/);
    }
  });

  it('F2 : header search label "Rechercher" + kbd masqués sur mobile (overflow fix)', () => {
    expect(shellSrc).toMatch(/\{!isMobile && \(\s*<>\s*<span>Rechercher<\/span>/);
  });

  it('F2 : Toggle Expert label vide sur mobile (overflow fix)', () => {
    expect(shellSrc).toMatch(/label=\{isMobile \? ['"]['"]\s*:\s*['"]Expert['"]\}/);
  });
});

describe('Drawer component — F2 conditional header + id prop', () => {
  it('F2 : accepte prop `id` propagée sur le div principal', () => {
    expect(drawerSrc).toMatch(/\bid,\s*\n/);
    expect(drawerSrc).toMatch(/id=\{id\}/);
  });

  it('F2 : accepte prop `ariaLabel` fallback pour dialog sans title', () => {
    expect(drawerSrc).toMatch(/\bariaLabel,\s*\n/);
    expect(drawerSrc).toMatch(/aria-label=\{ariaLabel \|\| title\}/);
  });

  it('F2 : header (h2 + close) rendu seulement si title truthy', () => {
    expect(drawerSrc).toMatch(/\{title \?/);
  });

  it('F2 : sans title, bouton Fermer absolute top-right encore accessible', () => {
    const absoluteCloseBlock = drawerSrc.match(/\) : \([\s\S]*?aria-label="Fermer"/);
    expect(absoluteCloseBlock).toBeTruthy();
    expect(drawerSrc).toMatch(/className="absolute top-2 right-2/);
  });
});

describe('Drawer component — 4 a11y patterns (V2 vigilance)', () => {
  it('pattern 1 : role="dialog"', () => {
    expect(drawerSrc).toMatch(/role=["']dialog["']/);
  });

  it('pattern 2 : aria-modal="true"', () => {
    expect(drawerSrc).toMatch(/aria-modal=["']true["']/);
  });

  it('pattern 3 : Escape handler closes drawer', () => {
    expect(drawerSrc).toMatch(/e\.key === ['"]Escape['"][\s\S]*?onClose\(\)/);
  });

  it('pattern 4 : body scroll lock (document.body.style.overflow = "hidden")', () => {
    expect(drawerSrc).toMatch(/document\.body\.style\.overflow\s*=\s*['"]hidden['"]/);
  });

  it('bonus : focus trap Tab/Shift+Tab cycles first/last focusable', () => {
    expect(drawerSrc).toMatch(/e\.key !== ['"]Tab['"]/);
    expect(drawerSrc).toMatch(/e\.shiftKey && document\.activeElement === first/);
  });

  it('bonus : auto-focus on open via requestAnimationFrame', () => {
    expect(drawerSrc).toMatch(/requestAnimationFrame\(\(\) => ref\.current\?\.focus\(\)\)/);
  });

  it('bonus : overlay click closes drawer', () => {
    expect(drawerSrc).toMatch(
      /className="absolute inset-0 bg-black\/40[\s\S]*?onClick=\{onClose\}/
    );
  });
});
