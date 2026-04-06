"""
NEXUS Platform — Zoo.dev Text-to-CAD Tool
==========================================
Generates parametric CAD files (STEP, STL, glTF) from natural language
prompts using Zoo.dev's Text-to-CAD API.

Output files are written to: backend/cad_output/{session_id}/
  zoo_design.step  — ISO 10303 STEP for CAD interop
  zoo_design.stl   — STL mesh for 3D printing
  zoo_design.gltf  — glTF for web/browser viewing

Pricing: $0.50/minute, 20 free minutes/month
API Docs: https://zoo.dev/docs/api/ai/text-to-cad
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Output directory — same as FreeCAD tool
CAD_OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "cad_output"
CAD_OUTPUT_DIR.mkdir(exist_ok=True)

# API Configuration
ZOO_API_URL = os.getenv("ZOO_API_URL", "https://api.zoo.dev")
ZOO_API_KEY = os.getenv("ZOO_API_KEY", "")
ZOO_TIMEOUT = int(os.getenv("ZOO_TIMEOUT_SECONDS", "120"))
ZOO_MAX_RETRIES = int(os.getenv("ZOO_MAX_RETRIES", "3"))


@dataclass
class ZooCADResult:
    """Result from Zoo.dev Text-to-CAD generation."""
    success: bool
    step_path: Optional[str] = None
    stl_path: Optional[str] = None
    gltf_path: Optional[str] = None
    generation_time_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    error_message: Optional[str] = None
    prompt_used: str = ""


class ZooCADClient:
    """
    Async client for Zoo.dev Text-to-CAD API.
    
    Usage:
        client = ZooCADClient()
        result = await client.generate(
            prompt="cylindrical heat exchanger shell, 200mm diameter, 500mm length",
            session_id="session_123",
            output_formats=["step", "stl"]
        )
    """
    
    def __init__(self, api_key: str = None, base_url: str = None):
        self.api_key = api_key or ZOO_API_KEY
        self.base_url = base_url or ZOO_API_URL
        
        if not self.api_key:
            logger.warning("ZOO_API_KEY not set — Zoo.dev CAD generation disabled")
    
    @property
    def is_available(self) -> bool:
        """Check if Zoo.dev API is configured."""
        return bool(self.api_key)
    
    async def generate(
        self,
        prompt: str,
        session_id: str,
        output_formats: list[Literal["step", "stl", "gltf"]] = ["step", "stl"],
        output_dir: Path = None
    ) -> ZooCADResult:
        """
        Generate CAD files from natural language prompt.
        
        Args:
            prompt: Natural language description of the part
            session_id: Session ID for file organization
            output_formats: List of output formats to generate
            output_dir: Override output directory
            
        Returns:
            ZooCADResult with file paths and metadata
        """
        if not self.is_available:
            return ZooCADResult(
                success=False,
                error_message="Zoo.dev API key not configured",
                prompt_used=prompt
            )
        
        start_time = time.perf_counter()
        output_path = output_dir or (CAD_OUTPUT_DIR / session_id)
        output_path.mkdir(parents=True, exist_ok=True)
        
        result = ZooCADResult(success=False, prompt_used=prompt)
        
        try:
            async with httpx.AsyncClient(timeout=ZOO_TIMEOUT) as client:
                # Generate for each requested format
                for fmt in output_formats:
                    file_path = await self._generate_format(
                        client, prompt, fmt, output_path
                    )
                    if file_path:
                        setattr(result, f"{fmt}_path", str(file_path))
                
                # Check if at least one format succeeded
                if result.step_path or result.stl_path or result.gltf_path:
                    result.success = True
                else:
                    result.error_message = "All format generations failed"
                    
        except httpx.TimeoutException:
            result.error_message = f"API timeout after {ZOO_TIMEOUT}s"
            logger.error(f"[{session_id}] Zoo.dev timeout: {prompt[:50]}...")
        except httpx.HTTPStatusError as e:
            result.error_message = f"API error: {e.response.status_code}"
            logger.error(f"[{session_id}] Zoo.dev HTTP error: {e}")
        except Exception as e:
            result.error_message = f"Unexpected error: {str(e)}"
            logger.exception(f"[{session_id}] Zoo.dev error")
        
        # Calculate timing and cost
        elapsed = time.perf_counter() - start_time
        result.generation_time_seconds = round(elapsed, 2)
        result.estimated_cost_usd = round((elapsed / 60) * 0.50, 2)
        
        logger.info(
            f"[{session_id}] Zoo.dev generation: "
            f"success={result.success}, time={elapsed:.1f}s, "
            f"cost=${result.estimated_cost_usd}"
        )
        
        return result
    
    async def _generate_format(
        self,
        client: httpx.AsyncClient,
        prompt: str,
        output_format: str,
        output_path: Path
    ) -> Optional[Path]:
        """Generate a single format via Zoo.dev API."""
        
        endpoint = f"{self.base_url}/ai/text-to-cad/{output_format}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {"prompt": prompt}
        
        for attempt in range(ZOO_MAX_RETRIES):
            try:
                response = await client.post(
                    endpoint,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                # Save the file
                file_path = output_path / f"zoo_design.{output_format}"
                file_path.write_bytes(response.content)
                
                logger.debug(f"Generated {output_format}: {file_path}")
                return file_path
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited — wait and retry
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                elif e.response.status_code == 402:
                    # Payment required — out of free credits
                    logger.error("Zoo.dev free credits exhausted, payment required")
                    return None
                else:
                    raise
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == ZOO_MAX_RETRIES - 1:
                    raise
        
        return None
    
    async def check_credits(self) -> dict:
        """Check remaining API credits."""
        if not self.is_available:
            return {"error": "API key not configured"}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self.base_url}/user/api-calls",
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"error": str(e)}


# Singleton instance
_zoo_client: Optional[ZooCADClient] = None


def get_zoo_client() -> ZooCADClient:
    """Get or create Zoo.dev client singleton."""
    global _zoo_client
    if _zoo_client is None:
        _zoo_client = ZooCADClient()
    return _zoo_client


# ── LangChain Tool Interface ─────────────────────────────────────────────────

async def generate_cad_from_text(
    prompt: str,
    session_id: str,
    output_formats: str = "step,stl"
) -> dict:
    """
    LangChain-compatible tool for Text-to-CAD generation.
    
    Args:
        prompt: Natural language description of the part to generate
        session_id: Session identifier for file organization
        output_formats: Comma-separated list of formats (step, stl, gltf)
    
    Returns:
        Dictionary with file paths and generation metadata
    """
    client = get_zoo_client()
    formats = [f.strip().lower() for f in output_formats.split(",")]
    
    result = await client.generate(
        prompt=prompt,
        session_id=session_id,
        output_formats=formats
    )
    
    return {
        "success": result.success,
        "step_file": result.step_path,
        "stl_file": result.stl_path,
        "gltf_file": result.gltf_path,
        "generation_time_seconds": result.generation_time_seconds,
        "estimated_cost_usd": result.estimated_cost_usd,
        "error": result.error_message,
        "prompt": result.prompt_used
    }


# ── Tool Definition for LangChain ────────────────────────────────────────────

ZOO_CAD_TOOL_SCHEMA = {
    "name": "generate_cad_from_text",
    "description": (
        "Generate a 3D CAD file (STEP, STL) from a natural language description. "
        "Use this for rapid prototyping or when the user describes a custom shape "
        "that doesn't fit predefined templates. Returns file paths to generated CAD files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": (
                    "Detailed natural language description of the part. "
                    "Include dimensions, materials, and key features. "
                    "Example: 'cylindrical heatsink, 50mm diameter, 30mm tall, "
                    "with 12 radial fins, 2mm thick, aluminum'"
                )
            },
            "output_formats": {
                "type": "string",
                "description": "Comma-separated output formats: step, stl, gltf",
                "default": "step,stl"
            }
        },
        "required": ["prompt"]
    }
}
