from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import jwt
import json
import os
from dotenv import load_dotenv
import jwt.exceptions  # Ensure this is imported
import jwt as PyJWT  # or just use PyJWT directly


load_dotenv()

# Add validation for JWT_SECRET_KEY
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is not set")
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

app = FastAPI()

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
    "user": "http://3.80.156.123:8001",  
    "order": "http://3.80.156.123:8004",
    "composite": "http://3.80.156.123:7999",
}

# JWT 验证
async def verify_jwt(authorization: str = Header(None)):
    print("Authorization header:", authorization)
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    try:
        token = str(authorization.split(' ')[1])  # Explicitly convert to string
        print(f"Token type: {type(token)}")  # Debug token type
        print(f"Token value: {token}")  # Debug full token value
        print(f"Secret key type: {type(JWT_SECRET_KEY)}")  # Debug secret key type
        print(f"Secret key value: {JWT_SECRET_KEY}")  # Debug secret key value
            
        payload = jwt.decode(
            token.encode('utf-8') if isinstance(token, str) else token,
            JWT_SECRET_KEY.encode('utf-8') if isinstance(JWT_SECRET_KEY, str) else JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        print(f"Successfully decoded token payload: {payload}")
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        print(f"Invalid token error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        print(f"Unexpected error during JWT verification: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# 不需要验证的路由
@app.post("/api/users/login/google")
async def google_login(request: Request):
    request_body = await request.json()
    print("Gateway received login request with body:", request_body)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{SERVICES['user']}/users/login/google",
                json=request_body,
                timeout=10.0  # Add timeout
            )
            
            # Debug response
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.content}")
            
            # Check if response is successful
            response.raise_for_status()
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON response: {e}")
                print(f"Raw response content: {response.content}")
                raise HTTPException(
                    status_code=500,
                    detail="Invalid response from authentication service"
                )
            
            if "user_id" not in data:
                raise HTTPException(
                    status_code=500,
                    detail="User ID missing in login response"
                )
            
            return {
                "message": "Login successful",
                "access_token": data.get("access_token"),
                "user_id": data.get("user_id")
            }
            
        except httpx.RequestError as e:
            print(f"Request failed: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Service unavailable: {str(e)}"
            )
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {str(e)}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Authentication service error: {str(e)}"
            )

@app.post("/api/users/login/email")
async def email_login(request: Request):
    form_data = await request.form()
    print("Gateway received login request with form data:", dict(form_data))
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERVICES['user']}/users/login/email",
            data=await request.form()
        )
        print("Gateway forwarded response") 
        
        data = response.json()

        if "user_id" not in data:
            raise HTTPException(status_code=500, detail="User ID missing in login response")

        return {
            "access_token": data.get("access_token"),  # JWT Token
            "user_id": data.get("user_id")            # User ID to return to frontend
        }

# 需要验证的路由
@app.get("/api/users/{username}")
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
    request_body = await request.json()
    print("Gateway received create order request with body:", request_body)
    try:
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
    request_body = await request.json()
    print(f"Gateway received update order request for order {order_id} with body:", request_body)
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

# 获取用户名
@app.get("/api/users/{user_id}/username")
async def get_username(user_id: str, user=Depends(verify_jwt)):
    """
    Fetch the username of the user identified by user_id.
    """
    print(f"Gateway received request to get username for user {user_id}")
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SERVICES['user']}/users/{user_id}/username",
            headers={"X-User-Id": user["sub"]}
        )
        print("Gateway forwarded response for username")
        return response.json()

# 获取用户邮箱
@app.get("/api/users/{user_id}/email")
async def get_email(request: Request, user_id: str, user=Depends(verify_jwt)):
    """
    Fetch the email of the user identified by user_id.
    """
    print(f"Gateway received request to get email for user {user_id}")
    print("Request headers:", dict(request.headers))  # Print all headers

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SERVICES['user']}/users/{user_id}",
            headers={"X-User-Id": user["sub"]}
        )
        print("Response headers:", dict(response.headers))  # Print response headers
        print("Response body:", response.text)  # Print response body
        return response.json()
