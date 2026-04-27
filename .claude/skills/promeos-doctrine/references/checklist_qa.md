## 15. Checklist QA zéro issue

### Front / UX

- [ ] Loading, empty, error, partial data et offline traités.
- [ ] Pas d'acronyme brut en titre.
- [ ] Source et date visibles pour les KPIs clés.
- [ ] Les filtres sont visibles, réinitialisables et actifs.
- [ ] Les graphes affichent unité, période, source et légende.
- [ ] Les actions mènent à une route réelle.
- [ ] Responsive validé mobile/tablette/desktop.
- [ ] Accessibilité clavier et contrastes validés.

### Back / API

- [ ] Validation server-side des inputs.
- [ ] Unités normalisées et conversions centralisées.
- [ ] Erreurs standardisées avec `code`, `message`, `hint`, `correlation_id`.
- [ ] Logs utiles sans données sensibles.
- [ ] Règles réglementaires versionnées.
- [ ] Endpoints documentés.
- [ ] Tests unitaires des calculs.
- [ ] Tests d'intégration des endpoints critiques.

### Data / métier

- [ ] Chaque KPI a définition, formule, source, unité, période, périmètre.
- [ ] Les valeurs sont cohérentes entre vues.
- [ ] Les données estimées ou partielles sont clairement indiquées.
- [ ] Les anomalies sont rattachées à un actif et une source.
- [ ] Les obligations conformité ont échéance, responsable, preuve et action.
- [ ] Les factures sont rattachées à compteur, contrat et période.

### Release

- [ ] Aucune route morte.
- [ ] Aucun bouton non fonctionnel.
- [ ] Aucun mock non signalé.
- [ ] Aucune régression KPI.
- [ ] Aucun écran sans état vide utile.
- [ ] Tests e2e sur parcours dirigeant, energy manager et admin data.

---

