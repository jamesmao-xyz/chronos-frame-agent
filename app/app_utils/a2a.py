from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from fastapi import FastAPI
    from google.adk.agents import BaseAgent
    from google.adk.runners import Runner

try:
    from a2a.server.apps import A2AFastAPIApplication
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.types import AgentCapabilities
    from a2a.utils.constants import (
        AGENT_CARD_WELL_KNOWN_PATH,
        EXTENDED_AGENT_CARD_PATH,
    )
    from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
    from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder

    HAS_A2A = True
except Exception as e:
    HAS_A2A = False
    logger.warning(f"A2A modules unavailable: {e}")


def _default_capabilities() -> Any:
    """Returns the default A2A capabilities used by scaffolded projects."""
    if not HAS_A2A:
        return None
    return AgentCapabilities(
        streaming=True,
        extensions=[],
    )


async def attach_a2a_routes(
    app: FastAPI,
    *,
    agent: BaseAgent,
    runner: Runner,
    task_store: Any,
    rpc_path: str,
    capabilities: Any = None,
    agent_version: str | None = None,
    app_url: str | None = None,
) -> None:
    """Register A2A routes if A2A package is available."""
    if not HAS_A2A:
        logger.info("Skipping A2A route attachment (A2A server modules not installed).")
        return

    resolved_app_url = app_url or os.getenv("APP_URL", "http://0.0.0.0:8000")
    resolved_agent_version = agent_version or os.getenv("AGENT_VERSION", "0.1.0")
    resolved_capabilities = capabilities or _default_capabilities()

    agent_card = await AgentCardBuilder(
        agent=agent,
        capabilities=resolved_capabilities,
        rpc_url=f"{resolved_app_url}{rpc_path}",
        agent_version=resolved_agent_version,
    ).build()

    request_handler = DefaultRequestHandler(
        agent_executor=A2aAgentExecutor(runner=runner),
        task_store=task_store,
    )

    a2a_app = A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
    a2a_app.add_routes_to_app(
        app,
        agent_card_url=f"{rpc_path}{AGENT_CARD_WELL_KNOWN_PATH}",
        rpc_url=rpc_path,
        extended_agent_card_url=f"{rpc_path}{EXTENDED_AGENT_CARD_PATH}",
    )
