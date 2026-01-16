from typing import List, Literal, Optional, get_args
from pydantic import BaseModel, Field

# Level 1 Required Enum + Necessary Extensions
RelationshipType = Literal[
    "founder", "ceo", "employee", "investor", "competitor", 
    "parentCompany", "subsidiary", "partner", "acquiredBy", 
    "boardMember", "advisor", "alumniOf", "affiliation",
    "opponent", "productOf", "creatorOf", "other"
]

ALLOWED_RELATIONS = ", ".join(get_args(RelationshipType))


class Entity(BaseModel):
    raw_name: str = Field(..., description="Exact name used in text (e.g., 'Sama', 'The Zuck')")
    canonical_name: str = Field(..., description="Formalized entity name (e.g., 'Sam Altman', 'Mark Zuckerberg')")


class Triplet(BaseModel):
    subject: Entity
    relationship: RelationshipType
    object: Entity
    evidence: str = Field(..., description="The specific phrase in the post that justifies this relationship.")
    suggested_relationship_evidence: Optional[str] = Field(..., description="justification for new suggested relationship, if relationship is of the type 'other'.")
    suggested_relationship: Optional[str] = Field(..., description="A new relationship type suggested by the LLM, if any.")


class PostAnalysis(BaseModel):
    has_business_info: bool = Field(..., description="Set to False if the post is just opinions/rants without hard relationships.")
    justification: Optional[str] = Field(..., description="Briefly explain why this post contains (or lacks) valid business triplets.")
    triplets: List[Triplet] = Field(default_factory=list)
    post_id: str = Field(..., description="The unique identifier of the Reddit post analyzed.")
    post_url: str = Field(None, description="The URL of the Reddit post.")


class BatchExtraction(BaseModel):
    results: List[PostAnalysis]


# Entity Resolution Models
class EntityGroup(BaseModel):
    master_name: str = Field(..., description="The canonical master name for this group of entities.")
    variants: List[str] = Field(..., description="List of entity names that refer to the same real-world entity.")


class EntityResolutionResult(BaseModel):
    groups: List[EntityGroup] = Field(..., description="List of entity groups, each with a master name and its variants.")


# Resolved Triplet Models for persistence
class ResolvedTriplet(BaseModel):
    subject: str = Field(..., description="The resolved canonical name of the subject entity.")
    relationship: RelationshipType
    object: str = Field(..., description="The resolved canonical name of the object entity.")
    evidence: str = Field(..., description="The specific phrase in the post that justifies this relationship.")


class ResolvedPostAnalysis(BaseModel):
    triplets: List[ResolvedTriplet]
    post_id: str
    post_url: Optional[str]
    justification: Optional[str]
