"""Conftest local backend/tests/unit/ — Sprint M2-2.

Fixtures isolées pour tests unit V4 :
- Override l'autouse parent `_ensure_seeded` (qui exigerait DB HELIOS réelle)
- Fournit `v4_session` : SQLAlchemy session in-memory SQLite avec les 8 tables V4 créées

Critère d'attention M2-2 #8 respecté : tests unit utilisent `:memory:` (PAS DB prod).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.base import Base

# Import V4 models pour enregistrer leurs tables dans Base.metadata
# (import direct des modules V4 — bypass backend.models.__init__.py qui charge tout legacy)
from models.v4.action_blockers import ActionBlocker
from models.v4.action_center_items import ActionCenterItem
from models.v4.action_event_log import ActionEventLog
from models.v4.action_links import ActionLink
from models.v4.action_scenarios import ActionScenario
from models.v4.duplicate_groups import DuplicateGroup
from models.v4.evidences import Evidence
from models.v4.recurrence_groups import RecurrenceGroup

# Liste des 8 tables V4 (subset Base.metadata pour create_all isolé)
V4_TABLES = [
    DuplicateGroup.__table__,
    RecurrenceGroup.__table__,
    ActionCenterItem.__table__,
    ActionEventLog.__table__,
    Evidence.__table__,
    ActionLink.__table__,
    ActionBlocker.__table__,
    ActionScenario.__table__,
]


@pytest.fixture(scope="module", autouse=True)
def _ensure_seeded():
    """Override le parent conftest._ensure_seeded — tests unit utilisent :memory: SQLite.

    Pas besoin de seeder HELIOS sur DB réelle pour tester les CHECK constraints
    SQLAlchemy V4 isolés.
    """
    return  # no-op : neutralise l'autouse parent


@pytest.fixture(scope="function")
def v4_session():
    """SQLAlchemy session in-memory SQLite avec les 8 tables V4 créées.

    Critère d'attention M2-2 #8 : :memory: (PAS DB prod).
    Function-scoped : chaque test démarre avec DB clean.
    """
    # SQLite in-memory avec foreign keys ON (par défaut OFF en SQLite)
    engine = create_engine("sqlite:///:memory:", future=True)

    # Activer les FK constraints SQLite (pour tester ON DELETE RESTRICT/CASCADE)
    @pytest.fixture
    def _enable_fk(_):  # Note : SQLite FK enforcement requires PRAGMA per connection
        pass

    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Créer juste les 8 tables V4 (bypass legacy)
    Base.metadata.create_all(engine, tables=V4_TABLES)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()
