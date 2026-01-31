"""Metadata CRUD endpoints."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()


class MetadataEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    key: str = Field(description="Unique metadata key")
    value: Any = Field(description="Metadata value (JSON)")
    version: int = Field(default=1, description="Version number")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CreateMetadataRequest(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    value: Any


class UpdateMetadataRequest(BaseModel):
    value: Any


# In-memory storage for development
_metadata_store: dict[str, MetadataEntry] = {}


@router.post("", response_model=MetadataEntry, status_code=status.HTTP_201_CREATED)
async def create_metadata(request: CreateMetadataRequest) -> MetadataEntry:
    if request.key in _metadata_store:
        raise HTTPException(status_code=409, detail=f"Key '{request.key}' already exists")
    
    entry = MetadataEntry(key=request.key, value=request.value)
    _metadata_store[request.key] = entry
    return entry


@router.get("", response_model=list[MetadataEntry])
async def list_metadata() -> list[MetadataEntry]:
    return list(_metadata_store.values())


@router.get("/{key}", response_model=MetadataEntry)
async def get_metadata(key: str) -> MetadataEntry:
    if key not in _metadata_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    return _metadata_store[key]


@router.put("/{key}", response_model=MetadataEntry)
async def update_metadata(key: str, request: UpdateMetadataRequest) -> MetadataEntry:
    if key not in _metadata_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    
    entry = _metadata_store[key]
    entry.value = request.value
    entry.version += 1
    entry.updated_at = datetime.now(timezone.utc)
    return entry


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_metadata(key: str) -> None:
    if key not in _metadata_store:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    del _metadata_store[key]
