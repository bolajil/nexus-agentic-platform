"""
Langfuse v3 connection test.
Run: python test_langfuse.py
"""
import os, sys

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

pk   = os.getenv("LANGFUSE_PUBLIC_KEY", "")
sk   = os.getenv("LANGFUSE_SECRET_KEY", "")
host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

if not pk or not sk:
    print("ERROR: LANGFUSE_PUBLIC_KEY or SECRET_KEY not in backend/.env")
    sys.exit(1)

from langfuse import Langfuse
import langfuse.version as _v
ver = getattr(_v, '__version__', None) or getattr(_v, 'VERSION', '?')
print(f"langfuse version : {ver}")
print(f"public key       : {pk[:12]}...")

lf = Langfuse(public_key=pk, secret_key=sk, host=host)

# Step 1: verify auth
try:
    lf.auth_check()
    print("auth_check       : OK")
except Exception as e:
    print(f"auth_check FAILED: {e}")
    sys.exit(1)

# Step 2: send a test span (v3 API)
try:
    span = lf.start_span(
        name="nexus-connection-test",
        metadata={"source": "test_langfuse.py", "platform": "nexus"},
    )
    span.update(output="NEXUS → Langfuse v3 connection verified OK")
    span.end()
    lf.flush()
    print(f"trace sent       : OK  (span id: {span.id})")
    print("\nCheck Langfuse dashboard → Tracing for 'nexus-connection-test'")
    print("Then restart uvicorn and run a pipeline — 6 agent traces will appear.")
except Exception as e:
    print(f"ERROR sending trace: {e}")
    import traceback; traceback.print_exc()
    sys.exit(1)
