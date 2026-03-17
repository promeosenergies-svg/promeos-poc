"""PROMEOS — Schemas Pydantic pour Conformité (compliance) et Tertiaire (EFA)."""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class RecomputeRequest(BaseModel):
    org_id: int = Field(gt=0)
    site_ids: Optional[List[int]] = None


class ComplianceFindingPatch(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|acknowledged|resolved|dismissed)$")
    assigned_to: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=2000)


class EfaCreateRequest(BaseModel):
    nom: str = Field(min_length=1, max_length=300)
    site_id: int = Field(gt=0)
    annee_reference: Optional[int] = Field(None, ge=2000, le=2050)
    surface_m2: Optional[float] = Field(None, ge=0, le=1_000_000)


class EfaUpdateRequest(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=300)
    annee_reference: Optional[int] = Field(None, ge=2000, le=2050)
    surface_m2: Optional[float] = Field(None, ge=0, le=1_000_000)
    statut: Optional[str] = Field(None, pattern="^(brouillon|publie|archive)$")
