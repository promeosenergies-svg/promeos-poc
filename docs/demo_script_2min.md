# PROMEOS IAM — Demo Script 2 minutes (Sprint 12)

## Prerequis

```bash
# Terminal 1 — Backend
cd backend
py -3.14 -m uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Ouvrir http://localhost:5173

---

## Scene 1 : Login Owner (30s)

1. Ouvrir `/login` — formulaire email + mot de passe
2. Se connecter :
   - **Email** : `sophie@atlas.demo`
   - **Password** : `demo2024`
3. Redirect vers `/` — Dashboard complet
4. Header : **Sophie Durand** - DG/Owner - Groupe Atlas
5. Sidebar : **toutes les sections** visibles (Cockpit, Patrimoine, Conformite, Achats, Actions, Monitoring, Admin)

---

## Scene 2 : Switch persona — Scope restreint (30s)

6. Logout (menu utilisateur en haut a droite)
7. Login **Pierre Garcia** :
   - **Email** : `pierre@atlas.demo`
   - **Password** : `demo2024`
   - **Role** : Responsable de Site — scope = Tour Atlas uniquement
8. Dashboard : uniquement les KPIs du site **Tour Atlas**
9. Sidebar : sections Admin **masquees**, seules Patrimoine / Conso / Conformite / Actions visibles
10. Naviguer vers un autre site → **403 Acces refuse**

---

## Scene 3 : Preuve 403 — Zero fuite de scope (30s)

11. Toujours connecte en tant que Pierre Garcia
12. Ouvrir les DevTools (F12 → Network)
13. Tenter d'acceder a `/api/sites/999` (site hors scope) → **403 Forbidden**
14. Tenter `/api/actions/export.csv` → seules les actions du site Tour Atlas apparaissent
15. Tenter `/api/admin/users` → **403 Permission denied**
16. Tenter `/api/purchase/estimate/<autre_site>` → **403 Site not in your scope**

---

## Scene 4 : Admin + Audit Log (30s)

17. Logout → Login **Marc Leroy** :
    - **Email** : `marc@atlas.demo`
    - **Password** : `demo2024`
    - **Role** : DSI/Admin — acces complet
18. Naviguer vers `/admin/users`
    - Table des 10 utilisateurs avec roles et scopes
    - Barre de recherche pour filtrer par nom/email/role
    - Cliquer sur l'oeil de Pierre Garcia → panneau **Acces Effectif** :
      - Sites resolus (1 site), scopes affiches (S:42)
      - Permissions du role resp_site
    - Modifier son scope : ajouter un 2e site → audit log enregistre
19. Naviguer vers `/admin/audit`
    - Timeline des evenements avec labels francais
    - Recherche par texte libre
    - Cliquer sur un evenement → **panneau detail JSON** (before/after)

---

## Personas Demo

| # | Prenom Nom     | Email               | Role             | Scope                     | Password |
|---|----------------|---------------------|------------------|---------------------------|----------|
| 1 | Sophie Durand  | sophie@atlas.demo   | DG/Owner         | ORG (tout)                | demo2024 |
| 2 | Marc Leroy     | marc@atlas.demo     | DSI/Admin        | ORG (tout)                | demo2024 |
| 3 | Claire Martin  | claire@atlas.demo   | DAF              | ORG (tout)                | demo2024 |
| 4 | Thomas Petit   | thomas@atlas.demo   | Acheteur         | ORG (tout)                | demo2024 |
| 5 | Nadia Benali   | nadia@atlas.demo    | Resp. Conformite | ORG (tout)                | demo2024 |
| 6 | Lucas Moreau   | lucas@atlas.demo    | Energy Manager   | ORG (tout)                | demo2024 |
| 7 | Julie Lambert  | julie@atlas.demo    | Resp. Immobilier | ENTITE Atlas IDF          | demo2024 |
| 8 | Pierre Garcia  | pierre@atlas.demo   | Resp. Site       | SITE Tour Atlas           | demo2024 |
| 9 | Karim Diallo   | karim@atlas.demo    | Prestataire      | SITE Tour Atlas + DC (J+90) | demo2024 |
|10 | Emma Roux      | emma@atlas.demo     | Auditeur         | ORG (lecture seule)       | demo2024 |

---

## Points cles a montrer

- **Multi-role** : chaque persona voit un perimetre different
- **Deny-by-default** : pas de scope = pas d'acces
- **Server-side** : le filtrage est fait cote serveur, pas juste UI (prouver via DevTools)
- **Zero fuite** : exports, details, listes — tout est filtre par `iam_scope.py`
- **Audit trail** : chaque action est tracee (login, scope_change, impersonate) avec detail JSON
- **Demo mode** : sans token, le systeme reste fonctionnel (backward compatible)
- **DEMO_MODE lockdown** : si `PROMEOS_DEMO_MODE=false`, tout endpoint requiert JWT
