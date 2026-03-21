# Milkdown Editor Test

> Testing all common Markdown elements to verify Milkdown renders correctly in VSCode.

---

## 1. Text Formatting

Normal text with **bold**, *italic*, ~~strikethrough~~, and `inline code`.

Combined: **_bold italic_** and **`bold code`**.

---

## 2. Headings

# H1 Heading
## H2 Heading
### H3 Heading
#### H4 Heading

---

## 3. Lists

**Unordered:**
- Item one
- Item two
  - Nested item A
  - Nested item B
- Item three

**Ordered:**
1. First step
2. Second step
   1. Sub-step
   2. Sub-step
3. Third step

**Task list:**
- [x] BM25 hybrid search ✅
- [x] JWT auth system ✅
- [x] Cloud deployment IaC ✅
- [ ] Test auth flow on staging

---

## 4. Code Blocks

```python
# NEXUS — bcrypt password hash example
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

```typescript
// AuthContext — save JWT session
const _saveSession = (data: TokenResponse) => {
  localStorage.setItem('nexus_access_token', data.access_token);
  localStorage.setItem('nexus_user', JSON.stringify(data.user));
  setUser(data.user);
};
```

---

## 5. Table

| Component | Cloud | Tech | Status |
|-----------|-------|------|--------|
| Kubernetes cluster | AWS | EKS 1.29 | ✅ Ready |
| Kubernetes cluster | GCP | GKE Autopilot | ✅ Ready |
| Kubernetes cluster | Azure | AKS 1.29 | ✅ Ready |
| Redis HA | AWS | ElastiCache r7g | ✅ Ready |
| Redis HA | GCP | Memorystore | ✅ Ready |
| Object storage | AWS | S3 + KMS | ✅ Ready |
| Container registry | Azure | ACR Premium | ✅ Ready |

---

## 6. Blockquotes

> **Architecture principle:** Auth is secured at the JWT layer (15-min access tokens, rotating refresh tokens) and at the network layer (WAFv2 rate limiting, HSTS, CSP headers).
>
> Secrets never touch source code — all loaded from AWS Secrets Manager / GCP Secret Manager / Azure Key Vault via External Secrets Operator.

---

## 7. Links & Images

[NEXUS GitHub repo](https://github.com/bolajil/nexus-agentic-platform)

[FastAPI docs](https://fastapi.tiangolo.com) · [LangGraph](https://langchain-ai.github.io/langgraph/) · [Terraform](https://terraform.io)

---

## 8. Horizontal Rules & Line Breaks

Section one content.

---

Section two content.

---

## 9. Inline HTML (if supported)

<details>
<summary>Click to expand — NEXUS agent pipeline summary</summary>

1. **Requirements Agent** — parses engineering brief with GPT-4o
2. **Research Agent** — BM25 + semantic hybrid RAG search
3. **Design Agent** — physics-based parameter calculation
4. **Simulation Agent** — NumPy/SciPy domain simulation
5. **Optimization Agent** — Pareto-front multi-objective sweep
6. **Report Agent** — structured JSON engineering report

</details>

---

## 10. Math (if Milkdown plugin enabled)

Reciprocal Rank Fusion score:

$$\text{RRF}(d) = \sum_{i} \frac{w_i}{k + \text{rank}_i(d)}$$

where $k = 60$, $w_{\text{semantic}} = 0.6$, $w_{\text{BM25}} = 0.4$.

---

*If all sections above render with proper formatting — headings, bold/italic, tables, code highlighting, task checkboxes, and blockquotes — Milkdown is working correctly.*
