/**
 * PROMEOS — Démo Marie 90s avec capture VIDÉO WebM (pour Loom narré).
 *
 * Variante de demo-marie-90s.mjs qui enregistre une vidéo continue
 * (Playwright recordVideo) au lieu de screenshots ponctuels.
 *
 * Le user enregistre ensuite sa narration en voice-over par-dessus la
 * vidéo brute (Loom / OBS / Final Cut). Le script narration FR canonique
 * vit dans le même dossier de sortie : `narration-script-90s.md`.
 *
 * Sortie : tools/playwright/captures/demo-marie-90s/
 *   - video-90s.webm (1920×1080, ~10-15s en mode demo accéléré)
 *   - narration-script-90s.md (script à lire en voice-over)
 *
 * Pour la version pitch live ralentie : `--slow=600` ralentit chaque
 * action de 600ms, donnant ~30-60s de vidéo cohérente avec une voix.
 *
 * Usage :
 *   node tools/playwright/demo-marie-90s-video.mjs --slow=800
 */

import { chromium } from 'playwright';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { resolve, join } from 'path';

const FRONTEND_URL = process.env.PROMEOS_FRONTEND_URL || 'http://localhost:5175';
const AUTH_EMAIL = 'promeos@promeos.io';
const AUTH_PASSWORD = 'promeos2024';
const OUT_DIR = resolve(process.cwd(), 'tools', 'playwright', 'captures', 'demo-marie-90s');

const args = process.argv.slice(2);
const SLOW_MO = (() => {
  const a = args.find((s) => s.startsWith('--slow='));
  return a ? parseInt(a.slice(7), 10) : 800; // 800ms par action par défaut → ~60s vidéo
})();

const log = (s) => console.log(`[${new Date().toISOString().slice(11, 23)}] ${s}`);

async function main() {
  if (!existsSync(OUT_DIR)) mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true, slowMo: SLOW_MO });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'fr-FR',
    deviceScaleFactor: 1,
    recordVideo: {
      dir: OUT_DIR,
      size: { width: 1920, height: 1080 },
    },
  });
  const page = await context.newPage();

  log(`Recording video (slowMo=${SLOW_MO}ms par action) → WebM 1920x1080`);

  // Auth
  await page.goto(FRONTEND_URL + '/login', { waitUntil: 'domcontentloaded' });
  const loginResp = await page.evaluate(
    async ({ email, password }) => {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });
      return res.json();
    },
    { email: AUTH_EMAIL, password: AUTH_PASSWORD }
  );
  if (!loginResp.access_token) {
    console.error('Login failed:', loginResp);
    await browser.close();
    process.exit(1);
  }
  await page.evaluate((t) => localStorage.setItem('promeos_token', t), loginResp.access_token);

  // ── Scène 1 : Cockpit hero (15s) ────────────────────────────────
  log('SCÈNE 1 — Cockpit hero');
  await page.goto(FRONTEND_URL + '/cockpit', { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {});
  await page.waitForSelector('[data-testid^="sol-event-card-"]', { timeout: 8000 });
  await page.waitForTimeout(3500); // Marie regarde le hero

  // ── Scène 2 : zoom sur la première card (15s) ───────────────────
  log('SCÈNE 2 — Marie repère la card critique billing');
  const firstCard = page.locator('[data-testid^="sol-event-card-"]').first();
  await firstCard.scrollIntoViewIfNeeded();
  await firstCard.hover();
  await page.waitForTimeout(2500);

  // ── Scène 3 : ouverture popover methodology (15s) ───────────────
  log('SCÈNE 3 — Marie clique sur l\'icône Info');
  const infoBtn = firstCard.locator('button[aria-label="Voir la méthodologie de calcul"]').first();
  if (await infoBtn.isVisible().catch(() => false)) {
    await infoBtn.click();
    await page.waitForTimeout(4500); // temps de lecture du popover
  }

  // ── Scène 4 : navigation CTA (15s) ──────────────────────────────
  log('SCÈNE 4 — Marie ouvre Bill-Intel pour traiter');
  const cardBox = await firstCard.boundingBox();
  if (cardBox) {
    await page.mouse.click(cardBox.x + cardBox.width / 2, cardBox.y + 50);
    await page.waitForLoadState('domcontentloaded', { timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(3500); // landing observée
  }

  log('Fin enregistrement vidéo');
  await context.close();
  await browser.close();

  // Renommer la vidéo (Playwright génère un nom UUID)
  const { readdirSync, renameSync } = await import('fs');
  const videos = readdirSync(OUT_DIR).filter((f) => f.endsWith('.webm') && f !== 'video-90s.webm');
  if (videos.length) {
    renameSync(join(OUT_DIR, videos[0]), join(OUT_DIR, 'video-90s.webm'));
    log(`Vidéo → ${join(OUT_DIR, 'video-90s.webm')}`);
  }

  // ── Script narration FR canonique (Loom voice-over) ─────────────
  const narration = `# Démo Marie 90s — Script narration voice-over

> **Personnage** : Marie, 38 ans, DAF tertiaire d'un groupe régional,
> 12 sites bureaux + retail. Elle ouvre PROMEOS Sol pendant son café.
> 5 minutes par jour. Elle veut savoir : où mes euros partent, qui décide
> quoi, sur quoi je peux compter.
>
> **Asset à narrer** : \`video-90s.webm\` (vidéo silencieuse Playwright).
> **Outil suggéré** : Loom (voice-over par-dessus la vidéo).

---

## SCÈNE 1 — Cockpit hero (0:00 → 0:15)

> *« Marie ouvre PROMEOS Sol. En haut : son exposition financière*
> *réglementaire, son score conformité, ses leviers d'économies estimés.*
> *Trois chiffres, trois sources, trois actions possibles. Pas de tableau.*
> *Pas de jargon. Juste son patrimoine, raconté. »*

**Voix off** :
> « Bonjour. Vue exécutive de Marie. 26 200 € d'exposition pénalité,
> conformité 37 sur 100, 25 500 € par an de leviers identifiés. Tout est
> prêt en moins de 5 secondes. »

---

## SCÈNE 2 — Carte événement critique (0:15 → 0:30)

> *« Marie remarque la première carte rouge : 48 anomalies de facturation*
> *détectées par le shadow billing de PROMEOS, réparties sur 5 sites,*
> *15 000 € à récupérer. Source : factures fournisseur. Fiabilité élevée.*
> *Suivi : DAF — c'est elle. »*

**Voix off** :
> « Premier événement critique : 48 anomalies de facturation détectées
> automatiquement par notre shadow billing. Marie voit l'impact, le
> nombre de sites concernés, la source de la donnée et qui doit la
> traiter. Tout sans cliquer. »

---

## SCÈNE 3 — Popover methodology (0:30 → 0:45)

> *« Avant d'aller en CODIR, Marie veut savoir comment c'est calculé.*
> *Un clic sur l'icône info. Le popover lui explique : cumul des pertes*
> *estimées par statut de traitement, récupérations cette année calculées*
> *depuis le 1ᵉʳ janvier. Sourcé. Vérifiable. Défendable. »*

**Voix off** :
> « PROMEOS expose la formule de calcul en un clic. Marie peut citer la
> méthodologie en CODIR sans paniquer. Plus aucun chiffre opaque —
> chaque euro affiché est traçable. C'est notre engagement règle d'or :
> fiable, vérifiable, simple. »

---

## SCÈNE 4 — Navigation contextuelle CTA (0:45 → 1:00)

> *« Marie clique sur la carte. PROMEOS l'amène directement à Bill-Intel,*
> *sur le détail des 48 anomalies, prêt à initier les contestations.*
> *Pas de menu, pas de filtre à régler. La navigation suit l'urgence. »*

**Voix off** :
> « Un clic. Marie atterrit sur la liste des 48 anomalies, contexte
> préservé, action prête. PROMEOS Sol n'est pas un dashboard — c'est un
> assistant exécutif qui pousse l'information utile au bon moment, à la
> bonne personne, dans la bonne grammaire. »

---

## Conclusion (0:60 → 1:30 si version étendue)

> « Marie a vu son patrimoine, compris l'origine des chiffres, et
> initié l'action en moins d'une minute. C'est ce que nous appelons
> la grammaire éditoriale Sol. Aucun acteur du marché n'a cette
> approche aujourd'hui. PROMEOS Sol est la première plateforme
> énergie B2B qui parle CFO, pas dashboard. »

---

**Tip enregistrement Loom** :
1. Lancer Loom Desktop
2. Importer \`video-90s.webm\` (timeline)
3. Enregistrer voix off en suivant les marqueurs 0:00 / 0:15 / 0:30 / 0:45
4. Export MP4 1080p pour pitch deck slide 4

**Tip pitch deck Sequoia** :
- Slide 4 = vidéo 90s embed Loom + 3 KPIs SolEventCard agrandis dessous
- Slide 5 = capture popover methodology zoom + tagline « le seul outil
  qui expose sa formule en 1 clic »
`;

  writeFileSync(join(OUT_DIR, 'narration-script-90s.md'), narration);
  log(`Script narration → ${join(OUT_DIR, 'narration-script-90s.md')}`);
  console.log(
    `\n✓ 4 scènes capturées avec slowMo=${SLOW_MO}ms.\n  - video-90s.webm prêt pour Loom voice-over\n  - narration-script-90s.md = script FR canonique\n`
  );
}

main().catch((err) => {
  console.error('[FATAL]', err);
  process.exit(1);
});
