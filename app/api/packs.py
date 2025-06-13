from __future__ import annotations

import asyncio
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.dto import PackCreateRequest, PackCreateResult
from app.services.pack_creator import PackCreatorService

router = APIRouter(prefix="/packs", tags=["packs"])
