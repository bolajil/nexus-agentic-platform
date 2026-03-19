"""
NEXUS Platform — Locust Load Testing
======================================
Simulates concurrent engineers submitting design briefs and querying sessions.

Run:
    pip install locust
    cd backend/tests
    locust -f locustfile.py --host http://localhost:8003

Then open http://localhost:8089 and set:
  - Number of users: 10–50
  - Spawn rate: 2 per second

Architecture note (for interviews):
  Single uvicorn worker handles ~10-20 concurrent SSE streams via asyncio.
  Scale to 50-100 concurrent users with:
      uvicorn app.main:app --workers 4 (requires Redis for shared session store)
  Scale to 200-500 with Kubernetes HPA + Redis Cluster.
"""
from __future__ import annotations

import json
import random
from locust import HttpUser, between, task, events

# ── Realistic engineering briefs for testing ──────────────────────────────────
BRIEFS = [
    "Design an aluminum heat sink for a 100W GPU. Max junction temp: 85°C. "
    "Air cooling at 3 m/s. Footprint: 120×80 mm.",

    "Design a cold gas thruster for a 3U CubeSat. Target thrust: 50 mN. "
    "Propellant: nitrogen. Isp > 65 s. Volume: 10×10×30 mm.",

    "Design a structural bracket for mounting a 5 kg avionics box. "
    "Max load: 500 N axial + 50 N·m moment. FOS ≥ 2.0. Material: Al 6061-T6.",

    "Design a heat exchanger for a power electronics module dissipating 2 kW. "
    "Inlet fluid temp: 25°C. Max surface temp: 80°C. Water cooling.",

    "Optimize fin geometry for an extruded aluminum heat sink cooling a "
    "200W motor controller. Constraint: max 15 cm total height. "
    "Minimize thermal resistance.",
]


class NEXUSEngineerUser(HttpUser):
    """
    Simulates an engineer using the NEXUS platform.

    Behavior:
      - 70% of time: health check + session list (read-heavy, cheap)
      - 20% of time: submit a new engineering brief (expensive — triggers pipeline)
      - 10% of time: fetch a specific session detail
    """
    wait_time = between(2, 8)   # realistic think time between actions

    def on_start(self):
        """Called when a simulated user starts. Fetch existing sessions for later GETs."""
        self._session_ids: list[str] = []
        resp = self.client.get("/api/v1/sessions", name="GET /sessions (warmup)")
        if resp.status_code == 200:
            try:
                sessions = resp.json()
                self._session_ids = [s["session_id"] for s in sessions[:10]]
            except Exception:
                pass

    # ── Health check — lightweight, validates backend is alive ────────────────
    @task(5)
    def health_check(self):
        self.client.get("/health", name="GET /health")

    # ── List sessions — most common read operation ─────────────────────────────
    @task(4)
    def list_sessions(self):
        self.client.get("/api/v1/sessions", name="GET /sessions")

    # ── List tool connections ──────────────────────────────────────────────────
    @task(3)
    def list_tools(self):
        self.client.get("/api/v1/tools", name="GET /tools")

    # ── Get session detail — requires a known session ID ──────────────────────
    @task(2)
    def get_session_detail(self):
        if not self._session_ids:
            return
        sid = random.choice(self._session_ids)
        self.client.get(f"/api/v1/sessions/{sid}", name="GET /sessions/{id}")

    # ── Submit new brief — triggers full 6-agent pipeline ─────────────────────
    @task(1)
    def submit_brief(self):
        brief = random.choice(BRIEFS)
        with self.client.post(
            "/api/v1/sessions",
            json={"engineering_brief": brief},
            name="POST /sessions (pipeline)",
            stream=True,          # SSE stream — read first event then close
            catch_response=True,  # Manually mark pass/fail
            timeout=30,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"Unexpected status {resp.status_code}")
                return

            # Read first SSE event to confirm pipeline started
            first_line = b""
            for chunk in resp.iter_content(chunk_size=512):
                first_line = chunk
                break  # Don't wait for full pipeline — just verify start

            if b'"type"' in first_line:
                resp.success()
                # Try to capture session_id for later GETs
                try:
                    raw = first_line.decode().lstrip("data:").strip()
                    event = json.loads(raw)
                    sid = event.get("session_id")
                    if sid and sid not in self._session_ids:
                        self._session_ids.append(sid)
                except Exception:
                    pass
            else:
                resp.failure("No SSE event in first chunk")


class NEXUSReadOnlyUser(HttpUser):
    """
    Read-only user — simulates monitoring dashboards / ops tooling.
    High frequency, lightweight. Good for testing read scalability.
    """
    wait_time = between(0.5, 2)

    @task(8)
    def health(self):
        self.client.get("/health", name="GET /health [monitor]")

    @task(3)
    def sessions(self):
        self.client.get("/api/v1/sessions", name="GET /sessions [monitor]")

    @task(1)
    def docs(self):
        self.client.get("/api/v1/knowledge/stats", name="GET /knowledge/stats [monitor]")


# ── Locust event hooks ─────────────────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n[NEXUS Load Test] Starting — target: http://localhost:8003")
    print("[NEXUS Load Test] Metrics: RPS, P50/P95/P99 latency, error rate")
    print("[NEXUS Load Test] Review Langfuse for per-session LLM token usage\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n[NEXUS Load Test] Complete")
    stats = environment.stats.total
    print(f"  Total requests: {stats.num_requests}")
    print(f"  Failures:       {stats.num_failures}")
    print(f"  P95 latency:    {stats.get_response_time_percentile(0.95):.0f} ms")
    print(f"  RPS (peak):     {stats.max_rps:.1f}")
