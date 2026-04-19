/**
 * PROMEOS — /_sol_showcase (Gate 1)
 *
 * Page de validation visuelle Phase 1 : rend les 21 composants Sol avec
 * des props démo, sans appel API, sans scope context.
 *
 * But : screenshot envoyé pour validation Gate 1.
 *
 * Note typo : les espaces fines (U+202F) et insécables (U+00A0) sont
 * utilisées telles quelles dans le source. JSX plain-text n'interprète
 * pas les séquences \uXXXX.
 */
import React, { useState } from 'react';
import {
  SolAppShell,
  SolPageHeader,
  SolHeadline,
  SolSubline,
  SolKpiRow,
  SolKpiCard,
  SolSourceChip,
  SolStatusPill,
  SolSectionHead,
  SolHero,
  SolPendingBanner,
  SolWeekGrid,
  SolWeekCard,
  SolLoadCurve,
  SolLayerToggle,
  SolInspectDoc,
  SolExpertGrid,
  SolJournal,
  SolDrawer,
  SolButton,
  SolBreadcrumb,
  SolEntityCard,
  SolTimeline,
  SolListPage,
  SolExpertToolbar,
  SolExpertGridFull,
  SolPagination,
} from '../ui/sol';

// U+202F thin NBSP et U+00A0 NBSP
// Data shape attendue par SolLoadCurve : [{ time, value }]
const LOAD_DATA = Array.from({ length: 48 }, (_, i) => {
  const hour = Math.floor(i / 2);
  const minute = (i % 2) * 30;
  const baseKw = 40 + Math.sin((i - 8) * 0.3) * 35 + (hour >= 10 && hour <= 16 ? 30 : 0);
  return {
    time: `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`,
    value: Math.max(20, Math.round(baseKw + ((i * 7) % 5))),
  };
});

const JOURNAL = [
  {
    key: 'j1',
    date: '15 avr · 14 h 32',
    actor: 'SOL',
    action: 'Envoi courrier contestation facture mars · site Lyon Sud',
    status: 'Envoyé',
    statusKind: 'ok',
  },
  {
    key: 'j2',
    date: '14 avr · 09 h 18',
    actor: 'SOL',
    action: "Proposition d'optimisation TURPE · reprogrammation HC",
    status: 'En attente',
    statusKind: 'att',
  },
  {
    key: 'j3',
    date: '13 avr · 17 h 54',
    actor: 'Amine',
    action: "Annulation envoi courrier litige consommation Nice",
    status: 'Annulé',
    statusKind: 'risk',
  },
];

const TIMELINE_EVENTS = [
  {
    datetime: '12 avr · 09 h 04',
    type: 'Upload',
    title: 'Facture mars Engie reçue',
    description: 'Fichier Enedis M023 joint · 48 pas de temps validés.',
    tone: 'neutral',
  },
  {
    datetime: '14 avr · 11 h 22',
    type: 'Anomalie',
    title: 'Écart TURPE détecté · Lyon Sud',
    description: 'Composante Gestion : 21,93 € HT vs 15,00 € contractuels.',
    tone: 'attention',
  },
  {
    datetime: '15 avr · 14 h 32',
    type: 'Action Sol',
    title: 'Courrier contestation envoyé',
    description: 'Envoi réversible 24 h · suivi de lecture activé.',
    tone: 'succes',
    deeplink: '/journal#j1',
  },
];

const EXPERT_COLS = [
  { key: 'site', label: 'Site', align: 'left', num: false },
  { key: 'surface', label: 'Surface', align: 'right', num: true },
  { key: 'conso', label: 'Conso', align: 'right', num: true },
  { key: 'score', label: 'Score DT', align: 'right', num: true },
  { key: 'status', label: 'État', align: 'right', num: false },
];
const EXPERT_ROWS = [
  { key: 'lyon', cells: { site: 'Lyon Sud', surface: '3 240 m²', conso: '412 MWh', score: '68', status: <SolStatusPill kind="att">Att</SolStatusPill> } },
  { key: 'nice', cells: { site: 'Nice Tertiaire', surface: '2 180 m²', conso: '298 MWh', score: '54', status: <SolStatusPill kind="risk">Risque</SolStatusPill> } },
  { key: 'paris', cells: { site: 'Paris Centre', surface: '4 820 m²', conso: '541 MWh', score: '82', status: <SolStatusPill kind="ok">Conforme</SolStatusPill> } },
];

// Pattern B démo — filtres, rows, pagination
const LIST_COLUMNS = [
  { id: 'site', label: 'Site', sortable: true, align: 'left' },
  { id: 'type', label: 'Type', sortable: true, align: 'left' },
  { id: 'severity', label: 'Sévérité', sortable: true, align: 'left' },
  { id: 'impact', label: 'Impact', sortable: true, align: 'right' },
  { id: 'status', label: 'Statut', sortable: true, align: 'left' },
];
const LIST_ROWS = [
  { id: 1, cells: { site: 'Lyon Sud', type: 'Facturation', severity: 'Critique', impact: '1 847 €', status: 'À traiter' }, tone: 'refuse' },
  { id: 2, cells: { site: 'Nice Hôtel', type: 'Conso', severity: 'Élevée', impact: '890 €', status: 'En cours' }, tone: 'attention' },
  { id: 3, cells: { site: 'Paris Centre', type: 'BACS', severity: 'Moyenne', impact: '420 €', status: 'Ouvert' } },
  { id: 4, cells: { site: 'Toulouse', type: 'Facturation', severity: 'Faible', impact: '120 €', status: 'Ouvert' } },
  { id: 5, cells: { site: 'Marseille', type: 'Conso', severity: 'Moyenne', impact: '650 €', status: 'Résolu' }, tone: 'succes' },
];
const LIST_FILTERS = [
  { id: 'site', label: 'Site', options: [{ value: 'lyon', label: 'Lyon Sud' }, { value: 'nice', label: 'Nice Hôtel' }] },
  { id: 'type', label: 'Type', options: [{ value: 'facturation', label: 'Facturation' }, { value: 'conso', label: 'Conso' }] },
  { id: 'severity', label: 'Sévérité', options: [{ value: 'critical', label: 'Critique' }, { value: 'high', label: 'Élevée' }] },
];

export default function SolShowcase() {
  const [mode, setMode] = useState('surface');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [listFilters, setListFilters] = useState({ site: 'lyon' });
  const [listSelected, setListSelected] = useState(new Set());
  const [listPage, setListPage] = useState(1);

  return (
    <SolAppShell
      railProps={{ role: 'dg_owner', isExpert: true }}
      panelProps={{
        desc: 'Votre cockpit énergétique, semaine du 14 avril.',
        badges: { '/conformite': '3' },
        isExpert: true,
      }}
      timerailProps={{
        currentTariff: 'HP',
        currentTariffEndsAt: '22 h',
        weekLabel: 'Sem. 16 · avril',
        dtTrajectory: { current: -12.4, target: -25 },
        solStatus: 'en veille · 3 actions en attente',
      }}
      cartoucheState="proposing"
      onCartoucheClick={() => setDrawerOpen(true)}
    >
      <SolPageHeader
        kicker="Showcase · 21 composants Sol · V2 raw"
        title="Bonjour — voici la galerie"
        titleEm="Sol"
        narrative="Les 21 composants de la refonte, rendus avec des props démo."
        subNarrative="Cette page sert à valider le Gate 1 avant câblage sur données réelles."
        rightSlot={<SolLayerToggle value={mode} onChange={setMode} />}
      />

      <SolHeadline>
        <em>Vous êtes</em> à 62/100 cette semaine. Deux sites tirent la facture vers le haut —
        Sol peut préparer les courriers.
      </SolHeadline>
      <SolSubline>
        La saisonnalité prolonge le pic du matin, mais le contrat limite les leviers jusqu&apos;au
        renouvellement d&apos;octobre.
      </SolSubline>

      <SolHero
        chip="Sol propose · action agentique"
        title="Contester la facture mars · site Lyon Sud"
        description="Deux anomalies détectées sur le TURPE et la CTA. Écart estimé : 1 847 €. Courrier pré-rédigé, envoi réversible 24 h."
        metrics={[
          { value: '1 847 €', label: 'écart estimé' },
          { value: '24 h', label: 'annulable' },
          { value: '2', label: 'anomalies' },
        ]}
        primaryLabel="Voir ce que j'enverrai"
        onPrimary={() => setDrawerOpen(true)}
        secondaryLabel="Plus tard"
        onSecondary={() => {}}
      />

      <SolPendingBanner
        message="Sol enverra le courrier"
        countdown="23 h 59 min"
        onEdit={() => {}}
        onCancel={() => {}}
      />

      <SolSectionHead title="Vos indicateurs · mars" meta="3 kpis · sources : factures, RegOps, Enedis" />
      <SolKpiRow>
        <SolKpiCard
          label="Facture énergie · mars"
          value="47 382"
          unit="€"
          delta={{ direction: 'up', text: '▲ +8,2 % vs fév' }}
          headline="Hausse tirée par Lyon et Nice."
          source={{ kind: 'factures', origin: '3 fournisseurs', freshness: 'mars 2026' }}
        />
        <SolKpiCard
          label="Conformité DT"
          value="62"
          unit="/100"
          delta={{ direction: 'down', text: '▼ -2 pts vs fév' }}
          headline="En zone à risque avant 2030."
          source={{ kind: 'calcul', origin: 'RegOps canonique', freshness: 'maj 23 h' }}
        />
        <SolKpiCard
          label="Consommation · patrimoine"
          value="1 847"
          unit="MWh"
          delta={{ direction: 'down', text: '▼ -4,1 % vs mars 2024' }}
          headline="Baisse organique sites tertiaires."
          source={{ kind: 'enedis', origin: 'Enedis + GRDF' }}
        />
      </SolKpiRow>

      <SolSectionHead title="Votre semaine" meta="3 signaux" />
      <SolWeekGrid>
        <SolWeekCard
          tag="À regarder"
          tagKind="attention"
          title="Dérive contrat gaz · Lyon"
          body="+18 % de consommation sur 14 jours, à investiguer avec le site."
          footer="Détecté par Sol · 15 avril"
        />
        <SolWeekCard
          tag="À faire"
          tagKind="afaire"
          title="Déclaration OPERAT · échéance 30 avril"
          body="Données 2024 à verser, 8 sites concernés."
          footer="Sol peut pré-remplir"
          onClick={() => {}}
        />
        <SolWeekCard
          tag="Bonne nouvelle"
          tagKind="succes"
          title="APER Paris Centre validée"
          body="Dossier solarisation parking accepté par la DDT."
          footer="12 avril · archivé"
        />
      </SolWeekGrid>

      <SolSectionHead title="Courbe de charge · 24 h" meta="site critique · pas 30 min" />
      <div style={{ background: 'var(--sol-bg-paper)', border: '1px solid var(--sol-rule)', borderRadius: 8, padding: 16, boxShadow: '0 1px 2px rgba(15, 23, 42, 0.03)' }}>
        <SolLoadCurve
          data={LOAD_DATA}
          peakPoint={{ time: '14:00', value: 118, label: 'pic 14 h · 118 kW' }}
          hpStart="06:00"
          hpEnd="22:00"
          sourceChip={<SolSourceChip kind="enedis" origin="M023" freshness="complète" />}
        />
      </div>

      {mode === 'inspect' && (
        <>
          <SolSectionHead title="Inspect · la logique Sol" meta="prose éditoriale · Fraunces 15/1.7" />
          <SolInspectDoc>
            <p>
              Le score conformité passe de 64 à 62 parce que deux obligations n&apos;ont pas progressé
              ce mois-ci : la <strong>déclaration OPERAT</strong> et l&apos;<strong>audit SMÉ</strong>
              {' '}sur le périmètre tertiaire.
            </p>
            <p>
              Sol observe également une dérive gaz sur le site de Lyon Sud depuis 14 jours. Sans
              correction, la trajectoire 2030 glisse de deux points. <em>Aucun levier ne peut
              déroger à la règle sans votre validation.</em>
            </p>
          </SolInspectDoc>
        </>
      )}

      {mode === 'expert' && (
        <>
          <SolSectionHead title="Expert · table sites" meta="6 colonnes triables" />
          <SolExpertGrid columns={EXPERT_COLS} rows={EXPERT_ROWS} />
        </>
      )}

      <SolSectionHead title="Journal des actions Sol" meta="append-only · traçabilité" />
      <SolJournal entries={JOURNAL} />

      <SolSectionHead
        title="Pattern C · fiche détail (Lot 3)"
        meta="SolBreadcrumb · SolEntityCard · SolTimeline · SolDetailPage wrapper"
      />
      <SolBreadcrumb
        backTo="/patrimoine"
        segments={[
          { label: 'Patrimoine', to: '/patrimoine' },
          { label: 'Tertiaire', to: '/patrimoine?type=tertiaire' },
          { label: 'Lyon Sud' },
        ]}
      />
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(260px, 300px) minmax(0, 1fr)',
          gap: 24,
          alignItems: 'flex-start',
        }}
      >
        <SolEntityCard
          title="Lyon Sud"
          subtitle="Tertiaire · 3 240 m² · OPERAT actif"
          status={{ label: 'À traiter', tone: 'afaire' }}
          fields={[
            { label: 'PDL', value: '14511234567890', mono: true },
            { label: 'Fournisseur', value: 'Engie' },
            { label: 'Contrat', value: 'Fixe 36 mois · fin 10/2026' },
            { label: 'Conso 2024', value: '412 MWh', mono: true },
            { label: 'Score DT', value: '68 / 100', mono: true },
          ]}
          actions={
            <>
              <SolButton variant="secondary" onClick={() => {}}>
                Voir factures
              </SolButton>
              <SolButton variant="ghost" onClick={() => {}}>
                Éditer
              </SolButton>
            </>
          }
        />
        <SolTimeline events={TIMELINE_EVENTS} onNavigate={() => {}} />
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 24, flexWrap: 'wrap' }}>
        <SolButton variant="primary" onClick={() => {}}>Primary</SolButton>
        <SolButton variant="secondary" onClick={() => {}}>Secondary</SolButton>
        <SolButton variant="ghost" onClick={() => {}}>Ghost</SolButton>
        <SolButton variant="agentic" onClick={() => {}}>Agentic</SolButton>
        <SolSourceChip kind="factures" origin="3 fournisseurs" />
      </div>

      <SolSectionHead
        title="Pattern B · liste drillable (Lot 2)"
        meta="SolListPage · SolExpertToolbar · SolExpertGridFull · SolPagination"
      />
      <SolExpertToolbar
        filters={LIST_FILTERS}
        activeFilters={listFilters}
        onFilterChange={(id, v) => setListFilters((prev) => ({ ...prev, [id]: v }))}
        searchPlaceholder="Rechercher un site, un type…"
        searchValue=""
        onSearchChange={() => {}}
        selection={{ count: listSelected.size, total: LIST_ROWS.length }}
        selectionActions={listSelected.size > 0 ? [
          { label: 'Contester sélection', onClick: () => {}, variant: 'primary' },
        ] : []}
      />
      <SolExpertGridFull
        columns={LIST_COLUMNS}
        rows={LIST_ROWS}
        sortBy={{ column: 'impact', direction: 'desc' }}
        onSort={() => {}}
        selectable
        selectedIds={listSelected}
        onSelectionChange={setListSelected}
        onRowClick={() => setDrawerOpen(true)}
        highlightColumn="impact"
      />
      <SolPagination
        page={listPage}
        pageSize={5}
        total={42}
        onPageChange={setListPage}
        onPageSizeChange={() => {}}
      />

      <SolDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title="Aperçu du courrier de contestation"
        width={540}
      >
        <SolInspectDoc>
          <p><em>Madame, Monsieur,</em></p>
          <p>
            Je relève sur votre facture de mars deux écarts avec la grille TURPE 7 publiée par la
            CRE en 2024 :
          </p>
          <p>
            <strong>— Composante Gestion</strong> : 21,93 € HT au lieu de 15,00 € HT contractuels.
            <br />
            <strong>— CTA</strong> : 10,11 % appliquée au lieu de 4,71 % applicables depuis
            le 1er février 2026.
          </p>
          <p>
            Je vous prie de bien vouloir corriger ces écarts sur la prochaine facturation et d&apos;en
            tenir compte pour la période mars 2026.
          </p>
          <p style={{ color: 'var(--sol-ink-500)', fontSize: 13 }}>
            <em>Ce courrier est généré par Sol · envoi réversible 24 h.</em>
          </p>
        </SolInspectDoc>
        <div style={{ display: 'flex', gap: 10, marginTop: 18 }}>
          <SolButton variant="agentic">Envoyer maintenant</SolButton>
          <SolButton variant="secondary" onClick={() => setDrawerOpen(false)}>Plus tard</SolButton>
        </div>
      </SolDrawer>
    </SolAppShell>
  );
}
