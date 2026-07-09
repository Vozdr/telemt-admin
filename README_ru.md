# TeleMT Admin

[English README](https://github.com/Vozdr/telemt-admin/blob/main/README.md) | [Русский README](https://github.com/Vozdr/telemt-admin/blob/main/README_ru.md) | [GitHub](https://github.com/Vozdr/telemt-admin) | [Docker Hub](https://hub.docker.com/r/w03zd8rc/telemt-admin)

Небольшая веб-админка для управления пользователями [TeleMT](https://github.com/telemt/telemt).

Она редактирует `config.toml` напрямую, не использует базу данных, хранит ротационные
резервные копии, генерирует `tg://proxy` ссылки и QR-коды, а также умеет показывать
пользовательские и общие Prometheus-метрики TeleMT.

## Возможности

- Добавление, редактирование, блокировка/разблокировка и удаление пользователей TeleMT.
- Настройка лимита уникальных IP для пользователя.
- Генерация ссылок и QR-кодов.
- Просмотр пользовательских и общих метрик TeleMT.
- Выбор языка интерфейса.
- Авторизация как web, так и Basic Auth.

## Требования к конфигу TeleMT

Админке нужен доступ на чтение и запись к `config.toml` TeleMT.

Для метрик обычная схема настройки такая:

1. Настройте TeleMT на прослушивание метрик со всех интерфейсов контейнера:

```toml
[server]
metrics_listen = "0.0.0.0:9090"
```

2. Объедините TeleMT и TeleMT Admin в одну Docker-сеть.

3. Укажите в TeleMT Admin адрес для сбора метрик:

```text
TELEMT_METRICS_URL=http://telemt:9090/metrics
```

Если `AUTO_FIX_METRICS_LISTEN=yes` и `ENABLE_METRICS=yes`, админка может сама
заменить `127.0.0.1:*` или `localhost:*` в `metrics_listen` на значение из
`TELEMT_METRICS_LISTEN` при запуске. После этого TeleMT может потребовать
однократный перезапуск, чтобы применить новый адрес.

Некоторые сборки или конфигурации TeleMT отвечают на метрики только из loopback
самого контейнера TeleMT, даже если `metrics_listen` выставлен в `0.0.0.0`.
В таком случае запускайте TeleMT Admin с `network_mode: "container:telemt"` и используйте:

```text
TELEMT_METRICS_URL=http://127.0.0.1:9090/metrics
```

Не публикуйте порт `9090` в интернет. Он должен быть доступен только внутри сервера или Docker-сети.

## Docker run

```bash
docker run -d \
  --name telemt-admin \
  --restart unless-stopped \
  -p 8080:8080 \
  -e ENABLE_WEB_AUTH=yes \
  -e WEB_ADMIN_USER=admin \
  -e WEB_ADMIN_PASS=change-me \
  -e TELEMT_CONFIG=/data/telemt/config/config.toml \
  -e TELEMT_METRICS_URL=http://telemt:9090/metrics \
  -e DEFAULT_THEME=light \
  -e LOG_LEVEL=ERROR \
  -e TZ=UTC \
  -v /data/telemt/config:/data/telemt/config:rw \
  -v /data/telemt-admin/backups:/data/backups:rw \
  w03zd8rc/telemt-admin:latest
```

## Пример Docker Compose

```yaml
services:
  telemt:
    image: ghcr.io/telemt/telemt:latest
    container_name: telemt
    volumes:
      - /data/telemt/config:/etc/telemt:rw
    expose:
      - "443"
      - "9090"

  telemt-admin:
    image: w03zd8rc/telemt-admin:latest
    container_name: telemt-admin
    restart: unless-stopped
    # Рекомендуется, если TeleMT отдает метрики только на loopback.
    network_mode: "container:telemt"
    environment:
      ENABLE_WEB_AUTH: "yes"
      WEB_ADMIN_USER: admin
      WEB_ADMIN_PASS: change-me
      ENABLE_BASIC_AUTH: "no"
      TELEMT_CONFIG: /data/telemt/config/config.toml
      TELEMT_METRICS_URL: http://127.0.0.1:9090/metrics
      ENABLE_METRICS: "yes"
      READ_ONLY: "no"
      DEFAULT_THEME: light
      LOG_LEVEL: ERROR
      TZ: UTC
    volumes:
      - /data/telemt/config:/data/telemt/config:rw
      - /data/telemt-admin/backups:/data/backups:rw
    # При network_mode: container:telemt порт 8080 должен быть доступен через
    # контейнер TeleMT или через другой контейнер той же сетевой namespace.
```

## Переменные окружения

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `ENABLE_WEB_AUTH` | `yes` | Включает встроенную форму входа. |
| `ENABLE_BASIC_AUTH` | `no` | Включает HTTP Basic Auth для UI/API. |
| `WEB_ADMIN_USER` | `admin` | Логин для формы входа. |
| `WEB_ADMIN_PASS` | `admin` | Пароль для формы входа. Обязательно поменяйте. |
| `BASIC_ADMIN_USER` | `admin` | Логин для Basic Auth. |
| `BASIC_ADMIN_PASS` | `admin` | Пароль для Basic Auth. Поменяйте, если включаете Basic Auth. |
| `SESSION_SECRET` | `WEB_ADMIN_PASS` | Секрет для подписи cookie web-сессии. Лучше задать стабильное случайное значение. |
| `TELEMT_CONFIG` | `/data/telemt/config/config.toml` | Путь к конфигу TeleMT внутри контейнера админки. |
| `TELEMT_BACKUP_DIR` | `/data/backups` | Каталог для резервных копий конфига. |
| `TELEMT_MAX_BACKUPS` | `20` | Количество резервных копий, которые нужно хранить. |
| `READ_ONLY` | `no` | Принудительно включает режим только чтение, даже если `config.toml` доступен на запись. |
| `ENABLE_METRICS` | `yes` | Включает метрики и проверки метрик. При `no` скрывает элементы статистики. |
| `TELEMT_METRICS_URL` | `http://telemt:9090/metrics` | URL Prometheus-метрик. Для `network_mode: container:telemt` используйте `http://127.0.0.1:9090/metrics`. |
| `TELEMT_METRICS_LISTEN` | `0.0.0.0:9090` | Значение, которое используется при автоисправлении `metrics_listen`. |
| `AUTO_FIX_METRICS_LISTEN` | `yes` | Автоматически меняет `127.0.0.1:*`/`localhost:*` в `metrics_listen` на значение выше. |
| `DEFAULT_LANG` | `en` | Язык интерфейса по умолчанию. Должен совпадать с именем JSON-файла в `LOCALES_DIR` без `.json`. |
| `DEFAULT_THEME` | `light` | Тема интерфейса по умолчанию. Поддерживаются `light`, `dark`. |
| `LOCALES_DIR` | `/app/locales` | Каталог с JSON-файлами локализации. |
| `LOG_LEVEL` | `ERROR` | Уровень логирования Uvicorn. Access logs отключены, чтобы не писать строку на каждый запрос. |
| `TELEMT_ADMIN_VERSION` | значение образа | Версия сборки, которая выводится при запуске контейнера. Обычно задаётся самим Docker-образом. |
| `TZ` | значение образа | Часовой пояс для метаданных пользователей. |

`TZ` задаётся в формате IANA timezone, например:

```text
TZ=Europe/Moscow
TZ=Asia/Yekaterinburg
TZ=UTC
```

## Режимы авторизации

По умолчанию включена только web-авторизация:

```text
ENABLE_WEB_AUTH=yes
ENABLE_BASIC_AUTH=no
```

Можно включить только web-авторизацию, только Basic Auth, оба варианта сразу или
отключить авторизацию полностью. Basic Auth отрабатывает внутри контейнера
TeleMT Admin и не требует дополнительного nginx или proxy-контейнера.

Если включены оба режима, TeleMT Admin требует обе проверки: сначала HTTP Basic
Auth, затем web-форму входа.

Если явно задать `ENABLE_WEB_AUTH=no` и `ENABLE_BASIC_AUTH=no`, админка
запустится без авторизации и выведет предупреждение в лог контейнера.

## Локализация

Файлы локализации находятся здесь:

```text
/app/locales/en.json
/app/locales/ru.json
```

Чтобы добавить новый язык, создайте JSON-файл с теми же ключами. Список языков
строится автоматически из `*.json` файлов в `LOCALES_DIR`.

Рекомендуемые метаданные:

```json
{
  "language.name": "French",
  "language.nativeName": "Français"
}
```

Если новый язык должен использоваться по умолчанию, укажите имя файла без
`.json` в `DEFAULT_LANG`.

## Безопасность

- Всегда меняйте `WEB_ADMIN_PASS` и/или `BASIC_ADMIN_PASS`.
- Не отключайте авторизацию на публичных установках.
- Размещайте админку только за HTTPS.
- Не открывайте метрики TeleMT в публичный интернет.
- Резервные копии содержат пользовательские secret-ключи. Защитите папку backups.

## Запуск и healthcheck

При запуске TeleMT Admin выводит в лог используемые несекретные настройки,
версию сборки, ссылку на GitHub, а также результат проверки чтения и записи
`config.toml`.

Если `config.toml` не читается, `/healthz` возвращает ошибку, чтобы Docker мог
пометить контейнер как unhealthy. Сам процесс продолжает работать для
диагностики. Если конфиг читается, но недоступен на запись, интерфейс
переключается в режим только чтение, а write API endpoints возвращают ошибку.

## Резервные копии

Перед каждой записью в `config.toml` админка копирует предыдущую версию конфига
в `TELEMT_BACKUP_DIR`. Старые копии удаляются, чтобы осталось не больше `TELEMT_MAX_BACKUPS`.

## Поведение метрик

Если `ENABLE_METRICS=no`:

- кнопки статистики скрыты или отключены;
- в таблице статистики отображается `-`;
- админка не проверяет и не меняет настройки метрик TeleMT.

Если `ENABLE_METRICS=yes`, админка читает:

```text
TELEMT_METRICS_URL
```

и ожидает Prometheus text format.

TeleMT Admin не требует отдельный прокси-контейнер для метрик, если метрики TeleMT
доступны напрямую. Обычная схема через Docker-сеть:

```text
metrics_listen = "0.0.0.0:9090"
TELEMT_METRICS_URL=http://telemt:9090/metrics
```

Используйте Docker `network_mode: "container:telemt"` только если ваш TeleMT
отвечает на метрики из собственного loopback, но закрывает соединения от других
контейнеров. В таком запасном режиме укажите:

```text
TELEMT_METRICS_URL=http://127.0.0.1:9090/metrics
```
