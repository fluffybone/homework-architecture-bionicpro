CREATE TABLE IF NOT EXISTS user_reports_mart (
    user_id BIGINT PRIMARY KEY,
    user_name VARCHAR(255),
    prosthesis_model VARCHAR(255),
    avg_daily_usage FLOAT,
    max_signal_value FLOAT,
    last_seen_date DATE,
    report_updated_at TIMESTAMP
);
