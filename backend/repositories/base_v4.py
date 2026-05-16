"""M2-3.C — Base repository for V4 models (IS11 cardinal · fail-closed org-scoping).

Tout repository V4 DOIT hériter de `BaseRepositoryV4`. La classe enforce le
scoping org sur chaque query (SELECT/UPDATE/DELETE) et chaque INSERT (`create()`).

FAIL-CLOSED : chaque méthode appelle `current_org_id()` qui lève
`NoOrgContextError` si aucun contexte n'est peuplé. Impossible d'oublier le
scoping — contraste avec le legacy `iam_scope.py` (helpers oubliables).

╔═══════════════════════════════════════════════════════════════════════════╗
║ EXTENSION HIÉRARCHIQUE — ENTITÉ / PORTEFEUILLE / SITE (porte ouverte v4.x)  ║
╠═══════════════════════════════════════════════════════════════════════════╣
║ M2-3.C livre UNIQUEMENT le scope ORG (`organisation_id`). PROMEOS reste     ║
║ hiérarchique (Organisation → EntitéJuridique → Portefeuille → Site → ...).   ║
║ 90 % des objets V4 Action Center sont rattachés à `organisation_id`, donc   ║
║ ORG-only est le socle pragmatique. Mais les cas prestataire/site-scoped     ║
║ (un `resp_site` ne voit que son site) DOIVENT pouvoir s'ajouter proprement. ║
║                                                                             ║
║ DEUX mécanismes d'extension, en parallèle :                                 ║
║                                                                             ║
║ 1. `_scope_column` (class attr) — cas SIMPLE : un V4 model qui nomme sa     ║
║    colonne org différemment override juste cet attribut.                    ║
║       class FooRepo(BaseRepositoryV4[Foo]):                                 ║
║           model = Foo                                                       ║
║           _scope_column = "tenant_id"   # au lieu de organisation_id        ║
║                                                                             ║
║ 2. `_apply_scope(stmt)` (méthode override-able) — cas HIÉRARCHIQUE : une    ║
║    future sous-classe ajoute un filtre site/portefeuille SANS toucher la    ║
║    base. Exemple (NON codé en M2-3.C — illustration) :                      ║
║                                                                             ║
║       class SiteScopedRepositoryV4(BaseRepositoryV4[X]):                    ║
║           def _apply_scope(self, stmt):                                     ║
║               stmt = super()._apply_scope(stmt)        # org filter d'abord ║
║               site_ids = current_site_ids()            # futur ContextVar   ║
║               return stmt.where(self.model.site_id.in_(site_ids))           ║
║                                                                             ║
║ La base reste fermée à la modification, ouverte à l'extension (OCP).        ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from middleware.org_context import current_org_id

ModelT = TypeVar("ModelT")


class OrgScopeViolation(PermissionError):
    """Levée quand une opération d'écriture franchit une frontière org.

    Ex : `update()`/`delete()` sur un objet dont `organisation_id` ≠ contexte
    courant — tentative d'IDOR en écriture, refusée bruyamment.
    """


class BaseRepositoryV4(Generic[ModelT]):
    """Classe de base des repositories V4. Enforce le scoping org automatiquement.

    Usage :
        class ActionCenterItemRepository(BaseRepositoryV4[ActionCenterItem]):
            model = ActionCenterItem

        repo = ActionCenterItemRepository(db_session)
        items = repo.list_all()        # auto-filtré par current_org_id()
        item  = repo.get(item_id)      # None si l'item est dans une autre org

    Attributs de classe (override-ables — cf. extension hiérarchique docstring module) :
        model        : le model SQLAlchemy V4 (OBLIGATOIRE, set par la sous-classe)
        _scope_column: nom de la colonne de scope org (défaut "organisation_id")
    """

    model: type[ModelT]  # à définir par la sous-classe
    _scope_column: str = "organisation_id"  # override-able (cas simple)

    def __init__(self, db: Session):
        self.db = db
        if not hasattr(self, "model") or self.model is None:
            raise ValueError(f"{self.__class__.__name__} must define a 'model' class attribute")

    # ── Scope (override-able pour extension hiérarchique) ───────────────

    def _apply_scope(self, stmt):
        """Ajoute le filtre org-scoping à un statement SQLAlchemy 2.x.

        Méthode OVERRIDE-ABLE : une sous-classe hiérarchique (site/portefeuille)
        appelle `super()._apply_scope(stmt)` puis ajoute son propre filtre.
        Cf. docstring module §EXTENSION HIÉRARCHIQUE.

        FAIL-CLOSED : `current_org_id()` lève `NoOrgContextError` si pas de contexte.
        """
        org_id = current_org_id()
        scope_col = getattr(self.model, self._scope_column)
        return stmt.where(scope_col == org_id)

    def _assert_belongs_to_current_org(self, obj: ModelT) -> None:
        """Lève `OrgScopeViolation` si `obj` n'appartient pas à l'org courante.

        Comparaison en str (type-agnostic — int legacy / UUID V4).
        """
        expected = current_org_id()
        actual = getattr(obj, self._scope_column, None)
        if str(actual) != str(expected):
            raise OrgScopeViolation(
                f"{self.model.__name__}(id={getattr(obj, 'id', '?')}) "
                f"belongs to {self._scope_column}={actual!r}, "
                f"but current org context is {expected!r}"
            )

    # ── Read ────────────────────────────────────────────────────────────

    def list_all(self) -> list[ModelT]:
        """Liste toutes les rows de l'org courante. FAIL-CLOSED."""
        stmt = self._apply_scope(select(self.model))
        return list(self.db.execute(stmt).scalars().all())

    def get(self, obj_id: Any) -> Optional[ModelT]:
        """Récupère une row par id, scopée org. None si elle est dans une autre org.

        Retourne None (pas 403) sur cross-org → l'appelant route renvoie 404,
        évite la fuite d'existence (anti-énumération IDOR).
        """
        stmt = self._apply_scope(select(self.model).where(self.model.id == obj_id))
        return self.db.execute(stmt).scalar_one_or_none()

    # ── Write ───────────────────────────────────────────────────────────

    def create(self, **kwargs) -> ModelT:
        """Crée une row en FORÇANT `organisation_id = current_org_id()`.

        Tout `organisation_id` passé par l'appelant est OVERRIDÉ — defense in
        depth contre une route qui laisserait fuiter un paramètre du body.
        FAIL-CLOSED : lève si pas de contexte.
        """
        kwargs[self._scope_column] = current_org_id()
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.flush()  # populate id sans commit
        return obj

    def update(self, obj: ModelT, **kwargs) -> ModelT:
        """Met à jour une row. Lève `OrgScopeViolation` si cross-org.

        Le `organisation_id` ne peut JAMAIS être changé par un update (retiré
        des kwargs) — un objet ne migre pas d'org via update.
        """
        self._assert_belongs_to_current_org(obj)
        kwargs.pop(self._scope_column, None)  # jamais changer le scope
        for key, value in kwargs.items():
            setattr(obj, key, value)
        self.db.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        """Supprime une row. Lève `OrgScopeViolation` si cross-org."""
        self._assert_belongs_to_current_org(obj)
        self.db.delete(obj)
        self.db.flush()
