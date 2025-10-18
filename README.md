# Задание 1. Повышение безопасности системы

## Предложите архитектурное решение и доработайте диаграмму C4 для управления учётными данными пользователя. 
[Диаграмма](diagram\bionik_diagram_task1.drawio)

## Улучшите безопасность существующего приложения, заменив Code Grant на PKCE

1. Включить PKCE в кейклоак в нашем реалме и  клиенте [Включение опции Proof key](images\setProofKey.png)
 
 Повторная аторизация и проверка

 ![Проверка параметров](images\checkSha.png)
 ![Включение опции Proof key](images\checkCode.png)

# Задание 2. Разработка сервиса отчётов

## 1. Создать архитектуру решения для подготовки и получения отчётов.

[Диаграмма](diagram\bionik_diagram_task2.drawio)

## 2. Разработать Airflow DAG и настроить его на запуск по расписанию.

Настройте подключения в Airflow:

 UI Airflow (http://localhost:8081, admin/admin).

Перейти в `Admin -> Connections`.

Создать подключение `bionic_pro_olap_db (тип Postgres)` со следующими параметрами:
-------------------------
**Connection Id**: bionic_pro_olap_db

**Host**: postgres_olap

**Schema**: olap_db

**Login**: olap_user

**Password**: olap_password

**Port**: 5432
--------------------------

#### **Проверка**
![Init](imagesTask2\init.png)

![Add Connection](imagesTask2\addConnection.png)

![Check Dugs](imagesTask2\task1Result.png)

![Check Table](imagesTask2\checkTable.png)

## 3. Создайте бэкенд-часть приложения для API.

![addedRequestReport](imagesTask2\addedRequestReport.png)

## 4. Реализуйте ограничение доступа к эндпоинту отчётности.
 
Дописан [Итоговый бэк](backend\main.py)
(и поправлены csv в соответсвии с конфигом пользователей кейклока)

## 5. Добавьте в UI кнопку получения отчёта и вызова эндпоинта его генерации.

![Check Report](imagesTask2\answer.png)

![Check Report2](imagesTask2\anotherAnswer.png)