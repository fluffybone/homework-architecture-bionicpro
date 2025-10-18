from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncpg
import os
from datetime import datetime, date

# --- Конфигурация и модель ---

app = FastAPI(title="BionicPRO Reporting API")

DATABASE_CONFIG = {
    'user': os.getenv('OLAP_DB_USER', 'olap_user'),
    'password': os.getenv('OLAP_DB_PASSWORD', 'olap_password'),
    'database': os.getenv('OLAP_DB_NAME', 'olap_db'),
    'host': os.getenv('OLAP_DB_HOST', 'postgres_olap'),
    'port': 5432
}


class Report(BaseModel):
    user_id: int
    user_name: str | None = None
    prosthesis_model: str | None = None
    avg_daily_usage: float | None = None
    max_signal_value: float | None = None
    last_seen_date: str | None = None
    report_updated_at: str | None = None


@app.get("/reports/{user_id}", response_model=Report)
async def get_report_by_user_id(user_id: int):
    """
    Получает готовый отчет для заданного пользователя из OLAP-витрины.
    """
    try:
        conn = await asyncpg.connect(**DATABASE_CONFIG)
        record = await conn.fetchrow(
            "SELECT * FROM user_reports_mart WHERE user_id = $1", user_id
        )
        await conn.close()

        if record is None:
            raise HTTPException(status_code=404, detail="Report for this user not found")

        record_dict = dict(record)
        for key in ['last_seen_date', 'report_updated_at']:
            value = record_dict.get(key)
            if isinstance(value, (datetime, date)):
                record_dict[key] = value.isoformat()
        # -----------------------------
        
        return record_dict

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection or other error: {e}")
