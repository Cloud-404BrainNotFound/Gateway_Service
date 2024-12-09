from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import jwt
import json
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
    "order": "http://localhost:8008",
    "composite": "http://localhost:7999",
}

# JWT 验证
async def verify_jwt(authorization: str = Header(None)):
    print("Auth header:", authorization)
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    try:
        token = authorization.split(' ')[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        print("Token payload:", payload)
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

@app.get("/api/users/{user")
async def get_user(username: str, user = Depends(verify_jwt)):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SERVICES['user']}/users/{username}",
            headers={"X-User-Id": user["sub"]}
        )
        return response.json()


# 不需要验证的路由
@app.post("/api/orders/order_stringing", status_code=201)
async def create_order(request: Request):
    print("Gateway received create order request")

    try:
        request_data = await request.json()
        request_data["user_id"] = user["sub"] 

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SERVICES['composite']}/orders/order_stringing",
                json=await request.json()
            )
            print("Gateway forwarded response")
            return response.json()
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504,
            detail="Service timeout - The request took too long to complete"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )
# 需要验证的路由
@app.get("/api/orders/{order_id}")
async def get_order(order_id: str, user=Depends(verify_jwt)):
    print(f"Gateway received get order request for order {order_id}")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SERVICES['composite']}/orders/{order_id}",
            headers={"X-User-Id": user["sub"]}
        )
        print("Gateway forwarded response")
        return response.json()

@app.put("/api/orders/{order_id}")
async def update_order(order_id: str, request: Request, user=Depends(verify_jwt)):
    print(f"Gateway received update order request for order {order_id}")
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{SERVICES['composite']}/orders/{order_id}",
            json=await request.json(),
            headers={"X-User-Id": user["sub"]}
        )
        print("Gateway forwarded response")
        return response.json()

@app.delete("/api/orders/{order_id}", status_code=204)
async def delete_order(order_id: str, user=Depends(verify_jwt)):
    print(f"Gateway received delete order request for order {order_id}")
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{SERVICES['composite']}/orders/{order_id}",
            headers={"X-User-Id": user["sub"]}
        )
        print("Gateway forwarded response")
        return {"message": "Order deleted successfully"}

# 
@app.get("/api/orders/user/{user_id}")
async def get_user_orders(user_id: str, user = Depends(verify_jwt)):
    # 验证请求用户是否在查看自己的订单
    if user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view these orders")
        
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SERVICES['composite']}/composite/orders/user/{user_id}",  # 注意路径包含 composite 前缀
                headers={
                    "X-User-Id": user["sub"],
                    "X-User-Role": user["role"]
                }
            )
            return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )