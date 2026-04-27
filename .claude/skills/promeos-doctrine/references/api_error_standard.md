### 12.2 Standard d'erreur API

```json
{
  "code": "DATA_QUALITY_INCOMPLETE_PERIOD",
  "message": "La consommation annuelle ne couvre pas une période complète.",
  "hint": "Importez les données manquantes de janvier à mars ou affichez ce KPI en statut partiel.",
  "correlation_id": "req_01HX...",
  "scope": {
    "site_id": "site_123",
    "meter_id": "meter_456"
  }
}
```

### 12.3 Interdits backend / frontend

Interdit :

- calcul KPI dans le frontend ;
- logique réglementaire dans le frontend ;
- conversion d'unités dispersée ;
- fallback silencieux ;
- mock non marqué ;
- endpoint différent pour la même mesure ;
- comparaison de données non alignées en période ;
- règles réglementaires non versionnées ;
- logs contenant des données sensibles.

---

