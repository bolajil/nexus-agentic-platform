"""
NEXUS Platform — Pydantic v2 Data Models
All request/response schemas and internal state models.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enumerations ────────────────────────────────────────────────────────────

class AgentName(str, Enum):
    REQUIREMENTS = "requirements"
    RESEARCH = "research"
    DESIGN = "design"
    SIMULATION = "simulation"
    OPTIMIZATION = "optimization"
    REPORT = "report"


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class SSEEventType(str, Enum):
    AGENT_START = "agent_start"
    AGENT_THOUGHT = "agent_thought"
    AGENT_COMPLETE = "agent_complete"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    SESSION_COMPLETE = "session_complete"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


# ── Provenance ───────────────────────────────────────────────────────────────

class ProvenanceEntry(BaseModel):
    """Audit trail entry for a single agent execution."""

    agent_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    input_summary: str
    output_summary: str
    tools_used: list[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    duration_ms: Optional[float] = None
    token_usage: Optional[dict[str, int]] = None


# ── Engineering Domain Models ─────────────────────────────────────────────────

class EngineeringRequirements(BaseModel):
    """Parsed engineering requirements from the Requirements Agent."""

    domain: str = Field(description="Engineering domain: heat_transfer|propulsion|structural|electronics_cooling")
    primary_objective: str
    constraints: list[str] = Field(default_factory=list)
    performance_targets: dict[str, Any] = Field(default_factory=dict)
    materials: list[str] = Field(default_factory=list)
    operating_conditions: dict[str, Any] = Field(default_factory=dict)
    raw_brief: str


class ResearchResult(BaseModel):
    """Results from the Research Agent RAG search."""

    query_used: str
    retrieved_documents: list[dict[str, Any]] = Field(default_factory=list)
    relevant_formulas: list[str] = Field(default_factory=list)
    recommended_approaches: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    summary: str


class DesignParameters(BaseModel):
    """Calculated design parameters from the Design Agent."""

    primary_parameters: dict[str, float] = Field(default_factory=dict)
    secondary_parameters: dict[str, float] = Field(default_factory=dict)
    units: dict[str, str] = Field(default_factory=dict)
    design_equations_used: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    feasibility_assessment: str


class SimulationResult(BaseModel):
    """Output from the Simulation Agent physics engine."""

    simulation_type: str
    input_parameters: dict[str, float] = Field(default_factory=dict)
    output_metrics: dict[str, float] = Field(default_factory=dict)
    performance_score: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)
    raw_data: dict[str, Any] = Field(default_factory=dict)


class OptimizedParameters(BaseModel):
    """Multi-objective optimized design from the Optimization Agent."""

    original_params: dict[str, float] = Field(default_factory=dict)
    optimized_params: dict[str, float] = Field(default_factory=dict)
    improvement_metrics: dict[str, float] = Field(default_factory=dict)
    optimization_method: str
    iterations: int
    pareto_front: list[dict[str, float]] = Field(default_factory=list)
    recommendation: str


class EngineeringReport(BaseModel):
    """Final compiled engineering report."""

    title: str
    executive_summary: str
    requirements_section: str
    research_findings: str
    design_solution: str
    simulation_results: str
    optimization_results: str
    conclusions: str
    recommendations: list[str] = Field(default_factory=list)
    appendix: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ── Session Models ────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    """Request to create a new NEXUS engineering session."""

    engineering_brief: str = Field(
        min_length=20,
        max_length=5000,
        description="The engineering challenge description",
    )
    session_name: Optional[str] = None


class Session(BaseModel):
    """Full session model stored in Redis."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    engineering_brief: str
    status: SessionStatus = SessionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    requirements: Optional[EngineeringRequirements] = None
    research_results: Optional[ResearchResult] = None
    design_params: Optional[DesignParameters] = None
    simulation_results: Optional[SimulationResult] = None
    optimized_params: Optional[OptimizedParameters] = None
    report: Optional[EngineeringReport] = None
    provenance_chain: list[ProvenanceEntry] = Field(default_factory=list)
    error: Optional[str] = None
    total_duration_ms: Optional[float] = None


class SessionSummary(BaseModel):
    """Lightweight session summary for list views."""

    id: str
    name: str
    status: SessionStatus
    created_at: datetime
    domain: Optional[str] = None
    brief_excerpt: str


# ── SSE Event Models ──────────────────────────────────────────────────────────

class SSEEvent(BaseModel):
    """Server-Sent Event payload."""

    type: SSEEventType
    agent: Optional[str] = None
    content: Any = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Knowledge Base Models ─────────────────────────────────────────────────────

class DocumentIngestion(BaseModel):
    """Request to add a document to the knowledge base."""

    title: str
    content: str
    domain: str
    source: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeStats(BaseModel):
    """Knowledge base statistics."""

    total_documents: int
    collections: list[str]
    domains: list[str]
    last_updated: Optional[datetime] = None


# ── Human Feedback / Grader Models ───────────────────────────────────────────

class FeedbackScore(int, Enum):
    """Human feedback score (thumbs up/down)."""
    THUMBS_DOWN = 0
    THUMBS_UP = 1


class FeedbackCreate(BaseModel):
    """Request to submit human feedback on a session or agent output."""
    
    session_id: str = Field(description="Session ID to provide feedback on")
    score: FeedbackScore = Field(description="1 = thumbs up, 0 = thumbs down")
    agent_name: Optional[str] = Field(default=None, description="Specific agent to rate (optional)")
    comment: Optional[str] = Field(default=None, description="Optional text feedback")
    user_id: Optional[str] = Field(default=None, description="User providing feedback")


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    score: FeedbackScore
    agent_name: Optional[str] = None
    comment: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    langfuse_score_id: Optional[str] = Field(default=None, description="Langfuse score ID if synced")


class FeedbackStats(BaseModel):
    """Aggregated feedback statistics."""
    
    total_feedback: int = 0
    thumbs_up: int = 0
    thumbs_down: int = 0
    approval_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    by_agent: dict[str, dict[str, int]] = Field(default_factory=dict)
