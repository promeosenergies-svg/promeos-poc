"""
PROMEOS Seed Coverage Audit — Phase 0
Vérifie que le seed HELIOS alimente correctement les 28 modules.
Mode : DB-only (pas besoin de serveur HTTP).
Usage : cd backend && python scripts/audit_seed_coverage.py
"""

import sqlite3
import json
import os
import sys
from datetime import datetime

# Force UTF-8 on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "promeos.db")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "..", "SEED_AUDIT_REPORT.md")


def connect():
    path = os.path.abspath(DB_PATH)
    if not os.path.exists(path):
        print(f"❌ DB not found: {path}")
        sys.exit(1)
    return sqlite3.connect(path)


def count(conn, table):
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM [{table}]")
        return cur.fetchone()[0]
    except Exception:
        return -1  # table does not exist


def count_where(conn, table, col, value):
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM [{table}] WHERE [{col}] = ?", (value,))
        return cur.fetchone()[0]
    except Exception:
        return -1


def distinct_values(conn, table, col):
    try:
        cur = conn.execute(f"SELECT DISTINCT [{col}] FROM [{table}]")
        return [r[0] for r in cur.fetchall()]
    except Exception:
        return []


def query_one(conn, sql):
    try:
        cur = conn.execute(sql)
        return cur.fetchone()
    except Exception:
        return None


# ─── Module checks ──────────────────────────────────────────────────────────


def check_patrimoine(conn):
    sites = count(conn, "sites")
    batiments = count(conn, "batiments")
    compteurs = count(conn, "compteurs")
    meters = count(conn, "meter")
    dp = count(conn, "delivery_points")
    return {
        "status": "✅" if sites >= 5 and meters > 0 else "❌",
        "detail": f"sites={sites} batiments={batiments} compteurs={compteurs} meters={meters} delivery_points={dp}",
        "sites": sites,
    }


def check_consommation(conn):
    readings = count(conn, "meter_reading")
    # Check multiple frequencies
    freqs = distinct_values(conn, "meter_reading", "frequency")
    return {
        "status": "✅" if readings > 0 and len(freqs) >= 3 else "⚠️" if readings > 0 else "❌",
        "detail": f"meter_readings={readings} frequencies={freqs}",
    }


def check_puissance(conn):
    pr = count(conn, "power_readings")
    pc = count(conn, "power_contracts")
    return {
        "status": "✅" if pr > 0 and pc > 0 else "❌",
        "detail": f"power_readings={pr} power_contracts={pc}",
        "power_readings": pr,
        "power_contracts": pc,
    }


def check_facturation(conn):
    invoices = count(conn, "energy_invoices")
    lines = count(conn, "energy_invoice_lines")
    insights = count(conn, "billing_insights")
    contracts = count(conn, "energy_contracts")
    # Check sites covered
    r = query_one(conn, "SELECT COUNT(DISTINCT site_id) FROM energy_invoices")
    sites_covered = r[0] if r else 0
    return {
        "status": "✅" if invoices > 0 and sites_covered >= 5 else "⚠️" if invoices > 0 else "❌",
        "detail": f"invoices={invoices} lines={lines} insights={insights} contracts={contracts} sites_covered={sites_covered}",
    }


def check_contrats_v2(conn):
    cadres = count(conn, "contract_cadres")
    if cadres == -1:
        cadres = count(conn, "energy_contracts")
    annexes = count(conn, "contract_annexes")
    pricing = count(conn, "contract_pricing")
    events = count(conn, "contract_events")
    return {
        "status": "✅" if annexes >= 4 else "⚠️" if annexes > 0 else "❌",
        "detail": f"annexes={annexes} pricing={pricing} events={events}",
    }


def check_shadow_billing(conn):
    insights = count(conn, "billing_insights")
    statuses = distinct_values(conn, "billing_insights", "insight_status")
    return {
        "status": "✅" if insights >= 10 and len(statuses) >= 3 else "⚠️" if insights > 0 else "❌",
        "detail": f"billing_insights={insights} statuses={statuses}",
    }


def check_conformite_dt(conn):
    efas = count(conn, "tertiaire_efa")
    buildings = count(conn, "tertiaire_efa_building")
    consumption = count(conn, "tertiaire_efa_consumption")
    targets = count(conn, "consumption_targets")
    return {
        "status": "✅" if efas > 0 and consumption > 0 and targets > 0 else "❌",
        "detail": f"efas={efas} efa_buildings={buildings} efa_consumption={consumption} targets={targets}",
    }


def check_bacs(conn):
    assets = count(conn, "bacs_assets")
    systems = count(conn, "bacs_cvc_systems")
    assessments = count(conn, "bacs_assessments")
    inspections = count(conn, "bacs_inspections")
    return {
        "status": "✅" if assets > 0 and assessments > 0 else "❌",
        "detail": f"assets={assets} systems={systems} assessments={assessments} inspections={inspections}",
    }


def check_aper(conn):
    # APER seuils: parking >= 1500 m², roof >= 500 m²
    r = query_one(
        conn,
        """
        SELECT COUNT(*) FROM sites
        WHERE (parking_area_m2 IS NOT NULL AND parking_area_m2 >= 1500)
           OR (roof_area_m2 IS NOT NULL AND roof_area_m2 >= 500)
    """,
    )
    eligible = r[0] if r else 0
    if eligible == -1:
        reg = count(conn, "reg_assessments")
        return {
            "status": "⚠️" if reg > 0 else "❌",
            "detail": f"reg_assessments={reg} (APER columns may not exist on sites)",
        }
    return {
        "status": "✅" if eligible >= 3 else "⚠️" if eligible > 0 else "❌",
        "detail": f"sites_eligible_aper={eligible} (parking>=1500 ou roof>=500)",
    }


def check_audit_sme(conn):
    audit = count(conn, "audit_energetique")
    if audit == -1:
        audit = count(conn, "audit_sme")
    return {
        "status": "✅" if audit > 0 else "❌",
        "detail": f"audit_energetique={audit}",
    }


def check_regops_scoring(conn):
    reg = count(conn, "reg_assessments")
    return {
        "status": "✅" if reg > 0 else "❌",
        "detail": f"reg_assessments={reg}",
    }


def check_compliance_findings(conn):
    findings = count(conn, "compliance_findings")
    statuses = distinct_values(conn, "compliance_findings", "insight_status")
    severities = distinct_values(conn, "compliance_findings", "severity")
    regulations = distinct_values(conn, "compliance_findings", "regulation")
    return {
        "status": "✅" if findings >= 15 and len(statuses) >= 3 else "⚠️" if findings >= 10 else "❌",
        "detail": f"findings={findings} statuses={statuses} severities={severities} regulations={regulations}",
        "count": findings,
        "statuses": statuses,
    }


def check_actions(conn):
    actions = count(conn, "action_items")
    source_types = distinct_values(conn, "action_items", "source_type")
    statuses = distinct_values(conn, "action_items", "status")
    return {
        "status": "✅" if actions >= 35 and len(source_types) >= 5 else "⚠️" if actions >= 10 else "❌",
        "detail": f"actions={actions} source_types={source_types} statuses={statuses}",
        "count": actions,
        "source_types": source_types,
    }


def check_purchase(conn):
    assumptions = count(conn, "purchase_assumption_sets")
    results = count(conn, "purchase_scenario_results")
    r = query_one(conn, "SELECT COUNT(DISTINCT site_id) FROM purchase_assumption_sets")
    sites = r[0] if r else 0
    return {
        "status": "✅" if assumptions >= 5 and results > 0 else "⚠️" if results > 0 else "❌",
        "detail": f"assumptions={assumptions} results={results} sites_covered={sites}",
        "sites_covered": sites,
    }


def check_monitoring(conn):
    snapshots = count(conn, "monitoring_snapshot")
    alerts = count(conn, "monitoring_alert")
    r = query_one(conn, "SELECT COUNT(DISTINCT site_id) FROM monitoring_snapshot")
    sites = r[0] if r else 0
    return {
        "status": "✅" if snapshots >= 5 and sites >= 5 else "⚠️" if snapshots > 0 else "❌",
        "detail": f"snapshots={snapshots} alerts={alerts} sites_covered={sites}",
    }


def check_usages_horaires(conn):
    schedules = count(conn, "site_operating_schedules")
    usages = count(conn, "usages")
    return {
        "status": "✅" if schedules >= 5 and usages > 0 else "⚠️" if usages > 0 else "❌",
        "detail": f"schedules={schedules} usages={usages}",
    }


def check_usages_drilldown(conn):
    usages = count(conn, "usages")
    # Usage links to site via batiment.site_id (no direct site_id on usages table)
    r = query_one(
        conn,
        """
        SELECT COUNT(DISTINCT b.site_id)
        FROM usages u JOIN batiments b ON u.batiment_id = b.id
        WHERE b.site_id IS NOT NULL
    """,
    )
    sites = r[0] if r else 0
    return {
        "status": "✅" if usages >= 25 and sites >= 5 else "⚠️" if usages > 0 else "❌",
        "detail": f"usages={usages} sites_via_batiment={sites}",
    }


def check_flex_scores(conn):
    # Flex scores are computed from Usage + PowerProfile
    usages = count(conn, "usages")
    pr = count(conn, "power_readings")
    flex_assets = count(conn, "flex_assets")
    return {
        "status": "✅" if usages > 0 and pr > 0 else "⚠️" if usages > 0 else "❌",
        "detail": f"usages={usages} power_readings={pr} flex_assets={flex_assets} (computed dynamically)",
    }


def check_energy_signature(conn):
    # Computed from MeterReading + weather
    readings = count(conn, "meter_reading")
    weather = count(conn, "ems_weather_cache")
    return {
        "status": "✅" if readings > 0 and weather > 0 else "❌",
        "detail": f"meter_readings={readings} weather_cache={weather} (computed dynamically)",
    }


def check_kb(conn):
    # KB items in main DB
    archetypes = count(conn, "kb_archetype")
    rules = count(conn, "kb_anomaly_rule")
    recos = count(conn, "kb_recommendation")
    versions = count(conn, "kb_version")
    return {
        "status": "✅" if archetypes > 0 and rules > 0 else "⚠️" if archetypes > 0 else "❌",
        "detail": f"archetypes={archetypes} rules={rules} recommendations={recos} versions={versions}",
    }


def check_market_prices(conn):
    mp = count(conn, "market_prices")
    mkt = count(conn, "mkt_prices")
    tariffs = count(conn, "regulated_tariffs")
    return {
        "status": "✅" if mkt > 0 or mp > 0 else "❌",
        "detail": f"market_prices={mp} mkt_prices={mkt} regulated_tariffs={tariffs}",
    }


def check_notifications(conn):
    events = count(conn, "notification_events")
    batches = count(conn, "notification_batches")
    return {
        "status": "✅" if events >= 20 else "⚠️" if events > 0 else "❌",
        "detail": f"events={events} batches={batches}",
        "count": events,
    }


def check_datapoints(conn):
    dp = count(conn, "data_points")
    if dp == -1:
        dp = count(conn, "datapoints")
    if dp == -1:
        dp = count(conn, "datapoint")
    return {
        "status": "✅" if dp > 0 else "❌",
        "detail": f"data_points={dp}",
        "count": dp,
    }


def check_reg_source_events(conn):
    rse = count(conn, "reg_source_events")
    return {
        "status": "✅" if rse >= 4 else "❌",
        "detail": f"reg_source_events={rse}",
        "count": rse,
    }


def check_evidence(conn):
    ev = count(conn, "evidences")
    r = query_one(conn, "SELECT COUNT(DISTINCT site_id) FROM evidences")
    sites = r[0] if r else 0
    return {
        "status": "✅" if ev >= 20 and sites >= 3 else "⚠️" if ev > 0 else "❌",
        "detail": f"evidences={ev} sites_covered={sites}",
        "count": ev,
    }


def check_site_intelligence(conn):
    # Computed from KB archetype matches
    recos = count(conn, "recommendation")
    anomalies = count(conn, "anomaly")
    return {
        "status": "✅" if recos > 0 and anomalies > 0 else "⚠️" if recos > 0 else "❌",
        "detail": f"recommendations={recos} anomalies={anomalies} (computed dynamically)",
    }


def check_cockpit(conn):
    # Aggregation of multiple modules — check critical dependencies
    sites = count(conn, "sites")
    invoices = count(conn, "energy_invoices")
    findings = count(conn, "compliance_findings")
    actions = count(conn, "action_items")
    return {
        "status": "✅" if sites > 0 and invoices > 0 and findings > 0 and actions > 0 else "⚠️",
        "detail": f"Deps: sites={sites} invoices={invoices} findings={findings} actions={actions}",
    }


def check_dt_progress(conn):
    efa_conso = count(conn, "tertiaire_efa_consumption")
    targets = count(conn, "consumption_targets")
    return {
        "status": "✅" if efa_conso > 0 and targets > 0 else "❌",
        "detail": f"efa_consumption={efa_conso} targets={targets}",
    }


# ─── Main ────────────────────────────────────────────────────────────────────

MODULES = [
    ("Patrimoine", check_patrimoine),
    ("Consommation", check_consommation),
    ("Puissance", check_puissance),
    ("Facturation", check_facturation),
    ("Contrats V2", check_contrats_v2),
    ("Shadow Billing", check_shadow_billing),
    ("Conformité DT", check_conformite_dt),
    ("BACS", check_bacs),
    ("APER", check_aper),
    ("Audit Énergétique/SMÉ", check_audit_sme),
    ("RegOps Scoring", check_regops_scoring),
    ("Compliance Findings", check_compliance_findings),
    ("Actions", check_actions),
    ("Achat Énergie", check_purchase),
    ("Monitoring", check_monitoring),
    ("Usages & Horaires", check_usages_horaires),
    ("Usages (drill-down)", check_usages_drilldown),
    ("Flex Scores", check_flex_scores),
    ("Energy Signature", check_energy_signature),
    ("KB", check_kb),
    ("Market Prices", check_market_prices),
    ("Notifications", check_notifications),
    ("DataPoints", check_datapoints),
    ("RegSourceEvents", check_reg_source_events),
    ("Evidence / Preuves", check_evidence),
    ("Site Intelligence", check_site_intelligence),
    ("Cockpit", check_cockpit),
    ("DT Progress", check_dt_progress),
]


def main():
    conn = connect()
    print(f"=== PROMEOS Seed Audit — {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    # 1. Table inventory
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"Tables totales : {len(tables)}")

    non_empty = 0
    for t in tables:
        c = count(conn, t)
        if c > 0:
            non_empty += 1
    print(f"Tables non-vides : {non_empty}/{len(tables)}\n")

    # 2. Module audit
    results = []
    ok = 0
    warn = 0
    fail = 0

    for name, check_fn in MODULES:
        r = check_fn(conn)
        results.append((name, r))
        if r["status"] == "✅":
            ok += 1
        elif r["status"] == "⚠️":
            warn += 1
        else:
            fail += 1
        print(f"  {r['status']} {name}: {r['detail']}")

    print(f"\n{'=' * 60}")
    print(f"BILAN : {ok}/28 ✅  |  {warn}/28 ⚠️  |  {fail}/28 ❌")
    print(f"{'=' * 60}\n")

    # 3. Generate report
    report = [
        f"# SEED AUDIT REPORT — HELIOS",
        f"",
        f"**Date** : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**Pack** : helios  **Size** : S",
        f"**DB** : `backend/data/promeos.db`",
        f"",
        f"## Résumé",
        f"",
        f"| Statut | Count |",
        f"|--------|-------|",
        f"| ✅ OK | {ok} |",
        f"| ⚠️ Partiel | {warn} |",
        f"| ❌ Vide/Manquant | {fail} |",
        f"| **Total** | **28** |",
        f"",
        f"## Détail par module",
        f"",
        f"| # | Module | Statut | Détail |",
        f"|---|--------|--------|--------|",
    ]

    for i, (name, r) in enumerate(results, 1):
        detail = r["detail"].replace("|", "\\|")
        report.append(f"| {i} | {name} | {r['status']} | {detail} |")

    # Gaps section
    gaps = [(name, r) for name, r in results if r["status"] != "✅"]
    if gaps:
        report.append("")
        report.append("## Gaps à combler (Phase 1)")
        report.append("")
        for name, r in gaps:
            report.append(f"### {r['status']} {name}")
            report.append(f"- {r['detail']}")
            report.append("")

    report_text = "\n".join(report) + "\n"
    report_path = os.path.abspath(REPORT_PATH)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"📄 Report saved: {report_path}")
    conn.close()


if __name__ == "__main__":
    main()
