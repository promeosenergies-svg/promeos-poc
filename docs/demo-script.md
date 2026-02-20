# PROMEOS — Script demo (3 minutes)

## Prerequis

- Backend sur localhost:8000
- Frontend sur localhost:5173
- Donnees demo seedees (login : sophie@atlas.demo / demo2024)

---

## Scene 1 : Cockpit — Vue executive (60s)

**URL** : `/cockpit`

**Points cles** :

1. "Voici le cockpit executif PROMEOS. En un coup d'oeil, le decideur voit
   l'etat de son patrimoine immobilier."
2. Montrer le **Resume executif** : "Le briefing du jour resume les alertes
   prioritaires et les actions recommandees."
3. Montrer les **4 tuiles KPIs** : couverture donnees, suivi conformite,
   actions actives, maturite de pilotage.
4. Montrer la **table des sites** en bas : "Tous les sites avec tri,
   recherche et filtres. On peut cliquer pour aller au detail."
5. Montrer le **bandeau risque** (si present) : "X sites non conformes,
   risque estime Yk€. Un bouton mene directement au plan d'action."

**Transition** : "Passons a la vue Patrimoine pour voir le parc complet."

---

## Scene 2 : Patrimoine — Command Center (60s)

**URL** : `/patrimoine`

**Points cles** :

1. "La vue Patrimoine est le centre de commande du parc immobilier."
2. Montrer les **4 KPIs interactifs** : cliquer sur "Non conformes" pour
   filtrer instantanement le tableau.
3. Montrer la **toolbar** : recherche en temps reel, filtres par usage et
   statut, vues predefinies (Risque Top, Non conformes, A evaluer).
4. **Demontrer** : cliquer sur une ligne pour ouvrir le **tiroir lateral**.
5. "Le tiroir donne un resume rapide avec 4 onglets : resume, anomalies,
   compteurs, actions."
6. Cliquer sur **"Voir la fiche site"** dans le tiroir.

**Transition** : "Plongeons dans le detail d'un site."

---

## Scene 3 : Site 360 — Fiche site detaillee (60s)

**URL** : `/sites/:id`

**Points cles** :

1. "La fiche Site 360 donne une vue complete du site."
2. Montrer le **header** : nom, statut de conformite (badge colore), usage,
   adresse, surface.
3. Montrer les **3 mini KPIs** : consommation annuelle, risque financier
   en euros, nombre d'anomalies.
4. **Onglet Resume** : indicateurs cles, recommandation principale,
   anomalies detectees avec severite et impact financier.
5. Cliquer sur l'**onglet Conformite** : "Le moteur reglementaire (KB)
   s'execute en temps reel. Il identifie les obligations applicables
   selon la surface, l'usage et le type de batiment."
6. Montrer les **obligations** : classees par severite avec sources
   reglementaires et echeances.

**Conclusion** : "En trois clics — Cockpit, Patrimoine, Site 360 — le
decideur passe de la vision globale au detail actionnable d'un site."

---

## Donnees demo recommandees

- **Organisation** : celle seedee via le pack demo
- **Login** : sophie@atlas.demo / demo2024
- Chercher un site avec statut `non_conforme` pour le demo le plus impactant
- L'onglet Conformite fait un vrai appel API au moteur KB

## Depannage

| Symptome | Cause probable | Solution |
|----------|---------------|----------|
| Site360 affiche "Site introuvable" | Scope pas encore charge | Attendre la fin du skeleton loading |
| Onglet Conformite affiche "Analyse indisponible" | Backend eteint | Verifier localhost:8000/api/health |
| Patrimoine vide | Pas de donnees seedees | Lancer le seed via DemoBanner |
| KPIs a zero dans Cockpit | Mauvaise org selectionnee | Verifier le scope dans le selecteur d'org |
