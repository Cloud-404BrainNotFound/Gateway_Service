from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 从环境变量获取密钥
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

# CORS 设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 服务地址配置
SERVICES = {
    "user": "http://localhost:8000",  
}

# JWT 验证
async def verify_jwt(authorization: str = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        token = authorization.split(' ')[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# 不需要验证的路由
@app.post("/api/users/login/google")
async def google_login(request: Request):
    print("Gateway received login request")
    async with httpx.AsyncClient() as client:
        
        response = await client.post(
            f"{SERVICES['user']}/users/login/google",
            json=await request.json()
        )
        print("Gateway forwarded response") 
        return response.json()

@app.post("/api/users/login/email")
async def email_login(request: Request):
    print("Gateway received login request")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERVICES['user']}/users/login/email",
            data=await request.form()
        )
        print("Gateway forwarded response") 
        return response.json()

# 需要验证的路由
@app.get("/api/users/{username}")
async def get_user(username: str, user = Depends(verify_jwt)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SERVICES['user']}/users/{username}",
            headers={"X-User-Id": user["sub"]}
        )
        return response.json()