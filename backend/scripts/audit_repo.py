"""Audit the PROMEOS POC repository structure."""
import os
import json
import sqlite3
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent  # backend/
PROJ = ROOT.parent  # promeos-poc/

def count_py(directory):
    """Count .py files excluding venv/__pycache__."""
    count = 0
    loc = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'venv', '.pytest_cache', 'node_modules')]
        for f in files:
            if f.endswith('.py'):
                count += 1
                try:
                    with open(os.path.join(root, f), encoding='utf-8', errors='ignore') as fh:
                        loc += sum(1 for line in fh if line.strip())
                except Exception:
                    pass
    return count, loc


def count_files(directory, ext):
    """Count files with extension."""
    count = 0
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ('__pycache__', 'venv', '.pytest_cache', 'node_modules')]
        for f in files:
            if f.endswith(ext):
                count += 1
    return count


print("=" * 70)
print("PROMEOS POC - AUDIT COMPLET")
print("=" * 70)

# 1. Backend modules
print("\n## BACKEND MODULES (Python)")
modules = ['app', 'ai_layer', 'connectors', 'database', 'jobs', 'models', 'regops', 'routes', 'services', 'utils', 'watchers', 'scripts', 'tests']
for mod in modules:
    modpath = ROOT / mod
    if modpath.exists():
        files, loc = count_py(modpath)
        print(f"  {mod:20s} -> {files:3d} files, {loc:5d} LOC")

# App submodules
print("\n  app/ submodules:")
app_dir = ROOT / 'app'
if app_dir.exists():
    for sub in sorted(app_dir.iterdir()):
        if sub.is_dir() and sub.name != '__pycache__':
            files, loc = count_py(sub)
            print(f"    app/{sub.name:20s} -> {files:3d} files, {loc:5d} LOC")

# 2. Frontend
print("\n## FRONTEND")
fe = PROJ / 'frontend' / 'src'
if fe.exists():
    jsx_count = count_files(fe, '.jsx')
    tsx_count = count_files(fe, '.tsx')
    js_count = count_files(fe, '.js')
    css_count = count_files(fe, '.css')
    print(f"  JSX: {jsx_count}, TSX: {tsx_count}, JS: {js_count}, CSS: {css_count}")
    # Pages
    pages_dir = fe / 'pages'
    if pages_dir.exists():
        pages = [f.name for f in pages_dir.iterdir() if f.suffix in ('.jsx', '.tsx')]
        print(f"  Pages: {pages}")
    components_dir = fe / 'components'
    if components_dir.exists():
        comps = [f.name for f in components_dir.iterdir() if f.suffix in ('.jsx', '.tsx')]
        print(f"  Components ({len(comps)}): {comps[:10]}{'...' if len(comps) > 10 else ''}")

# 3. Data
print("\n## DATA FILES")
data_dir = ROOT / 'data'
if data_dir.exists():
    for item in sorted(data_dir.iterdir()):
        if item.is_file():
            size = item.stat().st_size
            print(f"  {item.name:40s} {size:>10,d} bytes")
        elif item.is_dir():
            fcount = sum(1 for _ in item.rglob('*') if _.is_file())
            print(f"  {item.name + '/':40s} {fcount:>5d} files")

# Demo invoices
demo_dir = data_dir / 'invoices' / 'demo'
if demo_dir.exists():
    demo_files = list(demo_dir.glob('*.json'))
    print(f"\n  Demo invoices: {len(demo_files)} JSON files")

# 4. KB
kb_db = data_dir / 'kb.db'
if kb_db.exists():
    conn = sqlite3.connect(str(kb_db))
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"\n  KB database tables: {[t[0] for t in tables]}")
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
        print(f"    {t[0]:30s} -> {count:5d} rows")
    conn.close()

# Main DB
main_db = data_dir / 'promeos.db'
if main_db.exists():
    conn = sqlite3.connect(str(main_db))
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"\n  Main database tables ({len(tables)}):")
    for t in tables:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM [{t[0]}]").fetchone()[0]
            print(f"    {t[0]:30s} -> {count:5d} rows")
        except Exception:
            print(f"    {t[0]:30s} -> (error reading)")
    conn.close()

# 5. Referential snapshots
snap_dir = data_dir / 'referential' / 'snapshots'
if snap_dir.exists():
    snaps = list(snap_dir.rglob('*.*'))
    print(f"\n  Referential snapshots: {len(snaps)} files")

# 6. Tests
print("\n## TESTS")
test_dir = ROOT / 'tests'
if test_dir.exists():
    test_files = list(test_dir.glob('test_*.py'))
    print(f"  Test files: {len(test_files)}")
    for tf in sorted(test_files):
        # Count test functions
        with open(tf, encoding='utf-8') as f:
            content = f.read()
        test_count = content.count('def test_')
        print(f"    {tf.name:45s} -> {test_count:3d} tests")

# 7. API Routes
print("\n## API ROUTES")
routers_found = []
for root, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ('__pycache__', 'venv', '.pytest_cache')]
    for f in files:
        if f.endswith('.py'):
            fpath = os.path.join(root, f)
            try:
                with open(fpath, encoding='utf-8') as fh:
                    content = fh.read()
                if 'APIRouter' in content or '@router.' in content or '@app.' in content:
                    endpoints = content.count('@router.') + content.count('@app.')
                    rel = os.path.relpath(fpath, ROOT)
                    if endpoints > 0:
                        routers_found.append((rel, endpoints))
            except Exception:
                pass

for r, e in sorted(routers_found):
    print(f"  {r:50s} -> {e:3d} endpoints")

# 8. YAML configs
print("\n## YAML/CONFIG FILES")
for yaml in PROJ.rglob('*.yaml'):
    if 'node_modules' not in str(yaml) and 'venv' not in str(yaml):
        rel = os.path.relpath(yaml, PROJ)
        print(f"  {rel}")
for yaml in PROJ.rglob('*.yml'):
    if 'node_modules' not in str(yaml) and 'venv' not in str(yaml):
        rel = os.path.relpath(yaml, PROJ)
        print(f"  {rel}")

# 9. Docs
print("\n## DOCUMENTATION")
docs_dir = PROJ / 'docs'
if docs_dir.exists():
    for md in sorted(docs_dir.rglob('*.md')):
        rel = os.path.relpath(md, PROJ)
        size = md.stat().st_size
        print(f"  {rel:50s} {size:>6,d} bytes")

# README
readme = PROJ / 'README.md'
if readme.exists():
    print(f"  {'README.md':50s} {readme.stat().st_size:>6,d} bytes")

# 10. Dependencies
print("\n## DEPENDENCIES")
req = ROOT / 'requirements.txt'
if req.exists():
    with open(req) as f:
        deps = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    print(f"  requirements.txt: {len(deps)} packages")
    for d in deps:
        print(f"    {d}")

pkg = PROJ / 'package.json'
if pkg.exists():
    with open(pkg) as f:
        pj = json.load(f)
    deps_count = len(pj.get('dependencies', {})) + len(pj.get('devDependencies', {}))
    print(f"  package.json: {deps_count} packages (frontend)")

# Summary
print("\n" + "=" * 70)
total_py_files, total_py_loc = count_py(ROOT)
fe_root = PROJ / 'frontend'
total_jsx = count_files(fe_root, '.jsx') + count_files(fe_root, '.tsx') if fe_root.exists() else 0
print(f"TOTAL: {total_py_files} Python files, {total_py_loc} LOC Python, {total_jsx} JSX/TSX")
print(f"Test files: {len(test_files)}, Total test functions: {sum(1 for tf in test_files for line in open(tf, encoding='utf-8') if 'def test_' in line)}")
print("=" * 70)
