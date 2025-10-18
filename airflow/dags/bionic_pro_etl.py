from datetime import datetime, timedelta
from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
import pandas as pd

# ID подключений, которые вы создали в UI Airflow
CRM_CONN_ID = 'bionic_pro_crm'
TELEMETRY_DB_CONN_ID = 'bionic_pro_telemetry_db'
OLAP_DB_CONN_ID = 'bionic_pro_olap_db'

def extract_crm_data_from_csv(**kwargs):
    """Извлекает данные о клиентах из локального CSV-файла."""
    print("Извлечение данных CRM из файла...")
    file_path = '/opt/airflow/sample_files/crm_data.csv'
    df = pd.read_csv(
        file_path,
        dtype={'id': 'int64', 'name': 'string', 'model': 'string'}
    )
    print(f"Извлечено {len(df)} записей из CRM файла.")
    # Передаем данные дальше в виде JSON-строки
    kwargs['ti'].xcom_push(key='crm_data_json', value=df.to_json(force_ascii=False))

def extract_telemetry_data_from_csv(**kwargs):
    """Извлекает данные телеметрии из локального CSV-файла."""
    print("Извлечение данных телеметрии из файла...")
    file_path = '/opt/airflow/sample_files/telemetry_data.csv'
    df = pd.read_csv(
        file_path,
        parse_dates=['timestamp'],
        dtype={'user_id': 'int64', 'signal_value': 'float64', 'activation_count': 'int64'}
    )
    print(f"Извлечено {len(df)} записей телеметрии из файла.")
    # Передаем данные дальше в виде JSON-строки с датами в формате ISO
    kwargs['ti'].xcom_push(key='telemetry_data_json', value=df.to_json(date_format='iso'))

def transform_and_create_mart(**kwargs):
    """Объединяет и агрегирует данные, формирует витрину."""
    print("Трансформация данных...")
    ti = kwargs['ti']
    # Получаем данные из предыдущих задач
    crm_df = pd.read_json(ti.xcom_pull(key='crm_data_json', task_ids='extract_crm_task'))
    telemetry_df = pd.read_json(ti.xcom_pull(key='telemetry_data_json', task_ids='extract_telemetry_task'))

    # Группируем телеметрию для получения агрегатов
    telemetry_df['timestamp'] = pd.to_datetime(telemetry_df['timestamp'])
    telemetry_agg_df = telemetry_df.groupby('user_id').agg(
        avg_daily_usage=('activation_count', 'mean'),
        max_signal_value=('signal_value', 'max'),
        last_seen_date=('timestamp', 'max')
    ).reset_index()

    # Объединяем данные
    mart_df = pd.merge(crm_df, telemetry_agg_df, how='left', left_on='id', right_on='user_id')

    # Приводим типы данных в порядок перед передачей в XCom
    mart_df['user_id'] = mart_df['user_id'].fillna(mart_df['id']).astype(int)
    mart_df['last_seen_date'] = pd.to_datetime(mart_df['last_seen_date']).dt.strftime('%Y-%m-%d %H:%M:%S')
    mart_df['report_updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Готовим финальную витрину
    mart_df.rename(columns={'name': 'user_name', 'model': 'prosthesis_model'}, inplace=True)
    final_mart = mart_df[[
        'user_id', 'user_name', 'prosthesis_model', 'avg_daily_usage',
        'max_signal_value', 'last_seen_date', 'report_updated_at'
    ]]
    
    # Заменяем NaN на None для корректной сериализации
    final_mart = final_mart.where(pd.notnull(final_mart), None)
    
    print("Витрина успешно сформирована.")
    kwargs['ti'].xcom_push(key='mart_records', value=final_mart.to_dict('records'))

def load_mart_to_olap(**kwargs):
    """Загружает витрину в OLAP-базу данных."""
    print("Загрузка витрины в OLAP...")
    ti = kwargs['ti']
    records = ti.xcom_pull(key='mart_records', task_ids='transform_task')
    olap_hook = PostgresHook(postgres_conn_id=OLAP_DB_CONN_ID)
    
    for record in records:
        olap_hook.run(
            """
            INSERT INTO user_reports_mart (user_id, user_name, prosthesis_model, avg_daily_usage, max_signal_value, last_seen_date, report_updated_at)
            VALUES (%(user_id)s, %(user_name)s, %(prosthesis_model)s, %(avg_daily_usage)s, %(max_signal_value)s, %(last_seen_date)s, %(report_updated_at)s)
            ON CONFLICT (user_id) DO UPDATE SET
                user_name = EXCLUDED.user_name,
                prosthesis_model = EXCLUDED.prosthesis_model,
                avg_daily_usage = EXCLUDED.avg_daily_usage,
                max_signal_value = EXCLUDED.max_signal_value,
                last_seen_date = EXCLUDED.last_seen_date,
                report_updated_at = EXCLUDED.report_updated_at;
            """,
            parameters=record
        )
    print(f"Обработано {len(records)} записей.")

# --- Определение DAG ---
with DAG(
    dag_id='bionic_pro_reports_etl',
    schedule='0 3 * * *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['bionic_pro'],
) as dag:
    
    extract_crm_task = PythonOperator(
        task_id='extract_crm_task',
        python_callable=extract_crm_data_from_csv
    )

    extract_telemetry_task = PythonOperator(
        task_id='extract_telemetry_task',
        python_callable=extract_telemetry_data_from_csv
    )

    transform_task = PythonOperator(
        task_id='transform_task',
        python_callable=transform_and_create_mart
    )

    load_task = PythonOperator(
        task_id='load_task',
        python_callable=load_mart_to_olap
    )

    # Задаем последовательность выполнения задач
    [extract_crm_task, extract_telemetry_task] >> transform_task >> load_task
