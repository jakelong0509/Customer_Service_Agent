from pydantic import Field
from src.core.agent_state import AgentState
from pydantic import BaseModel

class NormalizedText(BaseModel):
    normalized_text: str

class ExtractedEntity(BaseModel):
    entity_text: str
    entity_type: str
    entity_med_info: dict

class ExtractedEntities(BaseModel):
    extracted_entities: list[ExtractedEntity]

class MappingResult(BaseModel):
    rxcui: str
    str: str
    tty: str
    similarity_score: float

class NDCResult(BaseModel):
    atn: str
    atv: str

class MappingResults(BaseModel):
    mapping_results: list[MappingResult]
    ndc_results: list[NDCResult]

class RxNormAgentState(AgentState):
    """State for the RxNorm mapping agent.

    Extends base state with intermediate pipeline results so each step
    (normalize → extract → map) can store its output for the next step,
    rather than re-parsing tool responses from message history.
    """
    normalized_text: NormalizedText = Field(default_factory=NormalizedText)
    extracted_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    mapping_results: MappingResults = Field(default_factory=MappingResults)
