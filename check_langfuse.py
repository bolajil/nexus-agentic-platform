import os
from dotenv import load_dotenv
load_dotenv('backend/.env')

from langfuse import Langfuse
lf = Langfuse(
    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
    host=os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')
)

# Fetch recent traces and check user_id
traces = lf.fetch_traces(limit=10)
print("Recent traces:")
for t in traces.data:
    print(f"  {t.name[:35]:35} | User: {t.user_id or 'NONE'}")
