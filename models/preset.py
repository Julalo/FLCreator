from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Preset(BaseModel):
    name: str = Field(..., description="Preset display name")
    plugin_name: str = Field(..., description="Plugin this preset targets")
    source: str = Field(..., description="Website / source name")
    url: Optional[str] = Field(None, description="Direct download or page URL")
    description: Optional[str] = Field(None)
    genre_tags: list[str] = Field(default_factory=list)
    sound_type: Optional[str] = Field(None, description="bass, lead, pad, pluck, etc.")
    free: bool = Field(True)
    local_path: Optional[str] = Field(None, description="Path after installation")
    installed: bool = Field(False)
