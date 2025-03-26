# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from fastapi.routing import APIRoute 

# Load environment variables
load_dotenv()

# Import database connection
from app.database import Base, engine

# Import models to register them with SQLAlchemy
from app.models.database import ForecastScenario, Parameters, MonthlyData, YearlySummary
from app.models.user import User

# Import all routes
from app.routes import router

# Initialize FastAPI app
app = FastAPI(title="RYZE.ai Financial Forecast API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the database tables are created
Base.metadata.create_all(bind=engine)

# Include all routes
app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Welcome to RYZE.ai Financial Forecast API"}

@app.get("/routes", tags=["Utility"])
async def get_routes():
    route_info = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = list(route.methods)
            route_info.append({
                "path": route.path,
                "methods": methods,
                "name": route.name
            })
    return {"routes": route_info}