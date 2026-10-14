"""Best-effort Discord message operations with one explicit rate-limit retry."""

import asyncio
import logging
from typing import Any

import discord

log = logging.getLogger(__name__)


async def _call(operation: str, target: Any, **kwargs: Any) -> tuple[bool, Any | None]:
    identifier = getattr(target, "id", "unknown")
    for attempt in range(2):
        try:
            return True, await getattr(target, operation)(**kwargs)
        except discord.Forbidden as exc:
            log.warning("Discord %s forbidden for %s (status %s)", operation, identifier, exc.status)
            return False, None
        except discord.HTTPException as exc:
            log.warning("Discord %s failed for %s (status %s)", operation, identifier, exc.status)
            if exc.status != 429 or attempt:
                return False, None
            await asyncio.sleep(float(getattr(exc, "retry_after", 1) or 1))
    return False, None


async def safe_send(channel: Any, **kwargs: Any) -> discord.Message | None:
    return (await _call("send", channel, **kwargs))[1]


async def safe_edit(message: Any, **kwargs: Any) -> bool:
    return (await _call("edit", message, **kwargs))[0]


async def safe_reply(message: Any, **kwargs: Any) -> discord.Message | None:
    return (await _call("reply", message, **kwargs))[1]


async def safe_delete(message: Any) -> bool:
    return (await _call("delete", message))[0]
