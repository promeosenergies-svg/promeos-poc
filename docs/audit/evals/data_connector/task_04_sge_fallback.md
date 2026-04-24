# Task 04 — Fallback SGE SOAP en cas d'erreur réseau

**Agent cible** : `data-connector`
**Difficulté** : medium
**Sprint origin** : Enedis SGE

## Prompt exact

> Appel SGE SOAP `ConsultationMesures` retourne erreur 503 puis timeout. Pattern fallback robuste sans perdre requête ?

## Golden output (PASS)

- [ ] Retry exponentiel (max 3 tentatives)
- [ ] Queue messages pour retry différé si erreurs persistantes
- [ ] Alert opérationnel si queue > seuil
- [ ] Timeout configuré (pas de hang)
- [ ] Délègue à `architect-helios` si pattern récurrent nécessite refacto circuit-breaker

## Anti-patterns (FAIL)

- ❌ Retry infini
- ❌ Perte silencieuse de requêtes
- ❌ Timeout default OS

## Rationale

Résilience connecteur critique. SGE souvent instable, pattern récurrent.
