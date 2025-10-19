from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from keycloak import KeycloakOpenID
import asyncpg
import os
from datetime import datetime, date
import traceback
import jwt

# --- Конфигурация ---
app = FastAPI(title="BionicPRO Reporting API")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Конфигурация Keycloak
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://keycloak:8080/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "reports-api")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{KEYCLOAK_SERVER_URL}realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"
)
keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_SERVER_URL,
    client_id=KEYCLOAK_CLIENT_ID,
    realm_name=KEYCLOAK_REALM
)

# Конфигурация БД
DATABASE_CONFIG = {
    'user': os.getenv('OLAP_DB_USER', 'olap_user'), 'password': os.getenv('OLAP_DB_PASSWORD', 'olap_password'),
    'database': os.getenv('OLAP_DB_NAME', 'olap_db'), 'host': os.getenv('OLAP_DB_HOST', 'postgres_olap'), 'port': 5432
}

class Report(BaseModel):
    user_id: int; user_name: str | None = None; prosthesis_model: str | None = None
    avg_daily_usage: float | None = None; max_signal_value: float | None = None
    last_seen_date: str | None = None; report_updated_at: str | None = None

# --- Зависимости и API ---

async def get_current_user_info(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        raw_key = keycloak_openid.public_key()
        pem_key = f"-----BEGIN PUBLIC KEY-----\n{raw_key}\n-----END PUBLIC KEY-----"
        
        # --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ---
        # Мы НЕ передаем 'audience', чтобы PyJWT не проверял 'aud' claim
        return jwt.decode(
            token,
            pem_key,
            algorithms=["RS256"],
            options={"verify_signature": True, "verify_exp": True, "verify_iss": False}
        )
    except jwt.InvalidTokenError as e:
        print(f"!!! JWT Invalid: {e} !!!")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")
    except Exception as e:
        print(f"!!! Unexpected token validation error: {e} !!!")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate credentials: {e}")

@app.get("/reports", response_model=Report)
async def get_report_for_current_user(user_info: dict = Depends(get_current_user_info)):
    user_roles = user_info.get("realm_access", {}).get("roles", [])
    if "prothetic_user" not in user_roles:
        raise HTTPException(status_code=403, detail="Forbidden: User does not have the required role.")

    user_id_from_token_str = user_info.get("user_id")
    if not user_id_from_token_str:
        raise HTTPException(status_code=403, detail="Forbidden: User ID not found in token.")
    
    try:
        user_id = int(user_id_from_token_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid user ID format in token.")

    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        record = await conn.fetchrow("SELECT * FROM user_reports_mart WHERE user_id = $1", user_id)
        await conn.close()
        
        if record is None:
            raise HTTPException(status_code=404, detail=f"Report for user_id {user_id} not found")
        
        record_dict = dict(record)
        for key in ['last_seen_date', 'report_updated_at']:
            value = record_dict.get(key)
            if isinstance(value, (datetime, date)):
                record_dict[key] = value.isoformat()
        
        return record_dict
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database or internal error: {e}")

