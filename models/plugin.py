from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PluginType(str, Enum):
    generator = "generator"
    effect = "effect"
    unknown = "unknown"


class Plugin(BaseModel):
    name: str = Field(..., description="Plugin display name")
    vendor: Optional[str] = Field(None, description="Vendor / manufacturer")
    type: PluginType = Field(..., description="Generator (instrument) or Effect")
    path: Optional[str] = Field(None, description="Path to the .dll / .vst3 file")
    nfo_path: Optional[str] = Field(None, description="Path to the .nfo descriptor file")

    # Populated by research_plugin
    synthesis_type: Optional[str] = Field(None, description="e.g. subtractive, wavetable, FM")
    recommended_genres: list[str] = Field(default_factory=list)
    sound_types: list[str] = Field(default_factory=list, description="bass, lead, pad, pluck…")
    description: Optional[str] = Field(None)
    useful_links: list[str] = Field(default_factory=list)
    researched: bool = Field(False, description="Whether online research has been done")

    model_config = {"use_enum_values": True}
