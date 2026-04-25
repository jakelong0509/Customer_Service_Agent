from pydantic import Field
from src.core.agent_state import AgentState
from pydantic import BaseModel
from typing import Any


class NormalizedText(BaseModel):
    normalized_text: str = ""


class ExtractedEntity(BaseModel):
    entity_text: str
    entity_type: str
    entity_med_info: dict[str, Any] = Field(default_factory=dict)


class ExtractedEntities(BaseModel):
    extracted_entities: list[ExtractedEntity] = Field(default_factory=list)


class MappingResult(BaseModel):
    anchor_text: str = ""
    rxcui: str = ""
    str: str = ""
    tty: str = ""
    similarity_score: float = 0.0
    resolution_strategy: str = ""
    resolution_path: str = ""
    confidence_score: float = 0.0


class NDCResult(BaseModel):
    atn: str
    atv: str


class MappingResults(BaseModel):
    mapping_results: list[MappingResult] = Field(default_factory=list)
    ndc_results: list[NDCResult] = Field(default_factory=list)


class ValidationResult(BaseModel):
    all_confident: bool = True
    low_confidence_entities: list[str] = Field(default_factory=list)
    warning_message: str = ""


class RxNormAgentState(AgentState):
    """State for the RxNorm mapping agent.

    Extends base state with intermediate pipeline results so each step
    (normalize -> extract -> map) can store its output for the next step,
    rather than re-parsing tool responses from message history.
    """
    normalized_text: NormalizedText = Field(default_factory=NormalizedText)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    mapping_results: MappingResults = Field(default_factory=MappingResults)
    validation: ValidationResult = Field(default_factory=ValidationResult)
