"""
PROMEOS — Sol V1 (agentic assistant).

Infrastructure agentique Sol V1 : les 5 lois en code.

Package organisation :
- schemas : types Pydantic (IntentKind, ActionPhase, ActionPlan, etc.)
- utils : fondations (datetime, hash, tokens HMAC, formatters FR)
- voice : frenchifier + SOL_VOICE_TEMPLATES_V1
- boundaries : OUT_OF_SCOPE_PATTERNS + BOUNDARY_RESPONSES
- context : SolContext builder depuis request FastAPI
- engines : moteurs déterministes par intent (Sprint 3+)
- planner / validator / scheduler / audit : orchestration (Phase 3)
- llm_client : wrapper Claude Haiku sandboxé (Sprint 7-8)

Modèles SQLAlchemy : backend/models/sol.py (Phase 1, déjà livré).

Décisions : docs/sol/DECISIONS_LOG.md
Prompt applicable : docs/sol/PROMPT_SOL_V1_SPRINT_1-2_APPLIED.md
"""
