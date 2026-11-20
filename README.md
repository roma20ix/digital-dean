# Цифровой деканат

Конкурсный личный кабинет студента для MGIMO AI Challenge. Сервер поддерживает вход, профиль, заказ справки и обращение в деканат по [контракту](docs/CONTRACT.md). Для каждого студента доступны собственные заявки и их статусы. Браузерный сценарий появится при интеграции с шаблонами B1. Команда `seed_demo` также заполняет расписание, результаты учёбы и уведомления. Даты и ожидаемые значения для проверки интерфейса приведены в [сценариях A2](docs/evidence/A2/README.md).

## Локальный запуск в Windows PowerShell

Из корня репозитория, с установленным Python 3.12 и Python Launcher:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

В другом окне PowerShell выполните `(Invoke-RestMethod http://127.0.0.1:8000/health/).Trim()`. Ожидаемый ответ — `ok`. Откройте http://127.0.0.1:8000/ в браузере. Для проверки с двумя студентами задайте в окружении команды разные пароли в `DEMO_STUDENT_A_PASSWORD` и `DEMO_STUDENT_B_PASSWORD`. После миграций выполните:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo
```

На хостинге используйте те же переменные из хранилища секретов и команду `python manage.py seed_demo`. Логины — `student_a` и `student_b`. У первого есть готовая демонстрационная справка, у второго — принятое обращение. Повторный запуск сохраняет номера, даты и пользовательские заявки. При изменении секрета команда обновляет пароль соответствующего демостудента.

Локальная конфигурация использует SQLite в `db.sqlite3`, русскую локаль и часовой пояс Europe/Moscow. На Linux используйте `python3.12 -m venv .venv`, затем `.venv/bin/python` для тех же команд.

## Первый HTTPS-деплой на Linux

1. Подготовьте Python 3.12, постоянную PostgreSQL 16 и выделенный домен с TLS. Направьте трафик через прокси хостинга. Он должен сохранять исходный Host, заменять входящий X-Forwarded-Proto фактической схемой и быть единственной точкой доступа к Gunicorn.
2. В панели хостинга задайте переменные для сборки, миграций и процесса приложения. Имена перечислены в [.env.example](.env.example). Django читает переменные процесса. Укажите `DJANGO_SETTINGS_MODULE=config.settings.production`, точные домены через запятую в `DJANGO_ALLOWED_HOSTS` и постоянный случайный `DJANGO_SECRET_KEY`. Ключ можно получить в приватной консоли командой `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
3. Задайте `PGDATABASE`, `PGUSER`, `PGPASSWORD`, `PGHOST` по данным хостинга. Порт PostgreSQL по умолчанию 5432. По умолчанию соединение требует TLS. Если провайдер выдаёт корневой сертификат, установите его для libpq и задайте `PGSSLMODE=verify-full`. Переменная `PORT` задаёт внутренний порт приложения.
4. В виртуальном окружении хостинга выполните сборку и проверку. Миграции запускайте один раз на выпуск до старта новых процессов.

```sh
python -m pip install -r requirements.txt
python manage.py check --deploy
python manage.py collectstatic --noinput
python manage.py migrate --noinput
gunicorn config.wsgi:application --bind "0.0.0.0:${PORT}"
```

5. Откройте публичный `https://<домен>/health/` и проверьте ответ `ok`, переход с HTTP на HTTPS, вход через браузер и загрузку `/static/cabinet.css`. После перезапуска проверьте вход того же пользователя. WhiteNoise раздаёт собранную статику.

Политика HSTS действует на выбранном хосте один час. Предупреждения Django `security.W005` и `security.W021` относятся к распространению HSTS на поддомены и включению preload. Эти параметры требуют отдельного решения владельца домена.

## Проверки

`python manage.py test cabinet.tests.FoundationTests.test_public_health` проверяет публичный ответ отдельно. Полный набор запускается через `python manage.py test`. GitHub Actions проверяет конфигурацию, миграции и тесты на Linux и Windows. На Windows workflow также запускает сервер и запрашивает `/health/` из PowerShell.

Источники зависимостей, лицензии и происхождение элементов интерфейса перечислены в [описании компонентов](docs/THIRD_PARTY.md).
