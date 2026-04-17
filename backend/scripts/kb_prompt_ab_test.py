"""
kb_prompt_ab_test.py -- Compare la qualite des reponses agents avec/sans contexte KB.
Mesure l'impact du contexte KB sur la precision des agents.

Usage:
    cd backend && python scripts/kb_prompt_ab_test.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


VALIDATION_CHECKS = {
    "has_correct_co2": lambda r: "0.052" in r or "0,052" in r,
    "has_correct_accise": lambda r: "30.85" in r or "30,85" in r,
    "avoids_turpe_confusion": lambda r: "0.0569" not in r.split("kgCO2")[0][-100:] if "kgCO2" in r else True,
    "avoids_wrong_price": lambda r: "0.18" not in r and "0,18" not in r,
    "cites_source": lambda r: any(src in r for src in ["ADEME", "CRE", "JORF", "RTE"]),
}


def run_ab_test_offline():
    """
    Test offline : verifie que build_kb_prompt_section genere du contenu
    contenant les valeurs attendues.
    """
    from ai_layer.kb_context import build_kb_prompt_section

    kb_section = build_kb_prompt_section(domain="facturation")

    if not kb_section:
        print("[AB Test] ERREUR: kb_section vide -- verifier kb.db")
        return

    results = {}
    for check_name, check_fn in VALIDATION_CHECKS.items():
        results[check_name] = check_fn(kb_section)

    score = sum(results.values()) / len(results)
    print(f"[AB Test] Score KB section : {score:.0%}")
    for name, passed in results.items():
        status = "OK" if passed else "FAIL"
        print(f"  [{status}] {name}")

    output = {
        "mode": "offline",
        "kb_section_length": len(kb_section),
        "checks": results,
        "score": score,
    }

    output_path = os.path.join(os.path.dirname(__file__), "..", "results")
    os.makedirs(output_path, exist_ok=True)
    with open(os.path.join(output_path, "ab_test_latest.json"), "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[AB Test] Resultats exportes -> results/ab_test_latest.json")
    return output


if __name__ == "__main__":
    run_ab_test_offline()
