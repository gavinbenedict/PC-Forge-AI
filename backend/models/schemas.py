"""
PCForge AI — Pydantic Schemas
All request/response models with full validation.
"""
from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator
from datetime import datetime


# ─── Enums / Literals ────────────────────────────────────────────────────────

UsageType = Literal["gaming", "streaming", "editing", "workstation", "mixed", "office"]
Region = Literal["US", "EU", "UK", "IN", "CA", "AU"]
PriceSource = Literal["live", "simulated", "predicted"]
CompatibilityStatus = Literal["valid", "warning", "invalid"]
BuildTier = Literal["budget", "mid-range", "high-end", "enthusiast"]


# ─── Input Schemas ────────────────────────────────────────────────────────────

class RAMSpec(BaseModel):
    size_gb: Optional[int] = Field(None, description="Total RAM in GB (e.g. 16, 32, 64)")
    type: Optional[str] = Field(None, description="e.g. DDR4, DDR5")
    speed_mhz: Optional[int] = Field(None, description="e.g. 3200, 4800, 6000")
    modules: Optional[int] = Field(None, description="Number of sticks (e.g. 2, 4)")


class StorageSpec(BaseModel):
    type: Optional[str] = Field(None, description="NVMe, SATA SSD, HDD")
    capacity_gb: Optional[int] = Field(None, description="Capacity in GB")
    interface: Optional[str] = Field(None, description="M.2 NVMe, SATA, PCIe 5.0")


class BuildSpec(BaseModel):
    """User-provided (possibly partial) PC specification."""
    
    # Core components (all optional to handle partial input)
    cpu: Optional[str] = Field(None, example="AMD Ryzen 9 7950X")
    gpu: Optional[str] = Field(None, example="NVIDIA RTX 4090")
    motherboard: Optional[str] = Field(None, example="ASUS ROG Crosshair X670E")
    ram: Optional[RAMSpec] = Field(None)
    storage: Optional[List[StorageSpec]] = Field(None)
    psu: Optional[str] = Field(None, example="Corsair RM1000x 1000W")
    case: Optional[str] = Field(None, example="Lian Li PC-O11 Dynamic")
    cooler: Optional[str] = Field(None, description="CPU cooler model")
    monitor: Optional[str] = Field(None, description="Optional monitor spec")
    
    # Build preferences
    budget_usd: Optional[float] = Field(None, ge=0, description="Total budget in USD")
    preferred_brand: Optional[str] = Field(None, description="e.g. ASUS, Corsair, Samsung")
    usage_type: Optional[UsageType] = Field(None)
    region: Region = Field(default="US")
    
    @model_validator(mode="after")
    def at_least_one_component(self) -> "BuildSpec":
        components = [self.cpu, self.gpu, self.motherboard, self.ram, 
                      self.storage, self.psu, self.case, self.cooler]
        if not any(c is not None for c in components):
            raise ValueError("At least one component must be specified.")
        return self


# ─── Pricing Schemas ─────────────────────────────────────────────────────────

class PricedPart(BaseModel):
    category: str
    brand: str
    model: str
    price_usd: float
    currency: str = "USD"
    store: str
    availability: str  # "In Stock", "Limited", "Out of Stock"
    url: str
    last_updated: datetime
    source: PriceSource
    predicted_range: Optional[PriceRange] = None


class PriceRange(BaseModel):
    min_price: float
    average_price: float
    max_price: float


# Self-reference fix
PricedPart.model_rebuild()


# ─── Compatibility Schemas ────────────────────────────────────────────────────

class CompatibilityIssue(BaseModel):
    severity: Literal["error", "warning", "info"]
    component: str
    issue: str
    suggested_fix: str


class CompatibilityReport(BaseModel):
    status: CompatibilityStatus
    issues: List[CompatibilityIssue] = []
    passed_checks: List[str] = []
    total_checks: int = 0


# ─── Recommendation Schemas ───────────────────────────────────────────────────

class RecommendedPart(BaseModel):
    category: str
    model: str
    brand: str
    reasoning: str
    price_usd: float
    compatibility_score: float = Field(ge=0.0, le=1.0)
    is_auto_filled: bool = True


class AlternativeOption(BaseModel):
    model: str
    brand: str
    price_usd: float
    notes: str


class RecommendationResult(BaseModel):
    recommended_parts: List[RecommendedPart] = []
    alternatives: Dict[str, List[AlternativeOption]] = {}
    inferred_tier: BuildTier
    tier_reasoning: str


# ─── Full Component (internal, resolved) ─────────────────────────────────────

class ResolvedComponent(BaseModel):
    category: str
    brand: str
    model: str
    specs: Dict[str, Any] = {}
    is_auto_filled: bool = False
    priced: Optional[PricedPart] = None


# ─── Response Schema ──────────────────────────────────────────────────────────

class PriceSummary(BaseModel):
    total_live_usd: float
    total_predicted_usd: float
    total_combined_usd: float
    market_range: PriceRange
    live_parts_count: int
    predicted_parts_count: int
    currency: str = "USD"
    region: str = "US"


class AnalyzeResponse(BaseModel):
    """Full analysis response returned by /analyze-build."""
    
    build_id: str
    timestamp: datetime
    
    # Completed build spec
    original_input: Dict[str, Any]
    completed_build: List[ResolvedComponent]
    auto_filled_components: List[str]
    
    # Reports
    compatibility: CompatibilityReport
    recommendations: RecommendationResult
    
    # Pricing
    pricing: List[PricedPart]
    price_summary: PriceSummary
    
    # Meta
    notes: List[str] = []
    inferred_tier: BuildTier
    usage_type: Optional[UsageType] = None


# ─── Export Request ───────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    """Inline payload for export endpoints."""
    analysis: AnalyzeResponse
    format: Literal["csv", "excel"] = "excel"
