"""WorkFlowOS Backend Entry Point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes_events import router as events_router
from .api.routes_workflows import router as workflows_router
from .api.routes_execution import router as execution_router

app = FastAPI(
    title="WorkFlowOS API",
    description="AI-Powered Desktop Workflow Automation Engine",
    version="0.1.0",
)

# Enable CORS for frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(execution_router, prefix="/api")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "WorkFlowOS"}
