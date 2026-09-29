from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from backend.models.database import check_database_connection
from backend.routers.materials import router as materials_router
from backend.routers.questions import router as questions_router
from backend.routers.answers import router as answers_router

app = FastAPI(
    title="Study AI API",
    description="API para a plataforma de estudos com inteligência artificial.",
    version="0.1.0",
)

    
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(materials_router)
app.include_router(questions_router)
app.include_router(answers_router)


@app.get("/")
def home():
    return {
        "message": "Study AI API está funcionando!",
        "status": "online",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/db-health")
def database_health_check():
    try:
        result = check_database_connection()

        if result != 1:
            raise HTTPException(
                status_code=503,
                detail="O banco de dados não respondeu corretamente.",
            )

        return {
            "database": "connected",
            "status": "healthy",
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível conectar ao banco de dados.",
        )
