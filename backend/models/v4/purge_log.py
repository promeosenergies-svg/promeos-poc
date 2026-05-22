"""PurgeLog — audit RGPD article 30 / journal des purges PII (M2-6.A.2).

CNIL article 30 exige un registre des traitements. Toute purge PII exécutée
par un admin doit être tracée avec :
  - `user_id_hash` (pas le user_id en clair — pour ne pas re-créer du PII)
  - `purged_at` timestamp précis (preuve délai légal 1 mois RGPD art. 17)
  - `purged_by_admin_id` (chain of custody — admin responsable)
  - `reason` (justification métier : demande user, audit, etc.)
  - `report_json` (compteurs entités traitées — preuve d'exécution complète)
  - `dry_run` (flag preview vs purge effective)

⚠️ `purged_by_admin_id` n'est PAS une FK : l'admin lui-même peut être purgé
plus tard. On garde l'id en colonne nue pour préserver l'audit historique.
La même logique s'applique aux user_id purgés (qui n'apparaissent qu'en
SHA256, jamais en clair).

Table plateforme-scoped (pas org-scoped) — la purge concerne un user, pas
une org, et le journal CNIL doit être lisible par le DPO de la plateforme.
"""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from models.base import Base


class PurgeLog(Base):
    __tablename__ = "purge_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id_hash = Column(String(64), nullable=False, index=True)
    purged_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    purged_by_admin_id = Column(Integer, nullable=False)
    reason = Column(String(500), nullable=False)
    report_json = Column(Text, nullable=False)
    dry_run = Column(Boolean, nullable=False, server_default="false", default=False)

    def __repr__(self) -> str:
        return f"<PurgeLog hash={self.user_id_hash[:8]}… at={self.purged_at} dry={self.dry_run}>"
