from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager

app = FastAPI()

# ✅ Register Prometheus instrumentation BEFORE startup
instrumentator = Instrumentator().instrument(app).expose(app)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # You could put startup/shutdown logic here if needed
    yield

app.router.lifespan_context = lifespan

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def hello():
    return {"message": "Hello from FastAPI Docker!"}
