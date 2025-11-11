from __future__ import annotations

import httpx
import structlog
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.config import settings


class DailySAO:
    """Service Access Object for Daily.co REST APIs."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        request_timeout: float = 10.0,
    ) -> None:
        self._base_url = (base_url or settings.daily_api_base_url).rstrip("/")
        self._api_key = api_key or settings.daily_api_key
        self._timeout = request_timeout
        self._logger = structlog.get_logger().bind(component="DailySAO")

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def api_key(self) -> str:
        return self._api_key

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RuntimeError("Daily API key is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_room(
        self,
        room_name: str,
        expires_at: datetime,
        privacy: str = "private",
    ) -> Dict[str, Any]:
        """
        Create a Daily.co room. If the room already exists, return the existing configuration.
        """
        payload = {
            "name": room_name,
            "privacy": privacy,
            "properties": {
                "exp": int(expires_at.timestamp()),
            },
        }

        url = "/rooms"
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout,
        ) as client:
            response = await client.post(url, json=payload, headers=self._headers())

            if response.status_code == httpx.codes.CONFLICT:
                self._logger.info(
                    "Daily room already exists, fetching existing configuration",
                    room_name=room_name,
                )
                return await self.get_room(room_name)

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                self._logger.error(
                    "Failed to create Daily room",
                    room_name=room_name,
                    status_code=exc.response.status_code,
                    response_body=exc.response.text,
                )
                raise

            return response.json()

    async def get_room(self, room_name: str) -> Dict[str, Any]:
        """Fetch an existing Daily.co room."""
        url = f"/rooms/{room_name}"
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout,
        ) as client:
            response = await client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    async def create_meeting_token(
        self,
        room_name: str,
        user_id: str,
        expires_at: datetime,
        is_owner: bool = False,
    ) -> Dict[str, Any]:
        """Create a Daily.co meeting token for the given room."""
        payload = {
            "properties": {
                "room_name": room_name,
                "is_owner": is_owner,
                "user_name": user_id,
                "exp": int(expires_at.timestamp()),
            }
        }

        url = "/meeting-tokens"
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self._timeout,
        ) as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()


daily_sao = DailySAO()

