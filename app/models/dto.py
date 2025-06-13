from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, StrictBool


class PackCreateRequest(BaseModel):
    # Metadata
    name: str
    description: Optional[str] = None
    category_id: Optional[str] = None
    coin_price: Optional[int] = None
    premium_price: Optional[int] = None
    is_free: Optional[StrictBool] = None
    is_starter_pack: Optional[StrictBool] = None
    is_premium: Optional[StrictBool] = None
    rarity: Optional[str] = Field(default="common")
    tags: Optional[List[str]] = None
    sort_order: Optional[int] = None

    # Files (raw bytes + original names)
    preview_image: bytes
    preview_image_name: str
    waiting_image: bytes
    waiting_image_name: str
    action_image: bytes
    action_image_name: str

    sound_idle: bytes
    sound_idle_name: str
    sound_action: bytes
    sound_action_name: str
    sound_bonus: bytes
    sound_bonus_name: str

    model_config = {"arbitrary_types_allowed": True}


class SoundRecordCreate(BaseModel):
    pack_id: str
    file_url: str
    sort_order: int


class PackCreateResult(BaseModel):
    id: str
    preview_image_url: str
    waiting_image_url: str
    action_image_url: str
    sound_urls: List[str]
