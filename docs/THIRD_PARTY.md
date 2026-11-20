# Компоненты и оформление прототипа

Отметка «Конкурсный прототип · вымышленные данные» и текстовый знак «Цифровой деканат» заданы в `templates/base.html`. Полосы у знака нарисованы в `static/cabinet.css`. Обе таблицы стилей поставляются с приложением. Браузер использует установленные системные шрифты. В шаблонах кабинета нет загружаемых изображений, наборов иконок, файлов шрифтов или внешнего JavaScript.

Прямые зависимости сверены с `requirements.txt` и текстами лицензий в установленных дистрибутивах. Условия отдельных файлов и вложенных библиотек приведены в уведомлениях соответствующего дистрибутива.

| Компонент | Использование | Лицензия пакета | Источник |
|---|---|---|---|
| Django 5.2.19 | Страницы, модели, авторизация и формы | BSD-3-Clause | [Django](https://pypi.org/project/Django/5.2.19/) |
| asgiref 3.13.0 | Адаптеры синхронного и асинхронного кода Django | BSD-3-Clause | [ASGI](https://pypi.org/project/asgiref/3.13.0/) |
| gunicorn 27.0.1 | WSGI-сервер для Linux | MIT | [Gunicorn](https://pypi.org/project/gunicorn/27.0.1/) |
| psycopg и psycopg-binary 3.3.9 | Подключение к PostgreSQL | LGPL-3.0-only | [psycopg](https://pypi.org/project/psycopg/3.3.9/), [psycopg-binary](https://pypi.org/project/psycopg-binary/3.3.9/) |
| sqlparse 0.6.1 | Разбор SQL для Django | BSD-3-Clause | [sqlparse](https://pypi.org/project/sqlparse/0.6.1/) |
| typing_extensions 4.16.0 | Поддержка аннотаций типов | PSF-2.0 | [Python](https://pypi.org/project/typing-extensions/4.16.0/) |
| tzdata 2026.6 | Данные часовых поясов для zoneinfo | Apache-2.0 для пакета | [tzdata](https://pypi.org/project/tzdata/2026.6/) |
| whitenoise 6.12.0 | Раздача статики | MIT | [WhiteNoise](https://pypi.org/project/whitenoise/6.12.0/) |

В проверках интерфейса используется Python Playwright 1.62.0 (Apache-2.0), который запускает отдельно установленный Chromium. [Playwright](https://pypi.org/project/playwright/1.62.0/) · [Лицензии Chromium](https://chromium.googlesource.com/chromium/src/+/main/LICENSE)
