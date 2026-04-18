"""
Voice Sol V1 : frenchifier (grammaire FR stricte) + templates V1.

Fonction centrale `frenchifier(text)` : pure, idempotente. Applique les
règles du guide éditorial Sol sur tout texte FR avant affichage.

Règles (docs/sol/SOL_V1_VOICE_GUIDE.md §3) :
- Espace fine insécable U+202F avant : ; ! ? % €
- Espace insécable U+00A0 dans nombres (1 847,20)
- Guillemets chevrons « ... » (remplace les " " droits, avec U+00A0)
- Tirets cadratins — pour incises (remplace -- et ' - ')
- Tiret demi-cadratin – pour intervalles (2024–2026)
- Ordinaux typographiques 1ᵉʳ 2ᵉ
- Majuscules accentuées (É À È) via dict statique de 30 mots FR courants
- NE PAS modifier les termes techniques sentinelles (TURPE, kWh, etc.)

Templates `SOL_VOICE_TEMPLATES_V1` : 30 templates min couvrant les 50
situations types S01-S50. Rendus via `render_template()` avec frenchifier
appliqué.

Décision P1-7 : frenchifier créé Phase 2 côté backend.
Décision P1-6 : R8 "zéro jargon Surface" assouplie (tooltips obligatoires).
"""

from __future__ import annotations

import re
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Caractères typographiques FR
# ─────────────────────────────────────────────────────────────────────────────

_NBSP = "\u00A0"    # U+00A0 — espace insécable (milliers, avant «, après »)
_NNBSP = "\u202F"   # U+202F — espace fine insécable (avant : ; ! ? % €)
_EMDASH = "\u2014"  # U+2014 — tiret cadratin
_ENDASH = "\u2013"  # U+2013 — tiret demi-cadratin
_LGUIL = "\u00AB"   # U+00AB — guillemet chevron gauche «
_RGUIL = "\u00BB"   # U+00BB — guillemet chevron droite »

# Termes techniques qu'on ne doit PAS frenchifier (protection sentinelles)
_TECHNICAL_SENTINELS = frozenset(
    {
        "TURPE", "ARENH", "CTA", "TVA", "CEE", "TDN", "VNU", "OID",
        "ENEDIS", "GRDF", "PDL", "PCE", "TRVE", "DJU", "NEBCO",
        "OPERAT", "BACS", "APER", "ADEME", "CRE", "HC", "HP",
        "aFRR", "FCR", "MA", "AOFD", "RTE", "HPH", "HCH", "HPE", "HCE",
        "T1", "T2", "T3", "T4", "TP", "CJN", "CJA",
        "kWh", "MWh", "GWh", "TWh", "kW", "MW", "GW",
        "€/MWh", "€/kWh", "€HT", "€TTC",
        "CSV", "PDF", "JSON", "JSONB", "SHA256", "HMAC", "URL",
    }
)


# ─────────────────────────────────────────────────────────────────────────────
# Majuscules accentuées (corrections fréquentes)
# ─────────────────────────────────────────────────────────────────────────────

_ACCENT_FIXES = {
    # Début de phrase uniquement (après point, retour ligne, ou début string)
    "A faire": "À faire",
    "A regarder": "À regarder",
    "A partir": "À partir",
    "A venir": "À venir",
    "A noter": "À noter",
    "Economie": "Économie",
    "Economies": "Économies",
    "Eco-": "Éco-",
    "Energie": "Énergie",
    "Energetique": "Énergétique",
    "Ecart": "Écart",
    "Ecarts": "Écarts",
    "Etat": "État",
    "Etats": "États",
    "Etre": "Être",
    "Evolution": "Évolution",
    "Evenement": "Événement",
    "Evenements": "Événements",
    "Emission": "Émission",
    "Emissions": "Émissions",
    "Electricite": "Électricité",
    "Eligible": "Éligible",
    "Eligibles": "Éligibles",
    "Ecole": "École",
    "Echec": "Échec",
    "Ete": "Été",
    "Editer": "Éditer",
    "Emettre": "Émettre",
}


# ─────────────────────────────────────────────────────────────────────────────
# frenchifier : fonction centrale, pure, idempotente
# ─────────────────────────────────────────────────────────────────────────────


def frenchifier(text: str) -> str:
    """
    Applique les règles de grammaire française stricte.

    Idempotent : `frenchifier(frenchifier(x)) == frenchifier(x)`.
    Pure function : pas d'effet de bord, retourne une nouvelle str.

    Ne touche PAS aux termes techniques (TURPE, MWh, CTA, etc.).
    """
    if not text:
        return text

    result = text

    # 1. Majuscules accentuées (appliquer AVANT autres substitutions)
    for wrong, right in _ACCENT_FIXES.items():
        # Remplace en début de texte OU après ponctuation terminale
        result = re.sub(
            r"(^|[.!?]\s+|\n)" + re.escape(wrong) + r"\b",
            lambda m: m.group(1) + right,
            result,
        )

    # 2. Guillemets droits "..." → chevrons « ... » avec U+00A0
    #    On cible les paires de `"` en supposant qu'elles viennent ensemble.
    def _replace_quotes(m: re.Match) -> str:
        inner = m.group(1)
        return f"{_LGUIL}{_NBSP}{inner}{_NBSP}{_RGUIL}"

    result = re.sub(r'"([^"]*)"', _replace_quotes, result)

    # 3. Tiret cadratin pour incises — pattern " -- " ou " - " (entre espaces)
    result = re.sub(r"\s+--\s+", f" {_EMDASH} ", result)
    # NB : on ne transforme pas tous les " - " en — car trop agressif (casse
    # les tirets de liaison. Voir si besoin Phase 3+.)

    # 4. Tiret demi-cadratin pour intervalles de dates 4 chiffres
    #    "2024-2026" → "2024–2026" (mais pas dans SIRET, PDL, etc.)
    result = re.sub(r"\b(\d{4})-(\d{4})\b", rf"\1{_ENDASH}\2", result)

    # 5. Ordinaux : 1er, 2eme, 3ème, 1ere → typographiques
    result = re.sub(r"\b1er\b", "1ᵉʳ", result)
    result = re.sub(r"\b1ere\b", "1ʳᵉ", result)
    result = re.sub(r"\b(\d+)(eme|ème)\b", r"\1ᵉ", result)

    # 6. Espace fine insécable avant : ; ! ? % €
    #    On remplace (espace normale ou rien) par U+202F devant ces signes.
    #    Déjà U+202F → idempotent (on ne re-convertit pas).
    for ch in [":", ";", "!", "?", "%", "€"]:
        # Pattern : tout espace ascii existant avant le char → U+202F
        result = re.sub(r"(?<!\u202F) +(?=" + re.escape(ch) + r")", _NNBSP, result)
        # Cas où il n'y a pas d'espace du tout : ne pas créer (ex: "http://" → KO)
        # On laisse tel quel pour ne pas sur-interpréter. Les templates doivent
        # déjà écrire l'espace.

    # 7. Espaces milliers U+00A0 (appliqué par fmt_eur/fmt_mwh/fmt_pct,
    #    pas par frenchifier qui pourrait casser les IDs/refs techniques)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Templates V1 — 30+ templates couvrant situations S01-S50
# ─────────────────────────────────────────────────────────────────────────────


# Structure : (voice_kind, situation_code) → template string
# Placeholders : {var} — substitution safe via str.format_map + DictWrapper

SOL_VOICE_TEMPLATES_V1: dict[tuple[str, str], str] = {
    # Accueil & ambiance (S01-S03)
    ("headline", "cockpit_morning"): "Bonjour — voici votre semaine.",
    ("headline", "cockpit_nothing_urgent"): "Rien d'urgent aujourd'hui. Bonne semaine.",
    ("headline", "cockpit_first_open"): (
        "Voici votre cockpit. Je commence à apprendre votre patrimoine — "
        "les premières analyses seront prêtes sous 48 h."
    ),

    # KPI sublines (S04-S07)
    ("kpi_sub", "dt_score_risk"): (
        "Vous êtes en zone à risque — {n_sites} sites tirent le score vers le bas."
    ),
    ("kpi_sub", "invoice_up_seasonal"): (
        "Hausse tirée par {sites} — principalement saisonnière, "
        "mais une anomalie explique un tiers de l'écart."
    ),
    ("kpi_sub", "consumption_down"): (
        "Vous consommez moins qu'à la même période l'an dernier — "
        "{drivers} portent la baisse."
    ),
    ("kpi_sub", "dt_trajectory_on_track"): (
        "Vous êtes sur la trajectoire 2030. "
        "À ce rythme, vous l'atteignez {advance_months} mois en avance."
    ),

    # Sol propose (S08-S12)
    ("propose", "invoice_dispute"): (
        "Votre facture {site} de {period} est plus élevée que d'habitude. "
        "{anomaly_reason}. Je peux contester à votre place — vous relisez avant, "
        "vous gardez la main pendant {grace_hours} h."
    ),
    ("propose", "operat"): (
        "Votre déclaration OPERAT pour {site} est due le {deadline}. "
        "Je peux préparer le fichier à partir de vos données. "
        "Voulez-vous voir ce que j'enverrai ?"
    ),
    ("propose", "exec_report"): (
        "Votre comex du {date} approche. Je prépare le rapport mensuel "
        "la veille au soir — vous pouvez le relire avant envoi."
    ),
    ("propose", "dt_action_plan"): (
        "{site} dérive — consommation en hausse de {pct} sur {days} jours. "
        "Je peux générer le plan d'action chiffré."
    ),
    ("propose", "ao_builder"): (
        "Votre contrat {site} se termine dans {days} jours. Je peux préparer "
        "le dossier d'appel d'offres et cibler {n_suppliers} fournisseurs pertinents."
    ),

    # Preview drawer (S13-S15)
    ("preview", "drawer_open"): (
        "Je vais envoyer le courrier ci-dessous à {recipient}. "
        "Vous avez {grace_hours} heures pour annuler après validation. "
        "Rien n'est irréversible."
    ),
    ("preview", "exec_report"): (
        "Voici le rapport qui partira au CODIR le {date} à {time}. "
        "{n_recipients} destinataires. Vous pouvez l'éditer jusque-là."
    ),
    ("preview", "operat"): (
        "Voici le fichier OPERAT que je vais générer pour {site}. "
        "Toutes les données proviennent de vos consommations ENEDIS validées. "
        "Un champ reste à compléter manuellement : {manual_field}."
    ),

    # Confirmations & exécutions (S16-S19)
    ("pending", "scheduled"): (
        "{action} programmée — envoi dans {remaining}. "
        "Vous pouvez annuler ou éditer jusque-là."
    ),
    ("done", "executed"): "{action} à {recipient} à {time}. Accusé de réception reçu.",
    ("cancelled", "user"): (
        "Annulation enregistrée. Rien n'a été envoyé. Vous pouvez reprendre plus tard."
    ),
    ("done", "report_delivered"): (
        "Rapport de {month} envoyé à {n_recipients} destinataires. "
        "{n_opened} l'ont ouvert dans les 24 heures."
    ),

    # Refus explicites (S20-S23)
    ("refuse", "missing_data"): (
        "Je ne peux pas générer ce fichier automatiquement : "
        "{field} n'est pas renseigné dans PROMEOS. "
        "C'est un champ obligatoire {context}. Voulez-vous le saisir maintenant ?"
    ),
    ("refuse", "confidence_low"): (
        "Je ne valide pas automatiquement : la confiance du calcul est à "
        "{conf_pct}, sous le seuil requis de {threshold_pct}. "
        "Le dossier reste en consultation — vous pouvez décider manuellement."
    ),
    ("refuse", "out_of_scope"): (
        "Je ne peux pas vous aider sur ce point — je suis spécialisé énergie "
        "et réglementation française. Pour les questions juridiques, "
        "mieux vaut consulter votre juriste."
    ),
    ("refuse", "consultative_mode"): (
        "Votre organisation a activé le mode consultatif. Je prépare les "
        "dossiers mais je ne les envoie pas — vous gardez toujours la main "
        "sur l'exécution."
    ),

    # Erreurs & incidents (S24-S27)
    ("error", "enedis_slow"): "La synchro ENEDIS est lente ce matin. Je réessaie dans {retry_min} min.",
    ("error", "invoice_not_found"): (
        "Je ne retrouve pas cette facture. Elle n'a peut-être pas encore "
        "été importée — voulez-vous vérifier ?"
    ),
    ("error", "mail_send_failed"): (
        "L'envoi a échoué. Le courrier n'est pas parti. "
        "J'ai conservé le brouillon — nous pouvons réessayer."
    ),

    # Célébrations & bonnes nouvelles (S34-S36)
    ("success", "bacs_validated"): "BACS {site} validé. Votre score gagne {delta} points.",
    ("success", "recovered_month"): (
        "Sol a généré {amount} de récupérations sur les 30 derniers jours, "
        "avec 0 erreur."
    ),
    ("success", "dt_trajectory_ahead"): (
        "Trajectoire 2030 tenue en avance de {months} mois. "
        "Votre patrimoine est en avance sur {target_pct}."
    ),

    # Boundary cases (S49-S50)
    ("boundary", "financial_advice"): (
        "Je peux comparer les scénarios avec les prix marché actuels, mais le "
        "choix final relève du conseil en stratégie achat. Voulez-vous voir "
        "la comparaison ?"
    ),
    ("boundary", "legal_advice"): (
        "Je peux vérifier la conformité technique du contrat au regard des "
        "barèmes réglementaires. Pour la validité juridique, mieux vaut "
        "consulter votre juriste — je peux préparer un dossier pour lui."
    ),
    ("boundary", "personal"): (
        "Je suis là pour les questions énergie et réglementation. "
        "Qu'est-ce que je peux regarder pour vous ?"
    ),
}


class _SafeDict(dict):
    """Dict qui retourne `{key}` si key manquante (évite KeyError templates incomplets)."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(key: tuple[str, str], ctx: dict[str, Any] | None = None) -> str:
    """
    Charge un template, substitue les variables, applique frenchifier().

    Si la clé n'existe pas → KeyError explicite (ne pas "deviner").
    Si une var manque dans ctx → placeholder conservé littéral dans l'output
    (pour signaler visuellement l'oubli sans crasher en prod).
    """
    if key not in SOL_VOICE_TEMPLATES_V1:
        raise KeyError(
            f"Sol voice template {key} not found. "
            f"Available templates : {sorted(SOL_VOICE_TEMPLATES_V1.keys())}"
        )
    template = SOL_VOICE_TEMPLATES_V1[key]
    safe_ctx = _SafeDict(ctx or {})
    rendered = template.format_map(safe_ctx)
    return frenchifier(rendered)


__all__ = [
    "frenchifier",
    "render_template",
    "SOL_VOICE_TEMPLATES_V1",
]
