"""Conftest local backend/tests/unit/ — Sprint M2-2 (étendu M2-4.1).

Fixtures isolées pour tests unit V4 :
- Override l'autouse parent `_ensure_seeded` (qui exigerait DB HELIOS réelle)
- Fournit `v4_session` : SQLAlchemy session in-memory SQLite avec un stub
  `organisations` (seedé) + les 8 tables V4 créées

Critère d'attention M2-2 #8 respecté : tests unit utilisent `:memory:` (PAS DB prod).

M2-4.1 (ADR-009 Option D) : `organisation_id` V4 est désormais un Integer FK
vers `organisations.id`. Sous `PRAGMA foreign_keys=ON`, les INSERT V4 exigent
une ligne parente. On crée un STUB minimal `organisations` (colonne `id` seule,
dans une MetaData dédiée) plutôt que la table legacy réelle — celle-ci traîne
une FK `users` qui entraînerait tout le schéma legacy dans les tests unit.
"""

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
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

# M2-4.1 : org de test, cible des FK organisation_id V4 (Integer FK · ADR-009 Option D).
TEST_ORG_ID = 1

# Stub minimal `organisations` (id PK seul) dans une MetaData dédiée — pas de
# collision avec la table `organisations` réelle de Base.metadata (legacy
# Organisation). Les FK V4 résolvent `organisations` par nom au runtime SQLite.
_org_stub_metadata = MetaData()
_organisations_stub = Table(
    "organisations",
    _org_stub_metadata,
    Column("id", Integer, primary_key=True),
)


@pytest.fixture(scope="module", autouse=True)
def _ensure_seeded():
    """Override le parent conftest._ensure_seeded — tests unit utilisent :memory: SQLite.

    Pas besoin de seeder HELIOS sur DB réelle pour tester les CHECK constraints
    SQLAlchemy V4 isolés.
    """
    return  # no-op : neutralise l'autouse parent


@pytest.fixture(scope="function")
def v4_session():
    """SQLAlchemy session in-memory SQLite : stub `organisations` + 8 tables V4.

    Critère d'attention M2-2 #8 : :memory: (PAS DB prod).
    Function-scoped : chaque test démarre avec DB clean.

    M2-4.1 : crée le stub `organisations` + seede l'org `TEST_ORG_ID` pour
    satisfaire la FK `organisation_id` V4 (Integer FK · ADR-009 Option D)
    sous `PRAGMA foreign_keys=ON`.
    """
    # SQLite in-memory avec foreign keys ON (par défaut OFF en SQLite)
    engine = create_engine("sqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Stub `organisations` (cible des FK) puis les 8 tables V4 (bypass legacy).
    _org_stub_metadata.create_all(engine)
    Base.metadata.create_all(engine, tables=V4_TABLES)

    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()

    # Seed l'org de test : satisfait les FK organisation_id des 8 tables V4.
    session.execute(_organisations_stub.insert().values(id=TEST_ORG_ID))
    session.commit()

    yield session

    session.close()
    engine.dispose()
