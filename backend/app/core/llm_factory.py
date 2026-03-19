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
        host = getattr(config, 'LANGFUSE_HOST', 'https://cloud.langfuse.com')
        _langfuse_client = Langfuse(public_key=pk, secret_key=sk, host=host)
        logger.info("Langfuse client initialised (v3)")
        _register_model_prices(pk, sk, host)
        return _langfuse_client
    except Exception as exc:
        logger.warning(f"Langfuse client init failed: {exc}")
        return None


def _register_model_prices(pk: str, sk: str, host: str) -> None:
    """
    Register OpenAI model prices in this Langfuse project so cost tracking works.
    Uses the Langfuse REST API — prices are per token (not per 1M tokens).
    Silently skips if models already exist or if the API is unreachable.

    Prices (March 2026):
      gpt-4o         input $2.50/1M  output $10.00/1M
      gpt-4o-mini    input $0.15/1M  output  $0.60/1M
    """
    import base64
    import json
    import urllib.request

    credentials = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }
    url = f"{host.rstrip('/')}/api/public/models"

    models = [
        {
            "modelName": "gpt-4o",
            "matchPattern": r"(?i)^(gpt-4o)(-\d{4}-\d{2}-\d{2})?$",
            "unit": "TOKENS",
            "inputPrice": 0.0000025,
            "outputPrice": 0.00001,
            "tokenizerId": "cl100k_base",
        },
        {
            "modelName": "gpt-4o-mini",
            "matchPattern": r"(?i)^(gpt-4o-mini)(-\d{4}-\d{2}-\d{2})?$",
            "unit": "TOKENS",
            "inputPrice": 0.00000015,
            "outputPrice": 0.0000006,
            "tokenizerId": "cl100k_base",
        },
        {
            "modelName": "text-embedding-3-small",
            "matchPattern": r"(?i)^text-embedding-3-small$",
            "unit": "TOKENS",
            "inputPrice": 0.00000002,
            "outputPrice": 0.0,
            "tokenizerId": "cl100k_base",
        },
    ]

    for model in models:
        try:
            data = json.dumps(model).encode()
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status in (200, 201):
                    logger.info(f"Langfuse model price registered: {model['modelName']}")
        except Exception as exc:
            # 409 = already exists — that's fine
            logger.debug(f"Model price registration skipped for {model['modelName']}: {exc}")


def create_llm(config: "Settings", temperature: float = 0.1):
    """Return a ChatOpenAI instance configured from Settings."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=config.MODEL_NAME,
        temperature=temperature,
        openai_api_key=config.OPENAI_API_KEY,
    )


def get_callbacks(
    config: "Settings",
    session_id: str,
    trace_name: str,
    trace_id: str = None,
    user_id: str = None,
) -> List:
    """
    Return a list of LangChain callbacks for the current invocation.

    Uses langfuse v3 langchain integration (langfuse.langchain.CallbackHandler).
    Passing trace_id nests each LLM generation under the root nexus-pipeline trace
    so token usage and costs roll up correctly in the Langfuse dashboard.
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

        kwargs = dict(
            session_id=session_id,
            user_id=user_id or session_id,
            trace_name=trace_name,
            tags=["nexus", getattr(config, 'APP_ENV', 'development')],
        )
        # If trace_id is provided, nest this generation under the root pipeline trace
        if trace_id:
            kwargs["trace_id"] = trace_id

        handler = CallbackHandler(**kwargs)
        logger.info(f"[{session_id}] Langfuse callback attached: {trace_name} (trace={trace_id})")
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
