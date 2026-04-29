from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SampleType(str, Enum):
    kick = "kick"
    snare = "snare"
    hihat_closed = "hihat_closed"
    hihat_open = "hihat_open"
    clap = "clap"
    tom = "tom"
    crash = "crash"
    ride = "ride"
    percussion = "percussion"
    s808 = "808"
    fx = "fx"
    loop = "loop"
    one_shot = "one_shot"
    vocal = "vocal"
    other = "other"


class Sample(BaseModel):
    path: str = Field(..., description="Absolute path to the audio file")
    filename: str = Field(..., description="Filename without directory")
    type: SampleType = Field(..., description="Classified sample type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classifier confidence (0-1)")
    duration: float = Field(..., ge=0.0, description="Duration in seconds")
    bpm: Optional[float] = Field(None, description="Estimated BPM (for loops)")
    brightness: float = Field(..., description="Spectral centroid in Hz (proxy for brightness)")
    rms: float = Field(..., description="Root mean square energy")
    extension: str = Field(..., description="File extension (.wav, .mp3, etc.)")

    model_config = {"use_enum_values": True}
