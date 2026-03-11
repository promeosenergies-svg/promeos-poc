# SCRIPT DÉMO PROMEOS — Version officielle

**Durée cible : 6 minutes**
**Public : DG / Directeur immobilier / Responsable énergie — tertiaire multi-sites B2B France**
**Prérequis : Seed Helios actif, scope "Groupe HELIOS — 5 sites"**

---

## Étape 1 — Cockpit exécutif (1 min)

**Page :** `/cockpit`
**Objectif :** Montrer la vue décideur en un coup d'œil.

**Message :**
> « Voici votre cockpit énergie. En un écran, vous voyez la conformité de votre parc, le risque financier associé, la maturité de vos données et la couverture de votre périmètre. Ici, votre Groupe HELIOS : 5 sites, 46/100 en conformité, 23 k€ de risque identifié. »

**KPIs à montrer :**
- 4 tuiles exécutives (conformité, risque, maturité, couverture)
- Panel "Activation des données" : 5/5 briques activées
- Tableau des sites en bas avec code couleur conformité

**Piège à éviter :**
- Ne pas cliquer sur le toggle "Expert" (affiche des données techniques avancées)
- Ne pas scroller trop loin — rester sur la vue synthétique

---

## Étape 2 — Patrimoine multi-sites (1 min)

**Page :** `/patrimoine`
**Objectif :** Montrer la gestion multi-sites et la vision risque.

**Message :**
> « Votre patrimoine immobilier est centralisé. Chaque site a sa fiche, sa surface, son statut de conformité et son risque financier. Vous identifiez immédiatement les sites prioritaires. Par exemple, l'Usine HELIOS Toulouse est non conforme — c'est là qu'il faut agir en premier. »

**Éléments à montrer :**
- Heatmap risque en haut
- Tableau trié par risque décroissant
- Cliquer sur un site pour montrer la fiche rapide

**Piège à éviter :**
- Le subtitle montre "de risque (tous sites)" — c'est voulu, ne pas s'en excuser
- Ne pas entrer dans le drawer site, rester en vue portefeuille

---

## Étape 3 — Connecteurs et qualité des données (45 sec)

**Page :** `/connectors`
**Objectif :** Montrer que PROMEOS se connecte aux sources officielles.

**Message :**
> « PROMEOS s'interface avec les sources de données réglementaires et opérationnelles : RTE pour le mix électrique, Enedis pour les données réseau et Linky, PVGIS pour le solaire, Météo-France pour le contexte climatique. Les connecteurs publics sont actifs, les connecteurs authentifiés attendent vos clés API. »

**Éléments à montrer :**
- 5 cartes connecteurs avec labels métier
- Badges "Public" (vert) et "Auth requise" (orange)
- Section "À propos" en bas pour crédibilité

**Piège à éviter :**
- Ne PAS cliquer "Test" ou "Sync" (les connecteurs auth requise retourneront une erreur)
- Rester en lecture seule

---

## Étape 4 — Assistant Achat Énergie (1 min 15)

**Page :** `/achat/assistant`
**Objectif :** Montrer le moteur de scénarios d'achat.

**Message :**
> « L'assistant achat vous aide à construire vos scénarios de couverture. Vous sélectionnez vos sites, renseignez votre profil de consommation, définissez votre horizon et votre tolérance au risque, puis le moteur compare les offres et produit un scoring multicritère. C'est un outil d'aide à la décision, pas un simple comparateur. »

**Éléments à montrer :**
- Étape 1 : sélection du périmètre — 5 sites chargés
- Les 8 onglets du wizard (Portefeuille → Décision)
- Ne pas aller au-delà de l'étape 2

**Piège à éviter :**
- Ne pas cliquer "Suivant" au-delà de Portefeuille sans données de scénario
- Montrer l'ambition du parcours, pas le résultat vide

---

## Étape 5 — Facturation et intelligence billing (1 min 15)

**Page :** `/billing`
**Objectif :** Montrer la couverture factures et la détection d'anomalies.

**Message :**
> « Bill Intel analyse automatiquement vos factures énergie. Vous voyez la timeline de couverture mois par mois, les périodes manquantes, et la comparaison année sur année. Le moteur détecte les anomalies — surcharges, dérives réseau, écarts de taxes — et les classe par impact financier pour que vous traitiez les plus urgentes en priorité. »

**Éléments à montrer :**
- Barre de couverture verte en haut
- Graphique de comparaison mensuelle
- Liste des périodes manquantes
- Timeline complète avec statut "Couvert"

**Piège à éviter :**
- Ne pas ouvrir l'onglet "Anomalies & Audit" si le nombre d'insights est élevé — rester sur Timeline
- Le graphique compare l'année courante vs l'année précédente automatiquement

---

## Étape 6 — Notifications et priorisation (45 sec)

**Page :** `/notifications`
**Objectif :** Montrer le flux opérationnel quotidien.

**Message :**
> « Enfin, PROMEOS génère un flux de notifications priorisées : alertes de consommation, échéances factures, actions de conformité, déclarations à valider. Chaque alerte est rattachée à un site et classée par urgence. C'est votre fil d'activité quotidien pour ne rien laisser passer. »

**Éléments à montrer :**
- Compteur d'alertes (nouvelles vs lues)
- Filtres par type (Toutes, Nouvelles, Lues, Ignorées)
- Liste avec icônes typées et sites rattachés

**Piège à éviter :**
- Ne pas cliquer sur une notification individuelle (le détail peut être incomplet)
- Rester en vue liste

---

## Conclusion (15 sec)

**Message :**
> « En résumé, PROMEOS vous donne la visibilité complète sur votre patrimoine énergie : conformité, facturation, consommation, achat. Le tout dans une plateforme unique, connectée aux sources officielles, avec de l'intelligence intégrée. Souhaitez-vous approfondir un module en particulier ? »

---

## Notes techniques pour le démonstrateur

- **Login :** promeos@promeos.io / promeos2024
- **Scope :** Groupe HELIOS — 5 sites (sélection automatique après seed)
- **Backend :** `cd backend && python main.py` → http://localhost:8001
- **Frontend :** `cd frontend && npm run dev` → http://localhost:5173
- **Re-seed si besoin :** `cd backend && python -m services.demo_seed --pack helios --size S --reset`
- **Ordre des pages :** Cockpit → Patrimoine → Connecteurs → Assistant Achat → Billing → Notifications
- **Durée totale :** 5 min 45 sec (marge 15 sec pour transitions)
