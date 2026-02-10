"""
PROMEOS KB - Service (Apply Engine)
Deterministic evaluation of KB items against site_context
HARD RULE: No recommendation without structured KB item
"""
from typing import List, Dict, Any, Optional
from .store import KBStore
from .indexer import KBIndexer


class KBService:
    """KB Service with apply engine"""

    def __init__(self):
        self.store = KBStore()
        self.indexer = KBIndexer()

    def apply(
        self,
        site_context: Dict[str, Any],
        domain: Optional[str] = None,
        allow_drafts: bool = False
    ) -> Dict[str, Any]:
        """
        Apply KB items to site_context
        Returns applicable items with explanations, actions, and sources

        HARD RULE: allow_drafts=False by default -> only validated items used for decisions.
        Drafts (confidence=low) are NEVER used in decisional mode unless explicitly requested.

        Args:
            site_context: Site data (surface_m2, hvac_kw, building_type, etc.)
            domain: Optional filter by domain
            allow_drafts: If False (default), only validated items are used.
                         If True, drafts are included (for exploration only).

        Returns:
            {
                "applicable_items": List[ApplicableItem],
                "missing_fields": List[str],
                "status": "ok" | "partial" | "insufficient",
                "suggestions": List[str]
            }
        """
        # GUARD: Only validated items by default — no decision without validated item
        status_filter = None if allow_drafts else "validated"
        items = self.store.get_items(domain=domain, status=status_filter, limit=1000)

        applicable_items = []
        missing_fields = set()

        for item in items:
            result = self._evaluate_item(item, site_context)

            if result["applicable"]:
                applicable_items.append({
                    "kb_item_id": item["id"],
                    "title": item["title"],
                    "domain": item["domain"],
                    "type": item["type"],
                    "confidence": item["confidence"],
                    "priority": item.get("priority", 3),
                    "why": result["why"],
                    "actions": result["actions"],
                    "sources": item["sources"],
                    "missing_inputs": result["missing_inputs"]
                })

            # Collect missing fields
            missing_fields.update(result["missing_inputs"])

        # Sort by priority (1=highest) then confidence
        confidence_order = {"high": 1, "medium": 2, "low": 3}
        applicable_items.sort(
            key=lambda x: (x["priority"], confidence_order.get(x["confidence"], 3))
        )

        # Determine status
        if not applicable_items and len(missing_fields) > 0:
            status = "insufficient"
        elif len(missing_fields) > 0:
            status = "partial"
        else:
            status = "ok"

        # Generate suggestions
        suggestions = self._generate_suggestions(
            applicable_items,
            missing_fields,
            site_context
        )

        return {
            "applicable_items": applicable_items,
            "missing_fields": sorted(list(missing_fields)),
            "status": status,
            "suggestions": suggestions,
            "stats": {
                "total_items_evaluated": len(items),
                "applicable_count": len(applicable_items),
                "missing_fields_count": len(missing_fields)
            }
        }

    def _evaluate_item(
        self,
        item: Dict[str, Any],
        site_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate single KB item against site_context
        Returns: {applicable: bool, why: List[str], actions: List, missing_inputs: List[str]}
        """
        scope = item.get("scope", {})
        logic = item.get("logic", {})

        # Track why conditions are true
        why = []
        missing_inputs = []

        # Evaluate scope (high-level conditions)
        scope_pass = self._evaluate_scope(scope, site_context, why, missing_inputs)

        # If scope doesn't pass, item is not applicable
        if not scope_pass:
            return {
                "applicable": False,
                "why": why,
                "actions": [],
                "missing_inputs": missing_inputs
            }

        # Evaluate logic.when (detailed conditions)
        logic_pass = True
        actions = []

        if logic and "when" in logic:
            logic_pass = self._evaluate_when(
                logic["when"],
                site_context,
                why,
                missing_inputs
            )

            # If logic passes, extract actions from logic.then
            if logic_pass and "then" in logic:
                actions = logic["then"].get("outputs", [])

        return {
            "applicable": logic_pass,
            "why": why,
            "actions": actions,
            "missing_inputs": missing_inputs
        }

    def _evaluate_scope(
        self,
        scope: Dict[str, Any],
        context: Dict[str, Any],
        why: List[str],
        missing: List[str]
    ) -> bool:
        """
        Evaluate scope conditions (null-safe)
        Returns True if all scope conditions pass
        """
        if not scope:
            return True

        for field, expected in scope.items():
            value = context.get(field)

            # Null-safe: missing field = False
            if value is None:
                missing.append(field)
                why.append(f"{field} is NULL (required for scope)")
                return False

            # List comparison (value must be in list)
            if isinstance(expected, list):
                if value not in expected:
                    why.append(f"{field}={value} not in {expected}")
                    return False
                else:
                    why.append(f"{field}={value} matches scope")

            # Min/max comparisons
            elif field.endswith("_min"):
                base_field = field[:-4]
                actual_value = context.get(base_field)
                if actual_value is None:
                    missing.append(base_field)
                    return False
                if actual_value < expected:
                    why.append(f"{base_field}={actual_value} < {expected} (min)")
                    return False
                else:
                    why.append(f"{base_field}={actual_value} >= {expected} (min)")

            elif field.endswith("_max"):
                base_field = field[:-4]
                actual_value = context.get(base_field)
                if actual_value is None:
                    missing.append(base_field)
                    return False
                if actual_value > expected:
                    why.append(f"{base_field}={actual_value} > {expected} (max)")
                    return False
                else:
                    why.append(f"{base_field}={actual_value} <= {expected} (max)")

            # Exact match
            else:
                if value != expected:
                    why.append(f"{field}={value} != {expected}")
                    return False
                else:
                    why.append(f"{field}={value} matches scope")

        return True

    def _evaluate_when(
        self,
        when: Dict[str, Any],
        context: Dict[str, Any],
        why: List[str],
        missing: List[str]
    ) -> bool:
        """
        Evaluate logic.when conditions (null-safe)
        Supports: all, any, condition objects
        """
        # Handle "all" (AND)
        if "all" in when:
            conditions = when["all"]
            for cond in conditions:
                if not self._evaluate_condition(cond, context, why, missing):
                    return False
            return True

        # Handle "any" (OR)
        elif "any" in when:
            conditions = when["any"]
            for cond in conditions:
                if self._evaluate_condition(cond, context, why, missing):
                    return True
            return False

        # Single condition
        else:
            return self._evaluate_condition(when, context, why, missing)

    def _evaluate_condition(
        self,
        cond: Dict[str, Any],
        context: Dict[str, Any],
        why: List[str],
        missing: List[str]
    ) -> bool:
        """
        Evaluate single condition
        Format: {field: "x", op: ">=", value: 100}
        """
        field = cond.get("field")
        op = cond.get("op")
        expected = cond.get("value")

        actual = context.get(field)

        # Null-safe: missing field = False
        if actual is None:
            missing.append(field)
            why.append(f"{field} is NULL (required)")
            return False

        # Evaluate operation
        try:
            if op == "==" or op == "=":
                result = actual == expected
            elif op == "!=":
                result = actual != expected
            elif op == ">":
                result = actual > expected
            elif op == ">=":
                result = actual >= expected
            elif op == "<":
                result = actual < expected
            elif op == "<=":
                result = actual <= expected
            elif op == "in":
                result = actual in expected
            elif op == "contains":
                result = expected in actual
            elif op == "exists":
                result = actual is not None
            else:
                why.append(f"Unknown op '{op}' for {field}")
                return False

            # Log why
            if result:
                why.append(f"{field} {op} {expected}: TRUE ({actual})")
            else:
                why.append(f"{field} {op} {expected}: FALSE ({actual})")

            return result

        except Exception as e:
            why.append(f"Error evaluating {field} {op} {expected}: {e}")
            return False

    def _generate_suggestions(
        self,
        applicable_items: List[Dict],
        missing_fields: set,
        site_context: Dict
    ) -> List[str]:
        """Generate suggestions for user"""
        suggestions = []

        if not applicable_items and missing_fields:
            suggestions.append(
                f"Collect missing data to unlock KB items: {', '.join(sorted(missing_fields))}"
            )

        if len(applicable_items) > 0:
            high_priority = [i for i in applicable_items if i["priority"] == 1]
            if high_priority:
                suggestions.append(
                    f"{len(high_priority)} high-priority items require action"
                )

        return suggestions
