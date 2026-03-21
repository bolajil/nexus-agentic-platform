"""
NEXUS Platform — Production Load Testing Suite
===============================================
Comprehensive load testing with authentication, full API coverage,
error scenarios, and production-grade metrics.

Run (Basic):
    pip install locust
    cd backend/tests
    locust -f locustfile.py --host http://localhost:8003

Run (Production - Headless with HTML report):
    locust -f locustfile.py --host http://localhost:8003 \
           --headless -u 50 -r 5 -t 10m \
           --html=load_test_report.html

Run (Staged Load Profile):
    locust -f locustfile.py --host http://localhost:8003 \
           --headless --step-load --step-users 10 --step-time 60s

UI URLs:
    Locust UI:      http://localhost:8089
    Backend API:    http://localhost:8003/docs
    Frontend:       http://localhost:3002
    Langfuse:       https://cloud.langfuse.com

Production SLOs:
    - P95 latency: < 500ms (read), < 30s (pipeline)
    - Error rate: < 1%
    - Availability: 99.9%

Architecture note (for interviews):
  Single uvicorn worker handles ~10-20 concurrent SSE streams via asyncio.
  Scale to 50-100 concurrent users with:
      uvicorn app.main:app --workers 4 (requires Redis for shared session store)
  Scale to 200-500 with Kubernetes HPA + Redis Cluster.
"""
from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime
from typing import Optional

from locust import HttpUser, between, task, events, LoadTestShape

# ── Test Configuration ────────────────────────────────────────────────────────
TEST_USER_EMAIL = os.getenv("TEST_USER_EMAIL", "loadtest@nexus.ai")
TEST_USER_PASSWORD = os.getenv("TEST_USER_PASSWORD", "LoadTest123!")
FAIL_ON_ERROR_RATE = float(os.getenv("FAIL_ON_ERROR_RATE", "0.01"))  # 1%
P95_THRESHOLD_MS = int(os.getenv("P95_THRESHOLD_MS", "500"))

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

    "Design a PCB thermal via array for a 50W power amplifier. "
    "Board thickness: 1.6mm. Target thermal resistance: < 5°C/W.",

    "Design a liquid cooling loop for a 500W server rack. "
    "Inlet temp: 20°C. Max component temp: 70°C. Flow rate: 2 L/min.",
]

# ── Invalid inputs for error testing ──────────────────────────────────────────
INVALID_BRIEFS = [
    "",  # Empty
    "x" * 10,  # Too short
    "x" * 50000,  # Too long
]


class NEXUSAuthenticatedUser(HttpUser):
    """
    Production user with full authentication flow.
    Tests login, authenticated requests, and token refresh.
    """
    wait_time = between(2, 8)
    weight = 3  # 3x more likely than other user types

    def on_start(self):
        """Login and setup authenticated session."""
        self._token: Optional[str] = None
        self._session_ids: list[str] = []
        self._login()

    def _login(self):
        """Authenticate and store JWT token."""
        with self.client.post(
            "/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
            name="POST /auth/login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    self._token = data.get("access_token")
                    resp.success()
                except Exception as e:
                    resp.failure(f"Login parse error: {e}")
            elif resp.status_code == 401:
                resp.success()  # Expected if user doesn't exist
            else:
                resp.failure(f"Login failed: {resp.status_code}")

    def _auth_headers(self) -> dict:
        """Return headers with auth token if available."""
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    # ── Authenticated endpoints ───────────────────────────────────────────────
    @task(5)
    def get_current_user(self):
        """Test /auth/me endpoint."""
        if not self._token:
            return
        self.client.get(
            "/api/auth/me",
            headers=self._auth_headers(),
            name="GET /auth/me"
        )

    @task(8)
    def list_sessions_auth(self):
        """List sessions with authentication."""
        self.client.get(
            "/api/v1/sessions",
            headers=self._auth_headers(),
            name="GET /sessions [auth]"
        )

    @task(3)
    def submit_brief_auth(self):
        """Submit engineering brief with authentication."""
        brief = random.choice(BRIEFS)
        with self.client.post(
            "/api/v1/sessions",
            json={"engineering_brief": brief},
            headers=self._auth_headers(),
            name="POST /sessions [auth]",
            stream=True,
            catch_response=True,
            timeout=60,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"Status {resp.status_code}")
                return
            # Read first SSE event
            for chunk in resp.iter_content(chunk_size=512):
                if b'"type"' in chunk:
                    resp.success()
                    try:
                        raw = chunk.decode().lstrip("data:").strip()
                        event = json.loads(raw)
                        sid = event.get("session_id")
                        if sid:
                            self._session_ids.append(sid)
                    except Exception:
                        pass
                break

    @task(2)
    def get_session_provenance(self):
        """Test provenance endpoint."""
        if not self._session_ids:
            return
        sid = random.choice(self._session_ids)
        self.client.get(
            f"/api/v1/sessions/{sid}/provenance",
            headers=self._auth_headers(),
            name="GET /sessions/{id}/provenance"
        )

    @task(2)
    def search_knowledge(self):
        """Test RAG knowledge search."""
        queries = ["thermal management", "structural analysis", "propulsion", "PCB design"]
        self.client.post(
            "/api/v1/knowledge/search",
            json={"query": random.choice(queries), "top_k": 5},
            headers=self._auth_headers(),
            name="POST /knowledge/search"
        )

    @task(1)
    def get_reviews(self):
        """Test reviews endpoint."""
        if not self._session_ids:
            return
        sid = random.choice(self._session_ids)
        self.client.get(
            f"/api/v1/reviews/{sid}",
            headers=self._auth_headers(),
            name="GET /reviews/{id}"
        )

    @task(1)
    def get_integrations(self):
        """Test integrations endpoint."""
        self.client.get(
            "/api/v1/integrations",
            headers=self._auth_headers(),
            name="GET /integrations"
        )


class NEXUSEngineerUser(HttpUser):
    """
    Simulates an engineer using the NEXUS platform (unauthenticated).
    Tests core functionality without auth.
    """
    wait_time = between(2, 8)
    weight = 2

    def on_start(self):
        """Fetch existing sessions for later GETs."""
        self._session_ids: list[str] = []
        resp = self.client.get("/api/v1/sessions", name="GET /sessions (warmup)")
        if resp.status_code == 200:
            try:
                sessions = resp.json()
                self._session_ids = [s.get("session_id") or s.get("id") for s in sessions[:10]]
            except Exception:
                pass

    @task(5)
    def health_check(self):
        self.client.get("/health", name="GET /health")

    @task(1)
    def ready_check(self):
        self.client.get("/ready", name="GET /ready")

    @task(4)
    def list_sessions(self):
        self.client.get("/api/v1/sessions", name="GET /sessions")

    @task(3)
    def list_tools(self):
        self.client.get("/api/v1/tools", name="GET /tools")

    @task(2)
    def get_session_detail(self):
        if not self._session_ids:
            return
        sid = random.choice(self._session_ids)
        self.client.get(f"/api/v1/sessions/{sid}", name="GET /sessions/{id}")

    @task(2)
    def get_knowledge_stats(self):
        self.client.get("/api/v1/knowledge/stats", name="GET /knowledge/stats")

    @task(1)
    def submit_brief(self):
        brief = random.choice(BRIEFS)
        with self.client.post(
            "/api/v1/sessions",
            json={"engineering_brief": brief},
            name="POST /sessions (pipeline)",
            stream=True,
            catch_response=True,
            timeout=60,
        ) as resp:
            if resp.status_code not in (200, 201):
                resp.failure(f"Status {resp.status_code}")
                return
            for chunk in resp.iter_content(chunk_size=512):
                if b'"type"' in chunk:
                    resp.success()
                    try:
                        raw = chunk.decode().lstrip("data:").strip()
                        event = json.loads(raw)
                        sid = event.get("session_id")
                        if sid:
                            self._session_ids.append(sid)
                    except Exception:
                        pass
                break


class NEXUSErrorTester(HttpUser):
    """
    Tests error handling and edge cases.
    Verifies the API handles bad input gracefully.
    """
    wait_time = between(5, 15)
    weight = 1

    @task(3)
    def invalid_brief_empty(self):
        """Test empty brief rejection."""
        with self.client.post(
            "/api/v1/sessions",
            json={"engineering_brief": ""},
            name="POST /sessions [invalid:empty]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 422:
                resp.success()  # Expected validation error
            else:
                resp.failure(f"Expected 422, got {resp.status_code}")

    @task(2)
    def invalid_brief_short(self):
        """Test too-short brief rejection."""
        with self.client.post(
            "/api/v1/sessions",
            json={"engineering_brief": "x" * 10},
            name="POST /sessions [invalid:short]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 422:
                resp.success()
            else:
                resp.failure(f"Expected 422, got {resp.status_code}")

    @task(2)
    def invalid_session_id(self):
        """Test invalid session ID handling."""
        with self.client.get(
            "/api/v1/sessions/invalid-uuid-12345",
            name="GET /sessions/{invalid}",
            catch_response=True,
        ) as resp:
            if resp.status_code in (404, 422):
                resp.success()
            else:
                resp.failure(f"Expected 404/422, got {resp.status_code}")

    @task(1)
    def invalid_auth_token(self):
        """Test invalid auth token handling."""
        with self.client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token-xyz"},
            name="GET /auth/me [invalid]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 401:
                resp.success()
            else:
                resp.failure(f"Expected 401, got {resp.status_code}")

    @task(1)
    def missing_required_field(self):
        """Test missing required field handling."""
        with self.client.post(
            "/api/v1/sessions",
            json={},  # Missing engineering_brief
            name="POST /sessions [invalid:missing]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 422:
                resp.success()
            else:
                resp.failure(f"Expected 422, got {resp.status_code}")


class NEXUSReadOnlyUser(HttpUser):
    """
    Read-only user — simulates monitoring dashboards / ops tooling.
    High frequency, lightweight. Good for testing read scalability.
    """
    wait_time = between(0.5, 2)
    weight = 1

    @task(8)
    def health(self):
        self.client.get("/health", name="GET /health [monitor]")

    @task(3)
    def sessions(self):
        self.client.get("/api/v1/sessions", name="GET /sessions [monitor]")

    @task(2)
    def knowledge_stats(self):
        self.client.get("/api/v1/knowledge/stats", name="GET /knowledge/stats [monitor]")

    @task(1)
    def langfuse_status(self):
        self.client.get("/api/v1/langfuse/status", name="GET /langfuse/status [monitor]")


# ── Staged Load Profile (Production) ──────────────────────────────────────────

class ProductionLoadProfile(LoadTestShape):
    """
    Production load profile with staged ramp-up:
      0-2 min:  Ramp to 20 users
      2-5 min:  Ramp to 50 users
      5-10 min: Sustain 50 users (steady state)
      10-12 min: Ramp to 100 users (peak)
      12-15 min: Sustain 100 users
      15-17 min: Cool down to 20 users
      17-18 min: Complete
    """
    stages = [
        {"duration": 120, "users": 20, "spawn_rate": 2},
        {"duration": 300, "users": 50, "spawn_rate": 3},
        {"duration": 600, "users": 50, "spawn_rate": 5},
        {"duration": 720, "users": 100, "spawn_rate": 5},
        {"duration": 900, "users": 100, "spawn_rate": 5},
        {"duration": 1020, "users": 20, "spawn_rate": 5},
        {"duration": 1080, "users": 0, "spawn_rate": 5},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None


# ── Locust Event Hooks ────────────────────────────────────────────────────────

test_start_time = None
metrics_log = []

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    global test_start_time
    test_start_time = datetime.utcnow()
    print("\n" + "="*70)
    print("  NEXUS Platform — Production Load Test")
    print("="*70)
    print(f"  Start time:     {test_start_time.isoformat()}")
    print(f"  Target host:    {environment.host}")
    print(f"  Error threshold: {FAIL_ON_ERROR_RATE*100:.1f}%")
    print(f"  P95 threshold:  {P95_THRESHOLD_MS} ms")
    print("="*70)
    print("\n  UI Links:")
    print("    Locust:     http://localhost:8089")
    print("    API Docs:   http://localhost:8003/docs")
    print("    Frontend:   http://localhost:3002")
    print("    Langfuse:   https://cloud.langfuse.com")
    print("\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    duration = (datetime.utcnow() - test_start_time).total_seconds() if test_start_time else 0
    error_rate = stats.fail_ratio if stats.num_requests > 0 else 0
    p95 = stats.get_response_time_percentile(0.95)
    p99 = stats.get_response_time_percentile(0.99)

    print("\n" + "="*70)
    print("  NEXUS Load Test — Final Report")
    print("="*70)
    print(f"  Duration:       {duration:.0f}s ({duration/60:.1f} min)")
    print(f"  Total requests: {stats.num_requests:,}")
    print(f"  Failures:       {stats.num_failures:,} ({error_rate*100:.2f}%)")
    print(f"  RPS (avg):      {stats.total_rps:.1f}")
    print(f"  RPS (peak):     {stats.max_rps:.1f}")
    print("-"*70)
    print("  Latency:")
    print(f"    P50:          {stats.get_response_time_percentile(0.50):.0f} ms")
    print(f"    P95:          {p95:.0f} ms")
    print(f"    P99:          {p99:.0f} ms")
    print(f"    Max:          {stats.max_response_time:.0f} ms")
    print("-"*70)

    # SLO Check
    slo_pass = True
    if error_rate > FAIL_ON_ERROR_RATE:
        print(f"  ❌ FAIL: Error rate {error_rate*100:.2f}% > {FAIL_ON_ERROR_RATE*100:.1f}%")
        slo_pass = False
    else:
        print(f"  ✅ PASS: Error rate {error_rate*100:.2f}% <= {FAIL_ON_ERROR_RATE*100:.1f}%")

    if p95 > P95_THRESHOLD_MS:
        print(f"  ❌ FAIL: P95 latency {p95:.0f}ms > {P95_THRESHOLD_MS}ms")
        slo_pass = False
    else:
        print(f"  ✅ PASS: P95 latency {p95:.0f}ms <= {P95_THRESHOLD_MS}ms")

    print("="*70)
    if slo_pass:
        print("  🎉 ALL SLOs PASSED — Ready for production")
    else:
        print("  ⚠️  SLO VIOLATIONS — Review before production")
    print("="*70 + "\n")
