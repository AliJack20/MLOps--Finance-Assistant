# tests/test_api.py
import sys
import json
import numpy as np
from pathlib import Path

# Ensure project root is on sys.path so "import src.api" works
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Import the app module
import src.api as api_mod
from fastapi.testclient import TestClient

# -------------------------
# Test doubles / stubs
# -------------------------
def dummy_load_model():
    class DummyModel:
        def predict(self, df):
            return np.array([42.42])
    return DummyModel()

class StubRAG:
    def __init__(self, docs_folder=None, index_path=None):
        self.docs_folder = docs_folder
        self.index_path = index_path

    def build_index_if_missing(self):
        # intentionally no-op
        return

    def query(self, q, k=4):
        context = "Source: training_case_0\nContent: Example context about personal finance."
        prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{q}\n\nAnswer concisely."
        return {"context": context, "prompt": prompt}

class StubLLMAdapter:
    def __init__(self):
        self.model_id = "stub-model"

    def generate(self, user_message, system_prompt="", max_tokens=200, temperature=0.7):
        return "This is a stubbed LLM answer."

# -------------------------
# Monkeypatch the app BEFORE TestClient startup runs
# -------------------------
# Prevent the real startup_event from running (so it won't overwrite our stubs or call external services).
async def _noop_startup_event():
    # intentionally do nothing in tests
    return None

api_mod.startup_event = _noop_startup_event

# Inject test doubles directly into module globals used by endpoints
api_mod.load_model = dummy_load_model
api_mod.model = dummy_load_model()       # pre-populate model used by /predict
api_mod.rag = StubRAG()                  # used by /qa
api_mod.hf_llm = StubLLMAdapter()        # used by /qa

# Create TestClient (startup_event is a no-op)
client = TestClient(api_mod.app)

# -------------------------
# Tests
# -------------------------
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}
    print("/health:", r.json())

def test_qa_endpoint():
    payload = {"query": "How much did I spend on burgers?"}
    r = client.post("/qa", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "answer" in body and "context" in body
    assert body["answer"] == "This is a stubbed LLM answer."
    print("/qa response:", json.dumps(body, indent=2))

def test_predict_endpoint():
    payload = {"actual_spending": 100.0}
    r = client.post("/predict", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "prediction_next_week" in body
    assert abs(body["prediction_next_week"] - 42.42) < 1e-6
    print("/predict response:", body)

def test_metrics_endpoint():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")
    print("/metrics: ok (content-length)", len(r.content))

if __name__ == "__main__":
    test_health()
    test_qa_endpoint()
    test_predict_endpoint()
    test_metrics_endpoint()
    print("All tests ran successfully.")
