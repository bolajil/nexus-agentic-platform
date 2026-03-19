"""
NEXUS Platform — LLM Factory
=============================
Centralised constructor for ChatOpenAI instances.
Automatically attaches Langfuse tracing callbacks when configured.

Compatible with langfuse 3.x:
  - LangChain callback is at langfuse.langchain.CallbackHandler
  - Session/user tracking via session_id and user_id params

Usage in any agent:
    from app.core.llm_factory import create_llm, get_callbacks

    llm = create_llm(config)
    cb  = get_callbacks(config, session_id, trace_name="requirements_agent")
    response = await llm.ainvoke(messages, config={"callbacks": cb})
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from app.core.config import Settings

logger = logging.getLogger(__name__)

# Module-level cached Langfuse client
_langfuse_client = None


def get_langfuse_client(config: "Settings"):
    return _get_langfuse_client(config)


def _get_langfuse_client(config: "Settings"):
    global _langfuse_client
    if _langfuse_client is not None:
        return _langfuse_client

    pk = getattr(config, 'LANGFUSE_PUBLIC_KEY', None)
    sk = getattr(config, 'LANGFUSE_SECRET_KEY', None)
    if not (pk and sk):
        return None

    try:
        from langfuse import Langfuse  # type: ignore
        _langfuse_client = Langfuse(
            public_key=pk,
            secret_key=sk,
            host=getattr(config, 'LANGFUSE_HOST', 'https://cloud.langfuse.com'),
        )
        logger.info("Langfuse client initialised (v3)")
        return _langfuse_client
    except Exception as exc:
        logger.warning(f"Langfuse client init failed: {exc}")
        return None


def create_llm(config: "Settings", temperature: float = 0.1):
    """Return a ChatOpenAI instance configured from Settings."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=config.MODEL_NAME,
        temperature=temperature,
        openai_api_key=config.OPENAI_API_KEY,
    )


def get_callbacks(config: "Settings", session_id: str, trace_name: str) -> List:
    """
    Return a list of LangChain callbacks for the current invocation.

    Uses langfuse v3 langchain integration (langfuse.langchain.CallbackHandler).
    Each agent LLM call is traced with session_id and user_id so all 6 agents
    for one pipeline run are grouped under the same session in Langfuse.
    """
    lf = _get_langfuse_client(config)
    if lf is None:
        return []

    pk = getattr(config, 'LANGFUSE_PUBLIC_KEY', None)
    sk = getattr(config, 'LANGFUSE_SECRET_KEY', None)
    host = getattr(config, 'LANGFUSE_HOST', 'https://cloud.langfuse.com')

    try:
        # langfuse v3: CallbackHandler reads keys from env vars
        import os
        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", pk)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", sk)
        os.environ.setdefault("LANGFUSE_HOST", host)

        from langfuse.langchain import CallbackHandler  # type: ignore
        handler = CallbackHandler(
            session_id=session_id,
            user_id=session_id,
            trace_name=trace_name,
            tags=["nexus", getattr(config, 'APP_ENV', 'development')],
        )
        logger.info(f"[{session_id}] Langfuse callback attached: {trace_name}")
        return [handler]
    except Exception as exc:
        logger.warning(f"[{session_id}] Langfuse langchain handler failed: {exc}")
        return []


def flush_langfuse():
    """Flush pending Langfuse events — called on app shutdown."""
    global _langfuse_client
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
            logger.info("Langfuse flushed")
        except Exception:
            pass
