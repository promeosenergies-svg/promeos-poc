# Phase 5 — Validation utilisateur kit (Sprint Refonte Narrative dynamique)

**Branche** : `claude/refonte-sol2`
**Date kit livré** : 2026-05-01
**Phase planning** : semaines 4-5 du sprint (post-déploiement Phases 1-4 en démo HELIOS)

---

## Objectif

Valider que la narrative dynamique livrée Phases 1-4 atteint **les 4 critères doctrine §11.3** en moins de 3 minutes de lecture, et ce **sur les 3 typologies** (Grand groupe / Commerce / ERP).

---

## Contenu du kit

| Fichier | Usage |
|---|---|
| [`recrutement_panel.md`](./recrutement_panel.md) | Profils ciblés + canaux de recrutement + budget |
| [`consent_form.md`](./consent_form.md) | Formulaire consentement RGPD (audio + verbatim) |
| [`script_session.md`](./script_session.md) | Déroulé chronométré 3 min + scripts neutres |
| [`questionnaire_post_test.md`](./questionnaire_post_test.md) | 12 questions post-session (5 min) |
| [`grille_evaluation.md`](./grille_evaluation.md) | Grille de cotation par typologie + critères de réussite |
| [`template_compte_rendu.md`](./template_compte_rendu.md) | Template `outputs/phase_5_user_tests.md` |

---

## Nature de l'étude — Phase 5.bis correction (mini-audit P0)

⚠️ **Test qualitatif exploratoire**, pas une étude statistique. n=2 par
typologie = échantillon trop faible pour des seuils en pourcentage type
"100 %" / "80 %". On parle ici de **convergence qualitative** : si les
2 panels d'une typologie donnent le même feedback structurant, c'est un
**signal fort à corriger**. Si 1 raté isolé, c'est un signal à investiguer
sans en faire un blocker statistique.

Pour un test quantitatif robuste (n=5 par typologie selon Nielsen), passer
à un sprint UX research dédié post-V1 (budget 1 500 € + 18 j/h).

## Critères de convergence qualitative (Phase 5.bis correction P0)

Reprend la doctrine §11.3 + l'audit triple Phase 3. Convergence requise
sur les **6/6 panels** pour C1-C3 (incompressible), bonus sur C4-C8.

1. **Lecture 3 min** : chaque panel identifie en 3 min au moins **4 critères
   sur 5** de la grille typologie (cf `grille_evaluation.md`).
2. **Vocabulaire juste** : chaque panel confirme verbalement que la
   narrative leur « parle » (registre métier ressenti comme adapté).
3. **Anti-paternalisme** : aucun panel n'utilise les mots « incompréhensible »,
   « abstrait », « trop technique », « infantilisant », « creux ».
4. **Sourçage perçu** (souhaitable) : majorité des panels notent que
   les chiffres sont sourcés (présence de « (source X) » remarquée).
5. **Action implicite** (souhaitable) : majorité des panels savent dire
   « la prochaine chose à faire » après lecture.
6. **Densité informationnelle** (audit vue exécutive 29/04) : aucun panel
   ne mentionne de chiffre incohérent, scope étranger ("retail-001" qui
   apparaît dans HELIOS), ou de surcharge KPI (>3 KPIs hero).

---

## Calendrier indicatif (à adapter)

| Semaine | Étape |
|---|---|
| W4 J1-J3 | Recrutement panel via canaux listés (LinkedIn pro, partenaires CCI, syndic ERP) |
| W4 J4-J5 | Validation profils + envoi consent forms + planification créneaux |
| W5 J1-J3 | 6 sessions chronométrées (1h chacune : 30 min entretien + 30 min retranscription) |
| W5 J4 | Synthèse compte-rendu + tri findings P0/P1/P2 |
| W5 J5 | Mini-sprint correctif si critère raté + re-test 1-2 panels rappelés |

---

## Budget

- **6 × 100 €** = 600 € compensation panels
- + ~ 10 j/h Amine ou délégué pour conduite sessions + retranscription
- + outil enregistrement audio sécurisé (Otter.ai / Riverside / Zoom local)

---

## Anti-patterns à éviter pendant les sessions

1. **Ne pas guider** : aucune intervention pendant les 3 min chronométrées
2. **Ne pas reformuler** la question post-test (« qu'est-ce que vous avez compris ») — laisser le silence faire parler
3. **Ne pas sur-recruter** dans son réseau direct (biais de complaisance) — privilégier des profils inconnus via canaux pro
4. **Ne pas tester la maquette HTML statique** (`docs/maquettes/narrative-sol2/narrative-*.html`) — tester l'instance live `claude/refonte-sol2` sur DB seedée HELIOS
5. **Ne pas mélanger les typologies sur une même session** — un panel = une typologie

Ref doctrine §11.3 lecture 3 min · Audit triple Phase 3 (Marie + Ergonomie + CX).
