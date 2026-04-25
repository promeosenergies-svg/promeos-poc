/**
 * PROMEOS — Cockpit Sol interpreters (pure presentation helpers).
 *
 * Fonctions pures de présentation qui prennent des KPIs/données déjà
 * calculées par le backend (hooks existants inchangés) et retournent
 * du JSX humain pour les headlines des SolKpiCard.
 *
 * Voix Sol : vouvoiement, chiffre d'abord, toujours une issue, italic
 * sur les noms/sites emphatisés.
 *
 * Source éditoriale : docs/sol/SOL_V1_VOICE_GUIDE.md (guide éditorial)
 * Source visuelle : docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 *
 * ⚠ Zéro logique métier : toutes les données utilisées ici viennent en
 * props déjà calculées. Aucun fetch, aucun calcul. Que de la
 * présentation conditionnelle.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Cost headlines — KPI facture énergie
// ─────────────────────────────────────────────────────────────────────────────

export function interpretCost(kpis, scope) {
  const delta = kpis?.costDelta ?? 0;
  const drivers = (kpis?.topDriverSites || []).slice(0, 2).map((s) => s.name);

  if (Math.abs(delta) < 0.02) {
    return (
      <>Facture stable ce mois — votre patrimoine consomme au rythme attendu pour la saison.</>
    );
  }

  if (delta > 0.05) {
    if (drivers.length >= 2) {
      return (
        <>
          Hausse tirée par <em>{drivers[0]}</em> et <em>{drivers[1]}</em> — principalement
          saisonnière, une anomalie à vérifier.
        </>
      );
    }
    return <>Hausse à surveiller — une anomalie peut expliquer une partie de l'écart.</>;
  }

  if (delta > 0) {
    return <>Hausse modérée — principalement saisonnière.</>;
  }

  // delta < 0 → baisse
  const portfolio = scope?.orgName || 'votre patrimoine';
  return <>Baisse vs mois précédent — {portfolio} optimise ses usages.</>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Compliance headlines — KPI conformité DT
// ─────────────────────────────────────────────────────────────────────────────

export function interpretCompliance(compliance) {
  const score = compliance?.score ?? 0;
  const siteCount = compliance?.sitesAtRisk ?? 0;
  const leadSite = compliance?.leadRiskSite?.name;

  if (score >= 80) {
    return <>Score solide — tous vos sites sont en trajectoire Décret Tertiaire 2030.</>;
  }

  if (score >= 60) {
    if (siteCount >= 3 && leadSite) {
      return (
        <>
          Vous êtes en zone à risque — trois sites tirent le score vers le bas, <em>{leadSite}</em>{' '}
          en tête.
        </>
      );
    }
    return <>Score correct mais quelques sites à surveiller.</>;
  }

  return <>Vous êtes en zone critique — plusieurs sites exigent un plan d'action rapide.</>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Consumption headlines — KPI consommation patrimoine
// ─────────────────────────────────────────────────────────────────────────────

export function interpretConsumption(kpis, scope) {
  const delta = kpis?.consoDelta ?? 0;
  const drivers = (kpis?.topBaisseSites || []).slice(0, 2).map((s) => s.name);

  if (delta < -0.02) {
    if (drivers.length >= 2) {
      return (
        <>
          Vous consommez <em>moins</em> qu'à la même période l'an dernier — <em>{drivers[0]}</em> et{' '}
          <em>{drivers[1]}</em> portent la baisse.
        </>
      );
    }
    return <>Vous consommez moins qu'à la même période l'an dernier — bonne tendance.</>;
  }

  if (delta > 0.05) {
    return <>Consommation en hausse — températures + extensions d'activité à vérifier.</>;
  }

  return <>Consommation stable — attendu pour la saison et votre profil d'usage.</>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Narrative headline Sol — en haut du Cockpit
// ─────────────────────────────────────────────────────────────────────────────

export function buildCockpitNarrative({ alertsCount, topAlertTitle } = {}) {
  if (!alertsCount || alertsCount === 0) {
    return <>Rien d'urgent aujourd'hui. Votre patrimoine tourne bien.</>;
  }

  const pluriel = alertsCount > 1;
  const intro = pluriel
    ? `${alertsCount} points méritent votre attention cette semaine`
    : `1 point mérite votre attention cette semaine`;

  if (topAlertTitle) {
    return (
      <>
        {intro}. L'action la plus urgente concerne <em>{topAlertTitle}</em>, que je peux traiter à
        votre place.
      </>
    );
  }

  return <>{intro}.</>;
}

export function buildCockpitSubNarrative({ sitesCount, nextComexDays } = {}) {
  const sites = sitesCount ? `de ${sitesCount} sites` : '';
  const comex = nextComexDays
    ? ` Votre prochain comex est dans ${nextComexDays} jours — le rapport sera prêt la veille.`
    : '';

  return (
    <>
      Votre patrimoine {sites} consomme au rythme attendu pour la saison. Un site peut dériver de sa
      trajectoire Décret Tertiaire.{comex}
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Week cards builder — transforme alertes backend en props SolWeekCard
// ─────────────────────────────────────────────────────────────────────────────

export function buildWeekCards(alerts = []) {
  return alerts.slice(0, 3).map((alert) => {
    const tagKind = alertTagKind(alert.severity || alert.kind);
    return {
      id: alert.id,
      tagKind,
      tagLabel: alertTagLabel(tagKind),
      title: alert.title,
      body: alert.summary || alert.body,
      footerLeft: alert.impact || '',
      footerRight: alert.automatable ? 'Automatisable' : '',
      onClick: alert.navigateTo,
    };
  });
}

function alertTagKind(severity) {
  const s = (severity || '').toLowerCase();
  if (['success', 'ok', 'good', 'validated', 'bonne_nouvelle', 'succes'].includes(s)) {
    return 'succes';
  }
  if (['warning', 'attention', 'risk', 'à_regarder'].includes(s)) {
    return 'attention';
  }
  return 'afaire';
}

function alertTagLabel(tagKind) {
  return {
    attention: 'À regarder',
    afaire: 'À faire',
    succes: 'Bonne nouvelle',
  }[tagKind];
}
