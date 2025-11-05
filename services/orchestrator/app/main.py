from fastapi import FastAPI
from .routers import applications, chat
from app.routers import clarifications
app = FastAPI(title="Orchestrator")

app.include_router(applications.router)
app.include_router(chat.router)   
app.include_router(clarifications.router)  

@app.get("/health")
def health():
    return {"status": "ok"}
