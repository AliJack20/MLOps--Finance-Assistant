# 📄 SECURITY.md

## 🔒 Security & Compliance

This document describes the security practices, safeguards, and responsible-AI measures implemented in the Financial Assistant application.
The system combines a Node.js backend, FastAPI ML service, LLM + RAG pipeline, and frontend UI.
Security, privacy, and safe AI output are enforced at every layer.

---

### 1. 🔐 Authentication & Access Control

#### 1.1 JWT-Based Route Protection
All backend routes that access user financial data are protected using **JWT authentication**.

Only authenticated users can access:
* Income & expense histories
* Dashboard stats
* Predictions
* LLM interactions

#### 1.2 Separation of Concerns
* The **frontend never communicates directly with the LLM**.
* All LLM requests go through the **Node backend**, which sanitizes and validates them.

#### 1.3 Least-Privilege Design
* The LLM **never sees database records**, PII, or raw user financial history directly unless explicitly required for a user-initiated query.
* Only minimal context (e.g., user query) is sent to the LLM.

---

### 2. 🛡️ Prompt Injection & LLM Safety

The system includes multiple layers to prevent prompt injection and unsafe LLM output.

#### 2.1 System Prompt Restrictions
The LLM is restricted to act as an **educational financial assistant**.
It refuses to provide:
* Personalized investment advice
* Financial decisions
* Legal or tax instructions

#### 2.2 Node “LLM Gateway” Guard
Before a request reaches the LLM, the Node backend:
* **Sanitizes user input**.
* **Strips dangerous patterns** (e.g., "ignore all previous instructions", "system:", "jailbreak").
* Ensures allowed query domain (**finance learning only**).

#### 2.3 RAG Grounding
Responses are grounded using retrieved financial documents. This reduces:
* Hallucinations
* Misinformation
* Prompt-injection effectiveness

#### 2.4 Output Validation
Before returning to the frontend:
* LLM answers are checked for safety violations.
* Disallowed content is filtered.
* Responses may be reframed into safe educational language.

---

### 3. 🔏 Data Privacy & Protection

#### 3.1 No Sensitive Logging
The system **never logs**:
* User transaction histories
* JWT tokens
* PII (name, email, financial records)
* LLM inputs or outputs

Only **operational metadata** (status, timestamps) is logged.

#### 3.2 Secure Storage
* Secrets and API keys are stored **only in `.env` files**.
* **No secrets** are committed to Git.

#### 3.3 Network Security
* **CORS** only allows trusted origins (frontend → backend).
* The **ML service is never exposed directly** to the internet.

---

### 4. 🔍 Dependency Security

#### 4.1 Node Dependency Audit
* We use `npm audit` to detect vulnerabilities in Node.js dependencies.
* High-severity findings must be resolved before deployment.

#### 4.2 Python Dependency Controls
* Python packages are pinned in `requirements.txt`.
* Updates are applied manually during development cycles.
* No dynamic dependency installation occurs in production.

#### 4.3 Environment Isolation
The FastAPI ML service runs inside a virtual environment, ensuring:
* Isolated dependencies
* No system-level contamination
* Predictable versioning

> **Note:** We do not use `pip-audit` in CI, but dependency safety is maintained through version pinning, manual review, and environment isolation.

---

### 5. 🤖 Responsible AI Guidelines & Guardrails

#### 5.1 Educational-Only Assistant
The LLM is explicitly instructed to:
* Provide only **high-level financial education**.
* **Never** give prescriptive financial, investment, or tax advice.
* Avoid predicting or influencing user decisions.

#### 5.2 Harmful Content Filters
The system blocks:
* Self-harm or dangerous activity queries
* Illegal or unethical content
* Hate or harassment
* Attempts to misuse the AI for harmful purposes

#### 5.3 Hallucination Reduction
Achieved through:
* **RAG retrieval**
* **Strict system prompts**
* **Output validation**

If insufficient context is available, the LLM responds with:
> “I’m not sure about that.”

#### 5.4 Transparency
The system can return the retrieved context used to generate the answer for added explainability.

---

### 6. 🧪 API Security

#### 6.1 Backend → ML Service Traffic
The Node backend **exclusively controls** calls to the FastAPI ML service. This prevents the frontend or attackers from abusing ML endpoints directly.

#### 6.2 Payload Validation
All financial inputs & prediction requests are validated before processing.