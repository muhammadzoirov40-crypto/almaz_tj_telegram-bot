from __future__ import annotations

from uuid import uuid4

import httpx

from app.config import settings
from app.constants.games import GAME_LABELS as _GAME_LABELS
from app.providers.base import AccountInfo, TopUpProvider, TopUpResult
from app.utils.logger import get_logger

logger = get_logger(__name__)

_API_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class MockTopUpProvider(TopUpProvider):
    """Development-only top-up provider.

    Simulates an authorized Free Fire top-up API. NEVER use in production.
    Does not require or store any Free Fire account password.
    """

    name = "mock"

    async def lookup_account(self, uid: str, game: str = "ff") -> AccountInfo:
        label = _GAME_LABELS.get(game, game.title())
        if not uid.isdigit() or len(uid) < 8:
            return AccountInfo(
                found=False,
                game=game,
                uid=uid,
                message="UID нодуруст аст.",
            )
        nickname = f"Player_{uid[-6:]}"
        logger.info(
            "Mock account lookup game=%s uid=%s nickname=%s", game, uid, nickname
        )
        return AccountInfo(
            found=True,
            nickname=nickname,
            game=label,
            uid=uid,
        )

    async def topup(
        self,
        uid: str,
        product: str,
        order_id: int,
    ) -> TopUpResult:
        reference = f"mocktop_{uuid4().hex[:16]}"
        logger.info(
            "Mock top-up order_id=%s uid=%s product=%s ref=%s",
            order_id,
            uid,
            product,
            reference,
        )
        # Simulate occasional failure for testing failure path:
        # fail if uid ends with "0000" (deterministic, documented)
        if uid.endswith("0000"):
            return TopUpResult(
                success=False,
                provider_reference=reference,
                message="Mock provider simulated failure",
            )
        return TopUpResult(
            success=True,
            provider_reference=reference,
            message="Mock top-up succeeded",
        )


_LOOKUP_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/141.0.0.0 Safari/537.36"
)
_FF_REGIONS = ("ind", "sg", "br", "ru", "id", "tw", "us", "vn", "th", "me", "pk")


def _extract_nickname(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    for key in (
        "nickname",
        "name",
        "player_name",
        "playerName",
        "AccountName",
        "account_name",
    ):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for nested_key in ("basicInfo", "basicinfo", "BasicInfo", "data", "player", "account"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            found = _extract_nickname(nested)
            if found:
                return found
    return ""


def _extract_region(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    for key in ("region", "server", "Region", "Server"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()
    for nested_key in ("basicInfo", "basicinfo", "BasicInfo", "data"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            found = _extract_region(nested)
            if found:
                return found
    return ""


class RealTopUpProvider(TopUpProvider):
    """Real, authorized Free Fire / game top-up API provider.

    Sends live requests to TOPUP_API_URL / FREE_FIRE_API_URL.
    Never asks for or stores Free Fire account passwords.
    """

    name = "real"

    def __init__(self, api_url: str | None = None, api_key: str | None = None) -> None:
        self.api_url = (api_url or settings.effective_topup_api_url).rstrip("/")
        self.api_key = api_key or settings.effective_topup_api_key
        if not self.api_url:
            raise RuntimeError(
                "TOPUP_PROVIDER=real requires FREE_FIRE_API_URL (or TOPUP_API_URL)"
            )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": _LOOKUP_UA,
        }
        if self.api_key:
            headers["x-api-key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers["Content-Type"] = "application/json"
        return headers

    def _is_ffc_lookup(self) -> bool:
        return "freefirecommunity.com" in self.api_url or self.api_url.endswith(
            "/api/v1/info"
        )

    async def _ffc_lookup(self, uid: str) -> httpx.Response:
        region = "ind"
        params: dict[str, str] = {"region": region, "uid": uid}
        if self.api_key:
            params["key"] = self.api_key
        async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
            return await client.get(
                self.api_url,
                params=params,
                headers={
                    "Accept": "application/json",
                    "User-Agent": _LOOKUP_UA,
                    **({"x-api-key": self.api_key} if self.api_key else {}),
                },
            )

    async def _free_ff_lookup(self, uid: str, region: str = "IND") -> dict | None:
        url = "https://epep-api.vercel.app/api/freefire/player/profile"
        params = {
            "server": region,
            "uid": uid,
            "need_gallery_info": "false",
            "call_sign_src": "7",
        }
        async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
            response = await client.get(
                url,
                params=params,
                headers={"Accept": "application/json", "User-Agent": _LOOKUP_UA},
            )
            response.raise_for_status()
            data = response.json()
        if isinstance(data, dict):
            return data
        return None

    async def _lookup_ff_nickname(self, uid: str, label: str) -> AccountInfo | None:
        """Try FFC first (needs key), then free epep API. None = hard fail."""
        ffc_error: str | None = None
        if self.api_key or not self._is_ffc_lookup():
            try:
                if self._is_ffc_lookup():
                    response = await self._ffc_lookup(uid)
                else:
                    payload = {"player_id": uid, "game": "ff"}
                    async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                        response = await client.post(
                            self.api_url,
                            json=payload,
                            headers=self._headers(),
                        )
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict):
                    exists = data.get("exists", data.get("found", True))
                    nickname = _extract_nickname(data)
                    region = _extract_region(data)
                    display = f"{label} ({region})" if region else label
                    if exists is False:
                        return AccountInfo(
                            found=False,
                            game=display,
                            uid=uid,
                            message=str(
                                data.get("error")
                                or data.get("message")
                                or "ID ёфт нашуд."
                            ),
                        )
                    if nickname:
                        logger.info(
                            "FF lookup ok via primary uid=%s nickname=%s",
                            uid,
                            nickname,
                        )
                        return AccountInfo(
                            found=True,
                            nickname=nickname,
                            game=display,
                            uid=uid,
                        )
            except httpx.HTTPStatusError as exc:
                ffc_error = f"HTTP {exc.response.status_code}"
                logger.warning(
                    "Primary FF lookup failed uid=%s status=%s",
                    uid,
                    exc.response.status_code,
                )
            except httpx.HTTPError as exc:
                ffc_error = type(exc).__name__
                logger.warning(
                    "Primary FF lookup network error uid=%s err=%s",
                    uid,
                    exc,
                )

        # Free fallback (no API key needed) — Free Fire only.
        try:
            free_data = await self._free_ff_lookup(uid, region="IND")
            if free_data is None:
                return None
            nickname = _extract_nickname(free_data)
            region = _extract_region(free_data)
            display = f"{label} ({region})" if region else label
            if nickname:
                logger.info(
                    "FF lookup ok via free uid=%s nickname=%s", uid, nickname
                )
                return AccountInfo(
                    found=True,
                    nickname=nickname,
                    game=display,
                    uid=uid,
                )
            # try other common regions
            for alt in ("SG", "BR", "US", "ID", "RU"):
                try:
                    free_data = await self._free_ff_lookup(uid, region=alt)
                except httpx.HTTPError:
                    continue
                if not free_data:
                    continue
                nickname = _extract_nickname(free_data)
                if nickname:
                    logger.info(
                        "FF lookup ok via free uid=%s region=%s nickname=%s",
                        uid,
                        alt,
                        nickname,
                    )
                    return AccountInfo(
                        found=True,
                        nickname=nickname,
                        game=f"{label} ({alt})",
                        uid=uid,
                    )
            return AccountInfo(
                found=True,
                nickname="",
                game=label,
                uid=uid,
                message="Ном ёфт нашуд. Бе санҷиш ID-ро идома диҳед.",
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "Free FF lookup failed uid=%s err=%s primary=%s",
                uid,
                exc,
                ffc_error,
            )
            return AccountInfo(
                found=True,
                nickname="",
                game=label,
                uid=uid,
                message="Ном санҷида нашуд. Бе санҷиш ID-ро идома диҳед.",
            )

    async def lookup_account(self, uid: str, game: str = "ff") -> AccountInfo:
        label = _GAME_LABELS.get(game, game.title())
        if not uid.isdigit() or len(uid) < 8:
            return AccountInfo(
                found=False,
                game=game,
                uid=uid,
                message="UID нодуруст аст.",
            )

        if game == "ff":
            result = await self._lookup_ff_nickname(uid, label)
            if result is not None:
                return result

        # Non-FF games or hard failure on custom endpoint.
        try:
            if self._is_ffc_lookup():
                response = await self._ffc_lookup(uid)
            else:
                payload = {"player_id": uid, "game": game}
                async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                    response = await client.post(
                        self.api_url,
                        json=payload,
                        headers=self._headers(),
                    )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning(
                "Real lookup HTTP error uid=%s game=%s status=%s",
                uid,
                game,
                status,
            )
            # API auth/rate-limit issues: do not block the order flow.
            if status in {401, 402, 403, 429, 500, 502, 503, 504}:
                return AccountInfo(
                    found=True,
                    nickname="",
                    game=label,
                    uid=uid,
                    message="Ном санҷида нашуд. Бе санҷиш ID-ро идома диҳед.",
                )
            return AccountInfo(
                found=False,
                game=label,
                uid=uid,
                message=f"Хатогии API ({status}).",
            )
        except httpx.HTTPError as exc:
            logger.exception("Real lookup failed uid=%s game=%s", uid, game)
            return AccountInfo(
                found=True,
                nickname="",
                game=label,
                uid=uid,
                message=(
                    "Хатогии пайвастшавӣ. Бе санҷиш ID-ро идома диҳед."
                ),
            )

        if not isinstance(data, dict):
            return AccountInfo(
                found=True,
                nickname="",
                game=label,
                uid=uid,
                message="API ҷавоби нодуруст дод. Бе санҷиш ID-ро идома диҳед.",
            )

        exists = data.get("exists", data.get("found", True))
        nickname = _extract_nickname(data)
        region = _extract_region(data)
        display_game = label
        if region and game == "ff":
            display_game = f"{label} ({region})"

        if exists is False:
            err = str(data.get("error") or data.get("message") or "ID ёфт нашуд.")
            return AccountInfo(
                found=False,
                game=display_game,
                uid=uid,
                message=err,
            )

        if not nickname:
            return AccountInfo(
                found=True,
                nickname="",
                game=display_game,
                uid=uid,
                message="Лақаб ёфт нашуд. Бе санҷиш ID-ро идома диҳед.",
            )

        logger.info(
            "Real account lookup ok game=%s uid=%s nickname=%s",
            game,
            uid,
            nickname,
        )
        return AccountInfo(
            found=True,
            nickname=nickname,
            game=display_game,
            uid=uid,
        )

    def _topup_url(self) -> str:
        # If FREE_FIRE_API_URL already points to /topup, use as-is.
        base = self.api_url.rstrip("/")
        if base.endswith("/topup"):
            return base
        if base.endswith("/lookup"):
            return base[: -len("/lookup")] + "/topup"
        return f"{base}/topup"

    async def topup(
        self,
        uid: str,
        product: str,
        order_id: int,
    ) -> TopUpResult:
        reference = f"realtop_{order_id}_{uuid4().hex[:8]}"
        if not self.api_key:
            return TopUpResult(
                success=False,
                provider_reference=reference,
                message="Калиди API ворид нашудааст (FREE_FIRE_API_KEY).",
            )
        payload = {
            "player_id": uid,
            "product": product,
            "order_id": order_id,
            "reference": reference,
        }
        try:
            async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                response = await client.post(
                    self._topup_url(),
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Real top-up HTTP error order_id=%s status=%s",
                order_id,
                exc.response.status_code,
            )
            return TopUpResult(
                success=False,
                provider_reference=reference,
                message=f"API xatosi ({exc.response.status_code})",
            )
        except httpx.HTTPError as exc:
            logger.exception("Real top-up failed order_id=%s", order_id)
            return TopUpResult(
                success=False,
                provider_reference=reference,
                message=f"Хатогии пайвастшавӣ: {exc.__class__.__name__}",
            )

        if not isinstance(data, dict):
            return TopUpResult(
                success=False,
                provider_reference=reference,
                message="API ҷавоби нодуруст дод",
            )

        success = bool(
            data.get(
                "success",
                data.get("exists", data.get("status") in {"ok", "completed", "success"}),
            )
        )
        remote_ref = str(
            data.get("reference") or data.get("transaction_id") or reference
        )
        message = str(data.get("message") or data.get("error") or ("OK" if success else "Failed"))
        logger.info(
            "Real top-up order_id=%s success=%s ref=%s",
            order_id,
            success,
            remote_ref,
        )
        return TopUpResult(
            success=success,
            provider_reference=remote_ref,
            message=message,
            raw=data,
        )

    async def close(self) -> None:
        return None
