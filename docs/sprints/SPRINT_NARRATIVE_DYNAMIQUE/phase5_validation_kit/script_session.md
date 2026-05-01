# Script de session — Test UX 3 min Phase 5

**Durée totale** : 45 min
**Format** : visioconférence (animateur + participant + observateur silencieux optionnel)
**Outils** : Zoom/Meet pour audio + capture écran de la page testée + chronomètre visible

---

## 0 — Avant la session (T-15 min, animateur seul)

- [ ] Ouvrir l'instance démo `claude/refonte-sol2` sur port 5175
- [ ] Login démo selon typologie testée :
  - Grand groupe → `marie@helios.demo` (DAF)
  - Commerce → `herve@boulangerie.demo` (NAF 4724Z)
  - ERP → `anne@ecole.demo` (directrice école primaire)
- [ ] Naviguer sur **Cockpit / Synthèse stratégique**
- [ ] Vérifier que la narrative dynamique est bien rendue :
  - Phrase 1 événementielle visible
  - Push +X vs S-1 en chip stylé (si données disponibles)
  - Mention persona italique sous le narrative
  - Drill-down "Voir les sites en dérive" cliquable
- [ ] Préparer le chronomètre (timer.live ou similaire — rendre visible à l'écran)

---

## 1 — Accueil (3 min)

> *« Bonjour {prénom}, merci d'être là. Comme convenu, on va faire un exercice en 3 phases : (1) je vais vous montrer une page web pendant 3 minutes — vous la lisez librement, je n'interviens pas ; (2) je vais vous poser une question à la fin pour comprendre ce que vous avez compris ; (3) on terminera par un mini questionnaire de 5 minutes.*
>
> *Tout ce que vous direz est anonymisé. L'enregistrement reste interne. Vous pouvez à tout moment dire "stop" ou refuser une question.*
>
> *Une dernière chose : il n'y a pas de bonne ou mauvaise réponse. C'est l'outil qu'on teste, pas vous. Donc soyez francs, c'est précieux pour nous.*
>
> *Prêt·e ? »*

---

## 2 — Présentation page (30 sec — neutre absolu)

> *« Je vais maintenant partager mon écran. Vous allez voir une page web qui s'appelle "Synthèse stratégique" — c'est un outil de pilotage énergie pour les {typologie}. Je vais lancer un chronomètre de 3 minutes. Lisez à votre rythme, comme si vous étiez seul·e devant votre écran. Je ne dirai rien pendant ces 3 minutes. »*

**Partage écran** : navigateur en plein écran, page Synthèse stratégique.
**Démarrer chronomètre** : 3 min visible.

⚠️ **Pendant les 3 min : silence absolu de l'animateur.** Ne répondre à aucune question (« on revient sur ça après »).

---

## 3 — Question ouverte libre (3-5 min — verbatim brut)

À la fin du timer :

> *« Stop. Racontez-moi librement ce que vous avez retenu de cette page. Prenez le temps qu'il vous faut. »*

**Phase 5.bis correction (mini-audit P0)** : pas de chronomètre sur cette
réponse — chronométrer 30 sec biaise le cadrage et favorise la complaisance
superficielle ("c'était bien"). Laisser le participant organiser sa pensée
spontanément.

⚠️ **Ne pas reformuler** la question initiale. Laisser le silence si
nécessaire (15-20 sec OK).

**Relances neutres autorisées** quand le participant marque une pause
visible :

- *« Et quoi d'autre ? »*
- *« Autre chose qui vous a marqué ? »*
- *« Autre chose qui vous a moins parlé ? »*

⚠️ **JAMAIS** :

- ❌ « Vous voulez dire que … ? » (reformulation = biais)
- ❌ « C'est intéressant ce que vous dites » (acquiescement = biais)
- ❌ « Mais vous avez vu le … ? » (guidage)

Continuer les relances neutres jusqu'à épuisement spontané (généralement
2-5 min selon profil).

**Animateur** : prendre note du **verbatim brut** (mot pour mot). Pas de
résumé. Pas d'interprétation.

---

## 4 — Approfondissement guidé (15 min — questions ciblées)

5 questions ouvertes, **dans cet ordre**. Une seule question à la fois. Laisser le silence après chaque question.

### Q1 — Vocabulaire
> *« Y a-t-il un mot ou une expression dans cette page qui vous a fait tiquer ? Soit parce que vous ne le comprenez pas, soit parce que ça sonne faux pour votre métier ? »*

→ **Cible audit** : §6 anti-paternalisme + jargon CFO chez Commerce/ERP

### Q2 — Chiffres et sources
> *« Quand vous voyez un chiffre dans la narrative — par exemple "3 sites en dérive" — est-ce que vous savez d'où vient ce chiffre ? Est-ce que vous lui faites confiance ? »*

→ **Cible audit** : §7 sourçage explicite

### Q3 — Action implicite
> *« Si vous deviez agir cette semaine sur la base de ce que vous venez de lire, quelle serait votre première action ? »*

→ **Cible** : la narrative pousse-t-elle à l'arbitrage ?

### Q4 — Push événementiel
> *« Vous avez vu un petit chip "+18 % vs semaine précédente" à côté du titre ? Qu'est-ce que ça vous dit ? Est-ce que ça change votre lecture de la page ? »*

→ **Cible** : visibilité du push styled (Phase 4.bis B)

### Q5 — Drill-down
> *« Sous la narrative, il y a un lien "Voir les sites en dérive". Vous l'aviez remarqué ? Est-ce que vous auriez cliqué ? »*

→ **Cible** : drill-down cliquable (Phase 4.bis C)

---

## 5 — Questionnaire post-test (5 min)

Ouvrir le fichier `questionnaire_post_test.md` et lire les 12 questions à voix haute. Réponses cochées par l'animateur sous la dictée du participant.

---

## 6 — Clôture (2 min)

> *« On a terminé. Merci beaucoup pour votre temps. Vous recevrez la compensation par {méthode choisie} sous 7 jours.*
>
> *Avez-vous une dernière chose à dire qui vous a marqué et que je n'ai pas demandée ? »*

→ Note libre verbatim (parfois la meilleure info sort là).

> *« Parfait. Je vous remercie encore. Bonne journée ! »*

---

## Post-session (30 min, animateur seul)

- [ ] Sauvegarder l'enregistrement audio (nom : `phase5_session_{numero}_{typologie}_{date}.mp4`)
- [ ] Retranscrire le verbatim Q1-Q5 + Q ouverte initiale dans `template_compte_rendu.md`
- [ ] Cocher les critères de la grille (`grille_evaluation.md`)
- [ ] Anonymiser : remplacer prénom + raison sociale par `[Participant N]` + `[Organisation typologie X]`
- [ ] Détruire l'audio source si > 30 jours (hors fichiers consentis citation publique)

---

## Anti-patterns animateur (à se rappeler)

- ❌ Reformuler les questions
- ❌ Acquiescer (« oui exactement », « bonne idée ») — biais d'approbation
- ❌ Sourire à des réponses positives, faire la moue à des réponses négatives
- ❌ Combler les silences (laisser parler)
- ❌ Aider à trouver le mot juste (« vous voulez dire X ? »)
- ❌ Justifier le design choisi (« c'est parce que… »)

---

*Total estimé : 45 min participant + 30 min retranscription animateur = 1h15 par session.*
