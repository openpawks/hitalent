# 🏢 API организационной структуры

REST API для управления организационной структурой (подразделения и сотрудники с древовидной иерархией).

---

## 🚀 Запуск проекта

### Через Docker

```bash
docker-compose up --build
```

После запуска:

* API: [http://localhost:8000](http://localhost:8000)
* Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧱 Технологии

* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic
* Docker / docker-compose
* Pytest

---

## 📦 Основной функционал

### Подразделения

* Создание подразделения
* Получение дерева подразделений (`depth`, `include_employees`)
* Обновление (name, parent_id)
* Удаление:

  * `cascade` — удалить всё
  * `reassign` — перенести сотрудников

### Сотрудники

* Создание сотрудника в подразделении

---

## 📡 API

### POST /departments/

```json
{ "name": "Backend", "parent_id": null }
```

### GET /departments/{id}

```
?depth=1&include_employees=true
```

### PATCH /departments/{id}

```json
{ "name": "New Name", "parent_id": 2 }
```

### DELETE /departments/{id}

```
?mode=cascade
?mode=reassign&reassign_to_department_id=5
```

### POST /departments/{id}/employees/

```json
{ "full_name": "Ivan Ivanov", "position": "Dev", "hired_at": "2025-01-01" }
```

---

## 📐 Правила

* name: 1–200, уникально внутри родителя
* full_name / position: 1–200
* нельзя создавать циклы в дереве
* нельзя ссылаться на несуществующее подразделение

---

## 🧪 Запуск тестов

```bash
docker-compose exec app pytest
```

---

## 🗄️ Миграции

```bash
docker-compose exec app alembic upgrade head
```

---

## 📁 Требования

* FastAPI / Django
* PostgreSQL
* ORM
* Alembic
* Docker Compose
* pytest

