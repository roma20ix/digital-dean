# Компоненты и оформление прототипа

Отметка «Конкурсный прототип · вымышленные данные» и текстовый знак «Цифровой деканат» заданы в `templates/base.html`. Знак и иллюстрация с книгами нарисованы в CSS. Пиктограммы разделов находятся в `templates/components/symbols.html`. Это собственная графика проекта. Таблицы стилей и скрипт выбора темы поставляются с приложением. Браузер использует шрифты, установленные на устройстве.

Прямые зависимости сверены с `requirements.txt` и текстами лицензий в установленных дистрибутивах. Условия отдельных файлов и вложенных библиотек приведены в уведомлениях соответствующего дистрибутива.

| Компонент | Использование | Лицензия пакета | Источник |
|---|---|---|---|
| Django 5.2.19 | Страницы, модели, авторизация и формы | BSD-3-Clause | [Django](https://pypi.org/project/Django/5.2.19/) |
| Pillow 13.0.0 | Проверка, обрезка и перекодирование аватара | MIT-CMU | [Pillow](https://pypi.org/project/pillow/13.0.0/) |
| asgiref 3.13.0 | Адаптеры синхронного и асинхронного кода Django | BSD-3-Clause | [ASGI](https://pypi.org/project/asgiref/3.13.0/) |
| gunicorn 27.0.1 | WSGI-сервер для Linux | MIT | [Gunicorn](https://pypi.org/project/gunicorn/27.0.1/) |
| psycopg и psycopg-binary 3.3.9 | Подключение к PostgreSQL | LGPL-3.0-only | [psycopg](https://pypi.org/project/psycopg/3.3.9/), [psycopg-binary](https://pypi.org/project/psycopg-binary/3.3.9/) |
| sqlparse 0.6.1 | Разбор SQL для Django | BSD-3-Clause | [sqlparse](https://pypi.org/project/sqlparse/0.6.1/) |
| typing_extensions 4.16.0 | Поддержка аннотаций типов | PSF-2.0 | [Python](https://pypi.org/project/typing-extensions/4.16.0/) |
| tzdata 2026.6 | Данные часовых поясов для zoneinfo | Apache-2.0 для пакета | [tzdata](https://pypi.org/project/tzdata/2026.6/) |
| whitenoise 6.12.0 | Раздача статики | MIT | [WhiteNoise](https://pypi.org/project/whitenoise/6.12.0/) |

В проверках интерфейса используется Python Playwright 1.62.0 (Apache-2.0), который запускает отдельно установленный Chromium. [Playwright](https://pypi.org/project/playwright/1.62.0/) · [Лицензии Chromium](https://chromium.googlesource.com/chromium/src/+/main/LICENSE)

Два 15-секундных учебных ролика в `static/learning/` созданы для проекта из собственных текстовых слайдов. «Сложение векторов» иллюстрирует сложение по координатам, «Разбор договора» — поиск сторон, предмета и срока. Текстовый разбор доступен рядом с проигрывателем.
