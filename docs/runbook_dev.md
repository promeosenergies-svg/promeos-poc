# PROMEOS - Runbook Developpeur

**Date**: 2026-02-11

---

## 1. Prerequis

| Outil | Version | Verifier |
|-------|---------|----------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Git | 2.x | `git --version` |
| OS | Windows 10/11 | Teste sur Windows 10 Pro |

---

## 2. Premier lancement (setup complet)

```bash
# Cloner
git clone https://github.com/promeosenergies-svg/promeos-poc.git
cd promeos-poc/promeos-poc

# Backend
cd backend
python -m venv venv

# Activer le venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Windows CMD:
venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate

# Installer les deps
pip install -r requirements.txt

# Initialiser la DB + seed 120 sites
python scripts/init_database.py
python scripts/seed_data.py

# Lancer le backend (port 8000)
python main.py
```

```bash
# Frontend (nouveau terminal)
cd frontend
npm install
npm run dev
# -> http://localhost:5173
```

---

## 3. Lancement quotidien

```bash
# Terminal 1 - Backend
cd backend
.\venv\Scripts\Activate.ps1    # ou source venv/bin/activate
python main.py
# -> http://localhost:8000/docs (Swagger)
# -> http://localhost:8000/health (health check)

# Terminal 2 - Frontend
cd frontend
npm run dev
# -> http://localhost:5173
```

---

## 4. Tests

```bash
# Depuis backend/
cd backend

# Tous les tests (427 attendus)
.\venv\Scripts\pytest.exe tests/ -v

# Tests rapides (sans -v)
.\venv\Scripts\pytest.exe tests/

# Un fichier specifique
.\venv\Scripts\pytest.exe tests/test_alert_engine.py -v

# Un test specifique
.\venv\Scripts\pytest.exe tests/test_kpi_engine.py::TestWeekendRatio -v

# Avec couverture (si pytest-cov installe)
.\venv\Scripts\pytest.exe tests/ --cov=. --cov-report=term-missing
```

---

## 5. Build frontend

```bash
cd frontend

# Build production
npx vite build
# -> dist/ genere

# Verifier le build (pas d'erreur)
# Fichiers attendus: dist/index.html, dist/assets/index-*.js, dist/assets/index-*.css
```

---

## 6. Seeds & donnees de demo

```bash
cd backend

# Reset complet DB + seed 120 sites
python scripts/seed_data.py

# Seed Knowledge Base
python scripts/kb_seed_import.py

# Generer donnees monitoring (2 sites, 90 jours)
python scripts/generate_monitoring_demo.py

# Generer corpus factures 24 mois
python scripts/generate_demo_corpus_24m.py

# Valider la KB
python scripts/kb_validate.py --strict

# Smoke test KB (14 checks)
python scripts/kb_smoke.py
```

---

## 7. Onboarding (creation patrimoine reel)

```bash
# Via API (curl ou Swagger http://localhost:8000/docs)
# 1. Creer org + sites
curl -X POST http://localhost:8000/api/onboarding \
  -H "Content-Type: application/json" \
  -d '{"organisation":{"nom":"Ma Societe","siren":"123456789","type_client":"bureau"},"sites":[{"nom":"Bureau Paris","type":"bureau","surface_m2":2000}]}'

# 2. Import CSV
curl -X POST http://localhost:8000/api/onboarding/import-csv \
  -F "file=@mes_sites.csv"

# 3. Verifier l'etat
curl http://localhost:8000/api/onboarding/status

# Format CSV attendu (separateur , ou ;):
# nom,adresse,code_postal,ville,surface_m2,type,naf_code
# Bureau Paris,10 rue de la Paix,75002,Paris,1200,bureau,
# Hotel Nice,Promenade,06000,Nice,800,,55.10Z
```

---

## 8. Fichiers cles

| Fichier | Role |
|---------|------|
| `backend/main.py` | Point d'entree FastAPI, enregistrement des 18 routers |
| `backend/models/__init__.py` | Exports de tous les modeles SQLAlchemy |
| `backend/database/connection.py` | Session SQLite, `get_db()` dependency |
| `backend/routes/__init__.py` | Exports de tous les routers |
| `backend/data/promeos.db` | Base de donnees principale |
| `backend/data/kb.db` | Knowledge Base (FTS5) |
| `frontend/src/App.jsx` | Routing React (9 pages) |
| `frontend/vite.config.js` | Config Vite + proxy API |

---

## 9. Conventions

- **Commits**: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`
- **Python**: black pour le formatage (pas encore enforce)
- **Tests**: un fichier `test_*.py` par module, classes `Test*`, methodes `test_*`
- **API**: prefixe `/api/`, tags par domaine, Pydantic pour validation
- **Frontend**: 1 page = 1 fichier JSX dans `src/pages/`, Tailwind pour le style

---

## 10. Troubleshooting

| Probleme | Solution |
|----------|----------|
| `ModuleNotFoundError` | Activer le venv: `.\venv\Scripts\Activate.ps1` |
| Port 8000 occupe | `netstat -ano \| findstr :8000` puis `taskkill /PID <PID> /F` |
| Frontend erreurs API | Verifier que backend tourne sur :8000 |
| DB vide | `python scripts/seed_data.py` |
| `node_modules` corrompus | `rm -rf node_modules && npm install` |
| PowerShell bloque scripts | `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` |
