# File: backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from .core.config.settings import settings
from .api.v1 import business_plans, evaluations, projects, scores

# 加载环境变量
load_dotenv()

# 创建FastAPI应用
app = FastAPI(
    title="PitchAI 后端 API",
    description="PitchAI项目评审系统后端API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS - MOVED TO TOP AND IMPROVED
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",  # Alternative localhost
        "http://localhost:3001",  # Mock server
        "http://127.0.0.1:3001",  # Alternative localhost
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Alternative: Allow all origins for development (less secure but simpler)
# Uncomment this and comment out the above if you still have issues:
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=False,  # Must be False when allow_origins=["*"]
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# 健康检查
@app.get("/ping", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}

# 根路径重定向到文档
@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "PitchAI API Server",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/ping"
    }

# API健康检查
@app.get(f"{settings.API_PREFIX}/ping", tags=["Health"])
def health_check_api():
    return {"status": "ok", "version": "1.0.0", "api_prefix": settings.API_PREFIX}

# 注册路由
app.include_router(
    projects.router, prefix=settings.API_PREFIX, tags=["项目管理"]
)

app.include_router(
    scores.router, prefix=settings.API_PREFIX, tags=["评分管理"]
)

app.include_router(
    business_plans.router, prefix=settings.API_PREFIX, tags=["商业计划书"]
)

app.include_router(
    evaluations.router, prefix=settings.API_PREFIX, tags=["评估"]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)