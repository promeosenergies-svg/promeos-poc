"""
PROMEOS — ConnectorToken model pour stockage OAuth2 tokens (Enedis, GRDF, etc.)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Date, UniqueConstraint
from models.base import Base, TimestampMixin


class ConnectorToken(Base, TimestampMixin):
    """Token OAuth2 stocké par connecteur et par PRM/PCE.

    connector_name: "enedis_dataconnect" ou "grdf_adict"
    prm: identifiant du point (PRM 14 chiffres, PCE, ou "__client__" pour client_credentials)
    """

    __tablename__ = "connector_tokens"
    __table_args__ = (UniqueConstraint("connector_name", "prm", name="uq_connector_token_prm"),)

    id = Column(Integer, primary_key=True)
    connector_name = Column(String(50), nullable=False, index=True)
    prm = Column(String(14), nullable=False, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(20), default="Bearer")
    expires_at = Column(DateTime, nullable=False)
    scope = Column(String(200), nullable=True)
    consent_expiry = Column(Date, nullable=True)
    consent_status = Column(String(20), default="unknown")  # active/revoked/expired/unknown

    def __repr__(self):
        return f"<ConnectorToken({self.connector_name}, prm={self.prm}, status={self.consent_status})>"
