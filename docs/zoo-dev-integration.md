# NEXUS — Zoo.dev Text-to-CAD Integration

> AI-powered parametric CAD generation via Zoo.dev API for rapid concept-to-STEP workflows.

---

## Overview

Zoo.dev Text-to-CAD generates **real parametric CAD files** (STEP, STL, glTF) from natural language prompts. Unlike artistic mesh generators (TRELLIS, Meshy), Zoo produces engineering-grade geometry suitable for simulation and manufacturing.

### Why Zoo.dev for NEXUS?

| Feature | Zoo.dev | FreeCAD (Current) |
|---------|---------|-------------------|
| Input | Natural language prompt | Python script + parameters |
| Speed | ~30-60 seconds | Instant (local) |
| Flexibility | Any shape describable | Predefined templates only |
| Output | STEP, STL, glTF | STEP, STL |
| Cost | $0.50/min (20 free min/month) | Free |

**Use Case:** Rapid prototyping before detailed FreeCAD parametric design.

---

## Pricing

| Tier | Cost | Notes |
|------|------|-------|
| Free | 20 minutes/month | Resets on 1st of month |
| Pay-as-you-go | $0.50/minute | Billed per second |
| Enterprise | Contact sales | Volume discounts |

**Typical costs:**
- Simple part (brick, bracket): ~$0.50
- Complex part (heat exchanger): ~$2-5
- File conversion (STEP→STL): ~$0.10

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       NEXUS Platform                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Design Agent                                │    │
│  │  Requirements → Design Parameters → CAD Generation       │    │
│  └────────────────────┬────────────────────────────────────┘    │
│                       │                                          │
│           ┌───────────┴───────────┐                             │
│           ▼                       ▼                             │
│  ┌─────────────────┐    ┌─────────────────┐                     │
│  │ FreeCAD Tool    │    │ Zoo.dev Tool    │  ← NEW              │
│  │ (Parametric)    │    │ (AI-Generated)  │                     │
│  │                 │    │                 │                     │
│  │ • Templates     │    │ • Any shape     │                     │
│  │ • Precise dims  │    │ • Natural lang  │                     │
│  │ • Local/free    │    │ • Cloud API     │                     │
│  └────────┬────────┘    └────────┬────────┘                     │
│           │                       │                              │
│           └───────────┬───────────┘                             │
│                       ▼                                          │
│              cad_output/{session_id}/                           │
│              ├── design.step                                    │
│              ├── design.stl                                     │
│              └── design.gltf                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## UI Toggle: Comparison Mode

Users can toggle between FreeCAD and Zoo.dev to compare generation experience side-by-side.

### Toggle Component

**File: `frontend/components/cad/CADEngineToggle.tsx`**
```tsx
"use client";

import { useState } from "react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Cpu, Cloud, Zap, DollarSign } from "lucide-react";

export type CADEngine = "freecad" | "zoo";

interface CADEngineToggleProps {
  value: CADEngine;
  onChange: (engine: CADEngine) => void;
  disabled?: boolean;
}

export function CADEngineToggle({ value, onChange, disabled }: CADEngineToggleProps) {
  const isZoo = value === "zoo";

  return (
    <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-md ${isZoo ? "bg-purple-100" : "bg-blue-100"}`}>
          {isZoo ? (
            <Cloud className="h-5 w-5 text-purple-600" />
          ) : (
            <Cpu className="h-5 w-5 text-blue-600" />
          )}
        </div>
        <div>
          <Label className="text-sm font-medium">
            CAD Engine: {isZoo ? "Zoo.dev AI" : "FreeCAD"}
          </Label>
          <p className="text-xs text-muted-foreground">
            {isZoo 
              ? "Natural language → any shape (cloud)" 
              : "Parametric templates (local)"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Feature badges */}
        <div className="hidden md:flex gap-2">
          {isZoo ? (
            <>
              <Badge variant="outline" className="text-xs">
                <Zap className="h-3 w-3 mr-1" /> AI-Powered
              </Badge>
              <Badge variant="outline" className="text-xs text-amber-600">
                <DollarSign className="h-3 w-3 mr-1" /> $0.50/min
              </Badge>
            </>
          ) : (
            <>
              <Badge variant="outline" className="text-xs text-green-600">
                Free
              </Badge>
              <Badge variant="outline" className="text-xs">
                Instant
              </Badge>
            </>
          )}
        </div>

        {/* Toggle switch */}
        <div className="flex items-center gap-2">
          <span className={`text-xs ${!isZoo ? "font-medium" : "text-muted-foreground"}`}>
            FreeCAD
          </span>
          <Switch
            checked={isZoo}
            onCheckedChange={(checked) => onChange(checked ? "zoo" : "freecad")}
            disabled={disabled}
          />
          <span className={`text-xs ${isZoo ? "font-medium" : "text-muted-foreground"}`}>
            Zoo.dev
          </span>
        </div>
      </div>
    </div>
  );
}
```

### Side-by-Side Comparison View

**File: `frontend/components/cad/CADComparisonView.tsx`**
```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Play, Clock, DollarSign, FileBox } from "lucide-react";

interface GenerationResult {
  engine: "freecad" | "zoo";
  success: boolean;
  stepPath?: string;
  stlPath?: string;
  timeSeconds: number;
  costUsd?: number;
  error?: string;
}

export function CADComparisonView() {
  const [prompt, setPrompt] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [results, setResults] = useState<GenerationResult[]>([]);

  const runComparison = async () => {
    setIsGenerating(true);
    setResults([]);

    // Run both engines in parallel
    const [freecadResult, zooResult] = await Promise.all([
      generateWithFreecad(prompt),
      generateWithZoo(prompt),
    ]);

    setResults([freecadResult, zooResult]);
    setIsGenerating(false);
  };

  return (
    <div className="space-y-6">
      {/* Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileBox className="h-5 w-5" />
            CAD Engine Comparison
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Describe your part... e.g., 'cylindrical heatsink, 50mm diameter, 30mm tall, with 12 radial fins'"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={3}
          />
          <Button 
            onClick={runComparison} 
            disabled={!prompt || isGenerating}
            className="w-full"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Generating with both engines...
              </>
            ) : (
              <>
                <Play className="h-4 w-4 mr-2" />
                Run Side-by-Side Comparison
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results side-by-side */}
      {results.length > 0 && (
        <div className="grid md:grid-cols-2 gap-4">
          {results.map((result) => (
            <Card 
              key={result.engine}
              className={result.success ? "border-green-200" : "border-red-200"}
            >
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center justify-between">
                  <span>{result.engine === "freecad" ? "FreeCAD" : "Zoo.dev AI"}</span>
                  {result.success ? (
                    <span className="text-green-600 text-sm">✓ Success</span>
                  ) : (
                    <span className="text-red-600 text-sm">✗ Failed</span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Metrics */}
                <div className="flex gap-4 text-sm">
                  <div className="flex items-center gap-1">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span>{result.timeSeconds.toFixed(1)}s</span>
                  </div>
                  {result.costUsd !== undefined && (
                    <div className="flex items-center gap-1">
                      <DollarSign className="h-4 w-4 text-muted-foreground" />
                      <span>${result.costUsd.toFixed(2)}</span>
                    </div>
                  )}
                </div>

                {/* 3D Preview placeholder */}
                {result.success && result.stlPath && (
                  <div className="h-48 bg-muted rounded-md flex items-center justify-center">
                    {/* Integrate Three.js STL viewer here */}
                    <span className="text-muted-foreground text-sm">
                      3D Preview: {result.stlPath}
                    </span>
                  </div>
                )}

                {/* Error message */}
                {result.error && (
                  <p className="text-sm text-red-600">{result.error}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Comparison summary */}
      {results.length === 2 && results.every(r => r.success) && (
        <Card className="bg-muted/30">
          <CardContent className="pt-4">
            <h4 className="font-medium mb-2">Comparison Summary</h4>
            <ul className="text-sm space-y-1">
              <li>
                <strong>Speed:</strong>{" "}
                {results[0].timeSeconds < results[1].timeSeconds 
                  ? `FreeCAD ${(results[1].timeSeconds / results[0].timeSeconds).toFixed(1)}x faster`
                  : `Zoo.dev ${(results[0].timeSeconds / results[1].timeSeconds).toFixed(1)}x faster`
                }
              </li>
              <li>
                <strong>Cost:</strong>{" "}
                FreeCAD: $0 | Zoo.dev: ${results[1].costUsd?.toFixed(2) || "N/A"}
              </li>
              <li>
                <strong>Best for:</strong>{" "}
                FreeCAD for templates, Zoo.dev for custom shapes
              </li>
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// API helpers
async function generateWithFreecad(prompt: string): Promise<GenerationResult> {
  const start = performance.now();
  try {
    const res = await fetch("/api/cad/freecad", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, session_id: `compare_${Date.now()}` }),
    });
    const data = await res.json();
    return {
      engine: "freecad",
      success: data.success,
      stepPath: data.step_path,
      stlPath: data.stl_path,
      timeSeconds: (performance.now() - start) / 1000,
      error: data.error,
    };
  } catch (e: any) {
    return {
      engine: "freecad",
      success: false,
      timeSeconds: (performance.now() - start) / 1000,
      error: e.message,
    };
  }
}

async function generateWithZoo(prompt: string): Promise<GenerationResult> {
  const start = performance.now();
  try {
    const res = await fetch("/api/cad/text-to-cad", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        prompt, 
        session_id: `compare_${Date.now()}`,
        output_formats: ["step", "stl"]
      }),
    });
    const data = await res.json();
    return {
      engine: "zoo",
      success: data.success,
      stepPath: data.step_path,
      stlPath: data.stl_path,
      timeSeconds: (performance.now() - start) / 1000,
      costUsd: data.estimated_cost_usd,
      error: data.error_message,
    };
  } catch (e: any) {
    return {
      engine: "zoo",
      success: false,
      timeSeconds: (performance.now() - start) / 1000,
      error: e.message,
    };
  }
}
```

### Usage in Design Page

**Edit: `frontend/app/design/page.tsx`**
```tsx
import { CADEngineToggle, CADEngine } from "@/components/cad/CADEngineToggle";
import { CADComparisonView } from "@/components/cad/CADComparisonView";

export default function DesignPage() {
  const [cadEngine, setCADEngine] = useState<CADEngine>("freecad");
  const [showComparison, setShowComparison] = useState(false);

  return (
    <div className="space-y-6">
      {/* Toggle between engines */}
      <CADEngineToggle value={cadEngine} onChange={setCADEngine} />

      {/* Option to run side-by-side comparison */}
      <Button 
        variant="outline" 
        onClick={() => setShowComparison(!showComparison)}
      >
        {showComparison ? "Hide" : "Show"} Side-by-Side Comparison
      </Button>

      {showComparison && <CADComparisonView />}

      {/* Rest of design workflow uses selected engine */}
    </div>
  );
}
```

---

## Step-by-Step Integration

### Step 1: Environment Setup

```bash
# 1.1 Create feature branch
cd nexus-agentic-platform
git checkout -b feature/zoo-dev-integration

# 1.2 Install dependencies
pip install httpx python-dotenv

# 1.3 Add to requirements.txt
echo "httpx>=0.27.0" >> backend/requirements.txt

# 1.4 Get Zoo.dev API key
# Visit: https://zoo.dev/account/api-tokens
# Create token with Text-to-CAD scope
```

### Step 2: Add Environment Variables

**File: `backend/.env`**
```env
# Zoo.dev Text-to-CAD API
ZOO_API_KEY=your_zoo_api_key_here
ZOO_API_URL=https://api.zoo.dev
ZOO_TIMEOUT_SECONDS=120
ZOO_MAX_RETRIES=3
```

**File: `backend/.env.example`**
```env
# Zoo.dev Text-to-CAD API (optional - for AI CAD generation)
ZOO_API_KEY=
ZOO_API_URL=https://api.zoo.dev
ZOO_TIMEOUT_SECONDS=120
ZOO_MAX_RETRIES=3
```

### Step 3: Create Zoo.dev Tool

**File: `backend/app/tools/zoo_cad_tool.py`**
```python
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
```

### Step 4: Register Tool with Design Agent

**Edit: `backend/app/agents/design_agent.py`**

Add import at top:
```python
from app.tools.zoo_cad_tool import generate_cad_from_text, ZOO_CAD_TOOL_SCHEMA
```

Add to tool binding (around line 65):
```python
# Add Zoo.dev tool alongside calculator tools
all_tools = CALCULATOR_TOOLS + [generate_cad_from_text]
llm = create_llm(config, temperature=0.1).bind_tools(all_tools)
```

### Step 5: Add API Route for Direct Access

**File: `backend/app/routers/cad_routes.py`**
```python
"""
NEXUS Platform — CAD Generation API Routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional

from app.tools.zoo_cad_tool import get_zoo_client, ZooCADResult

router = APIRouter(prefix="/api/cad", tags=["cad"])


class TextToCADRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=100)
    output_formats: List[str] = Field(default=["step", "stl"])


class TextToCADResponse(BaseModel):
    success: bool
    step_path: Optional[str] = None
    stl_path: Optional[str] = None
    gltf_path: Optional[str] = None
    generation_time_seconds: float
    estimated_cost_usd: float
    error_message: Optional[str] = None


class CreditsResponse(BaseModel):
    available: bool
    free_minutes_remaining: Optional[float] = None
    error: Optional[str] = None


@router.post("/text-to-cad", response_model=TextToCADResponse)
async def generate_cad(request: TextToCADRequest):
    """
    Generate CAD files from natural language prompt using Zoo.dev API.
    
    Pricing: $0.50/minute, 20 free minutes/month included.
    """
    client = get_zoo_client()
    
    if not client.is_available:
        raise HTTPException(
            status_code=503,
            detail="Zoo.dev API not configured. Set ZOO_API_KEY environment variable."
        )
    
    result = await client.generate(
        prompt=request.prompt,
        session_id=request.session_id,
        output_formats=request.output_formats
    )
    
    return TextToCADResponse(
        success=result.success,
        step_path=result.step_path,
        stl_path=result.stl_path,
        gltf_path=result.gltf_path,
        generation_time_seconds=result.generation_time_seconds,
        estimated_cost_usd=result.estimated_cost_usd,
        error_message=result.error_message
    )


@router.get("/credits", response_model=CreditsResponse)
async def check_credits():
    """Check remaining Zoo.dev API credits."""
    client = get_zoo_client()
    
    if not client.is_available:
        return CreditsResponse(available=False, error="API key not configured")
    
    credits_info = await client.check_credits()
    
    if "error" in credits_info:
        return CreditsResponse(available=False, error=credits_info["error"])
    
    return CreditsResponse(
        available=True,
        free_minutes_remaining=credits_info.get("free_minutes_remaining")
    )


@router.get("/health")
async def cad_health():
    """Check Zoo.dev API connectivity."""
    client = get_zoo_client()
    return {
        "zoo_api_configured": client.is_available,
        "zoo_api_url": client.base_url if client.is_available else None
    }
```

### Step 6: Register Router in Main App

**Edit: `backend/app/main.py`**

Add import:
```python
from app.routers.cad_routes import router as cad_router
```

Add router registration:
```python
app.include_router(cad_router)
```

---

## Performance Testing

### Test 1: Unit Tests

**File: `backend/tests/test_zoo_cad_tool.py`**
```python
"""
NEXUS Platform — Zoo.dev Text-to-CAD Tool Tests
"""
import pytest
import asyncio
import time
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# Skip tests if API key not available
pytestmark = pytest.mark.skipif(
    not os.getenv("ZOO_API_KEY"),
    reason="ZOO_API_KEY not set"
)


class TestZooCADClient:
    """Unit tests for Zoo.dev client."""
    
    @pytest.fixture
    def client(self):
        from app.tools.zoo_cad_tool import ZooCADClient
        return ZooCADClient()
    
    def test_client_initialization(self, client):
        """Client should initialize with env vars."""
        assert client.base_url == "https://api.zoo.dev"
        assert client.is_available == bool(os.getenv("ZOO_API_KEY"))
    
    @pytest.mark.asyncio
    async def test_generate_simple_part(self, client, tmp_path):
        """Generate a simple brick — should complete in < 90 seconds."""
        if not client.is_available:
            pytest.skip("API key not configured")
        
        start = time.perf_counter()
        result = await client.generate(
            prompt="simple rectangular brick, 100mm x 50mm x 25mm",
            session_id="test_simple",
            output_formats=["step"],
            output_dir=tmp_path
        )
        elapsed = time.perf_counter() - start
        
        assert result.success, f"Generation failed: {result.error_message}"
        assert result.step_path is not None
        assert Path(result.step_path).exists()
        assert Path(result.step_path).stat().st_size > 1000  # > 1KB
        assert elapsed < 90, f"Generation took {elapsed:.1f}s, expected < 90s"
        print(f"Simple brick: {elapsed:.1f}s, cost: ${result.estimated_cost_usd}")
    
    @pytest.mark.asyncio
    async def test_generate_complex_part(self, client, tmp_path):
        """Generate complex heatsink — should complete in < 180 seconds."""
        if not client.is_available:
            pytest.skip("API key not configured")
        
        start = time.perf_counter()
        result = await client.generate(
            prompt=(
                "cylindrical heatsink for electronics cooling, "
                "60mm outer diameter, 40mm height, "
                "central bore 20mm diameter for mounting, "
                "16 radial fins, each 2mm thick, extending to outer edge, "
                "aluminum 6061"
            ),
            session_id="test_complex",
            output_formats=["step", "stl"],
            output_dir=tmp_path
        )
        elapsed = time.perf_counter() - start
        
        assert result.success, f"Generation failed: {result.error_message}"
        assert result.step_path is not None
        assert result.stl_path is not None
        assert elapsed < 180, f"Generation took {elapsed:.1f}s, expected < 180s"
        print(f"Complex heatsink: {elapsed:.1f}s, cost: ${result.estimated_cost_usd}")
    
    @pytest.mark.asyncio
    async def test_invalid_prompt_handling(self, client, tmp_path):
        """Invalid prompt should return graceful error."""
        if not client.is_available:
            pytest.skip("API key not configured")
        
        result = await client.generate(
            prompt="",  # Empty prompt
            session_id="test_invalid",
            output_formats=["step"],
            output_dir=tmp_path
        )
        
        # Should fail gracefully, not crash
        assert result.success == False or result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_check_credits(self, client):
        """Should retrieve credit info."""
        if not client.is_available:
            pytest.skip("API key not configured")
        
        credits = await client.check_credits()
        assert "error" not in credits or credits.get("error") is None


class TestZooCADPerformance:
    """Performance benchmarks for Zoo.dev integration."""
    
    @pytest.fixture
    def client(self):
        from app.tools.zoo_cad_tool import ZooCADClient
        return ZooCADClient()
    
    @pytest.mark.asyncio
    async def test_concurrent_generations(self, client, tmp_path):
        """Test 3 concurrent generations — should all complete."""
        if not client.is_available:
            pytest.skip("API key not configured")
        
        prompts = [
            "cube 50mm x 50mm x 50mm",
            "cylinder 30mm diameter, 60mm height",
            "rectangular plate 100mm x 50mm x 5mm with 4 corner holes 5mm diameter"
        ]
        
        start = time.perf_counter()
        tasks = [
            client.generate(
                prompt=p,
                session_id=f"concurrent_{i}",
                output_formats=["step"],
                output_dir=tmp_path / f"part_{i}"
            )
            for i, p in enumerate(prompts)
        ]
        results = await asyncio.gather(*tasks)
        elapsed = time.perf_counter() - start
        
        successes = sum(1 for r in results if r.success)
        print(f"Concurrent test: {successes}/3 succeeded in {elapsed:.1f}s")
        
        assert successes >= 2, f"Only {successes}/3 succeeded"
        assert elapsed < 300, f"Concurrent took {elapsed:.1f}s, expected < 300s"
    
    @pytest.mark.asyncio
    async def test_generation_time_distribution(self, client, tmp_path):
        """Benchmark generation times for different complexities."""
        if not client.is_available:
            pytest.skip("API key not configured")
        
        test_cases = [
            ("simple", "cube 25mm"),
            ("medium", "bracket with 2 holes, 80mm x 40mm x 3mm, holes 6mm diameter"),
            ("complex", "finned heatsink 50mm diameter, 30mm tall, 12 fins, 1.5mm thick")
        ]
        
        results = {}
        for name, prompt in test_cases:
            start = time.perf_counter()
            result = await client.generate(
                prompt=prompt,
                session_id=f"bench_{name}",
                output_formats=["step"],
                output_dir=tmp_path / name
            )
            elapsed = time.perf_counter() - start
            results[name] = {
                "success": result.success,
                "time_seconds": elapsed,
                "cost_usd": result.estimated_cost_usd
            }
        
        print("\n=== Generation Time Benchmark ===")
        for name, data in results.items():
            status = "✓" if data["success"] else "✗"
            print(f"{status} {name}: {data['time_seconds']:.1f}s (${data['cost_usd']})")
        
        # All should succeed
        assert all(r["success"] for r in results.values())
```

### Test 2: API Load Test

**File: `backend/tests/performance/locustfile_cad.py`**
```python
"""
NEXUS Platform — Zoo.dev CAD API Load Test

Run with:
    locust -f tests/performance/locustfile_cad.py --host=http://localhost:8003

Note: This will consume Zoo.dev API credits!
"""
from locust import HttpUser, task, between
import random


class CADAPIUser(HttpUser):
    """Load test for CAD generation API."""
    
    # Slow wait time — CAD generation is expensive
    wait_time = between(30, 60)
    
    PROMPTS = [
        "cube 50mm x 50mm x 50mm",
        "cylinder 40mm diameter, 80mm height",
        "rectangular bracket 100mm x 30mm x 5mm with 2 mounting holes",
        "hexagonal nut M10, 8mm thick",
        "simple washer, outer diameter 20mm, inner 10mm, thickness 2mm",
    ]
    
    @task(1)
    def generate_simple_cad(self):
        """Generate a simple CAD part."""
        prompt = random.choice(self.PROMPTS)
        session_id = f"loadtest_{random.randint(1000, 9999)}"
        
        with self.client.post(
            "/api/cad/text-to-cad",
            json={
                "prompt": prompt,
                "session_id": session_id,
                "output_formats": ["step"]
            },
            timeout=120,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    response.success()
                else:
                    response.failure(f"Generation failed: {data.get('error_message')}")
            elif response.status_code == 503:
                response.failure("API not configured")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(5)
    def check_health(self):
        """Health check — lightweight."""
        self.client.get("/api/cad/health")
    
    @task(2)
    def check_credits(self):
        """Check API credits."""
        self.client.get("/api/cad/credits")
```

### Test 3: Integration Test Script

**File: `backend/tests/test_zoo_integration.py`**
```python
"""
NEXUS Platform — Zoo.dev End-to-End Integration Test

Run manually:
    python -m pytest tests/test_zoo_integration.py -v -s
"""
import pytest
import httpx
import asyncio
import os
from pathlib import Path

BASE_URL = os.getenv("NEXUS_API_URL", "http://localhost:8003")


@pytest.mark.integration
class TestZooDevIntegration:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test complete workflow: health → credits → generate → verify."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=120) as client:
            # 1. Health check
            health = await client.get("/api/cad/health")
            assert health.status_code == 200
            health_data = health.json()
            
            if not health_data.get("zoo_api_configured"):
                pytest.skip("Zoo.dev API not configured")
            
            # 2. Check credits
            credits = await client.get("/api/cad/credits")
            assert credits.status_code == 200
            print(f"Credits: {credits.json()}")
            
            # 3. Generate CAD
            response = await client.post(
                "/api/cad/text-to-cad",
                json={
                    "prompt": "simple test cube 30mm x 30mm x 30mm",
                    "session_id": "integration_test",
                    "output_formats": ["step", "stl"]
                }
            )
            assert response.status_code == 200
            data = response.json()
            
            print(f"Generation result: {data}")
            
            assert data["success"], f"Failed: {data.get('error_message')}"
            assert data["step_path"] is not None
            assert data["generation_time_seconds"] > 0
            assert data["estimated_cost_usd"] >= 0
            
            # 4. Verify files exist
            step_path = Path(data["step_path"])
            assert step_path.exists(), f"STEP file not found: {step_path}"
            assert step_path.stat().st_size > 100, "STEP file too small"
            
            print(f"✓ Integration test passed in {data['generation_time_seconds']:.1f}s")
```

---

## Performance Targets

| Metric | Target | Test Command |
|--------|--------|--------------|
| **Simple part generation** | < 60s | `pytest tests/test_zoo_cad_tool.py::TestZooCADClient::test_generate_simple_part` |
| **Complex part generation** | < 180s | `pytest tests/test_zoo_cad_tool.py::TestZooCADClient::test_generate_complex_part` |
| **3 concurrent generations** | < 300s total | `pytest tests/test_zoo_cad_tool.py::TestZooCADPerformance::test_concurrent_generations` |
| **API health check** | < 100ms | `curl http://localhost:8003/api/cad/health` |
| **Error handling** | No crashes | `pytest tests/test_zoo_cad_tool.py::TestZooCADClient::test_invalid_prompt_handling` |

---

## Cost Estimation

| Usage Pattern | Monthly Generations | Estimated Cost |
|---------------|---------------------|----------------|
| Light (prototyping) | 20 parts | **$0** (free tier) |
| Medium (development) | 50 parts | ~$15-25 |
| Heavy (production) | 200 parts | ~$100-150 |

---

## Rollout Checklist

- [ ] Get Zoo.dev API key from https://zoo.dev/account/api-tokens
- [ ] Add `ZOO_API_KEY` to backend `.env`
- [ ] Run unit tests: `pytest tests/test_zoo_cad_tool.py`
- [ ] Run integration test: `pytest tests/test_zoo_integration.py`
- [ ] Test via Swagger UI: http://localhost:8003/docs#/cad
- [ ] Monitor credits usage via `/api/cad/credits`
- [ ] Add billing alerts in Zoo.dev dashboard

---

## References

- [Zoo.dev API Documentation](https://zoo.dev/docs/api)
- [Zoo.dev Pricing](https://zoo.dev/zoo-pricing)
- [Text-to-CAD Examples](https://zoo.dev/text-to-cad)
- [Zoo.dev Community Forum](https://community.zoo.dev)

---

*Created: April 4, 2026*
*Author: NEXUS Platform Team*
