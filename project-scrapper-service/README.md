# Scrapper Service для трекера ссылок (LinkTracker)

## 📌 Описание проекта
Бэкенд-сервис на FastAPI для сбора обновлений по отслеживаемым ссылкам (GitHub, StackOverflow), хранения данных в реляционной базе данных и асинхронной рассылки уведомлений.

## 🛠 Технологии и реализация
* **Язык:** Python / FastAPI
* **Архитектура:** REST API сервис с подключением PostgreSQL, миграциями и брокером сообщений.
* **Что использовано:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Docker, Apache Kafka.
* **Изученные инструменты:**
  * Создание RESTful API на FastAPI.
  * Управление миграциями БД и ORM.
  * Событийно-ориентированная архитектура (Apache Kafka).
  * Контейнеризация через Docker Compose и тестирование с Testcontainers.

## 🚀 Инструкция по запуску
1. Установка зависимостей:
   ```bash
   poetry install
   ```
2. Запуск через Docker Compose:
   ```bash
   docker compose up --build
   ```
3. Запуск тестов:
   ```bash
   pytest tests/ -v --cov=src
   ```
