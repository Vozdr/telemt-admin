# TeleMT Admin

[GitHub](https://github.com/Vozdr/telemt-admin) | [Docker Hub](https://hub.docker.com/r/w03zd8rc/telemt-admin) | [English README](https://github.com/Vozdr/telemt-admin/blob/main/README.md) | [Русский README](https://github.com/Vozdr/telemt-admin/blob/main/README_ru.md)

---

# TeleMT Admin

[English README](https://github.com/Vozdr/telemt-admin/blob/main/README.md) | [Русский README](https://github.com/Vozdr/telemt-admin/blob/main/README_ru.md) | [GitHub](https://github.com/Vozdr/telemt-admin) | [Docker Hub](https://hub.docker.com/r/w03zd8rc/telemt-admin)

Small web admin panel for [TeleMT](https://github.com/telemt/telemt) users.

It edits `config.toml` directly, does not use a database, keeps rotating backups,
generates `tg://proxy` links and QR codes, and can show per-user and global
TeleMT Prometheus metrics.

## Features

- Add, edit, block/unblock and delete TeleMT users.
- Edit per-user unique IP limits.
- Generate proxy links and QR codes.
- View user and global TeleMT metrics.
- UI language selector.
- Web login and Basic Auth support.

## TeleMT config requirements

The admin panel needs read/write access to TeleMT `config.toml`.

For metrics, the normal setup is:

1. Configure TeleMT to listen for metrics on all container interfaces:

```toml
[server]
metrics_listen = "0.0.0.0:9090"
```

2. Put TeleMT and TeleMT Admin in the same Docker network.

3. Set the metrics URL in TeleMT Admin:

```text
TELEMT_METRICS_URL=http://telemt:9090/metrics
```

If `AUTO_FIX_METRICS_LISTEN=yes` and `ENABLE_METRICS=yes`, the admin panel can
rewrite `127.0.0.1:*` or `localhost:*` in `metrics_listen` to
`TELEMT_METRICS_LISTEN` on startup. TeleMT may still need to be restarted once
for the changed listen address to take effect.

Some TeleMT builds/configurations respond to metrics only from the TeleMT
container loopback even when `metrics_listen` is set to `0.0.0.0`. If that is
your case, run TeleMT Admin with `network_mode: "container:telemt"` and use:

```text
TELEMT_METRICS_URL=http://127.0.0.1:9090/metrics
```

Do not publish port `9090` to the internet. It only needs to be reachable inside
the Docker network.

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

## Docker Compose example

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
    # Recommended when TeleMT metrics are loopback-only.
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
    # With network_mode: container:telemt, expose/publish port 8080 from
    # the TeleMT container or reach it through another container in the same
    # Docker network via http://telemt:8080.
```

## Environment variables

| Variable | Default | Description |
| --- | --- | --- |
| `ENABLE_WEB_AUTH` | `yes` | Enables the built-in login form. |
| `ENABLE_BASIC_AUTH` | `no` | Enables HTTP Basic Auth for API/UI requests. |
| `WEB_ADMIN_USER` | `admin` | Login form username. |
| `WEB_ADMIN_PASS` | `admin` | Login form password. Change it. |
| `BASIC_ADMIN_USER` | `admin` | Basic Auth username. |
| `BASIC_ADMIN_PASS` | `admin` | Basic Auth password. Change it if Basic Auth is enabled. |
| `SESSION_SECRET` | `WEB_ADMIN_PASS` | Secret used to sign web login cookies. Set a stable random value if the password may change. |
| `TELEMT_CONFIG` | `/data/telemt/config/config.toml` | Path to TeleMT config inside the admin container. |
| `TELEMT_BACKUP_DIR` | `/data/backups` | Directory for config backups. |
| `TELEMT_MAX_BACKUPS` | `20` | Number of backups to keep. |
| `READ_ONLY` | `no` | Forces read-only mode even when `config.toml` is writable. |
| `ENABLE_METRICS` | `yes` | Enables metrics UI and metrics checks. Use `no` to hide metrics controls. |
| `TELEMT_METRICS_URL` | `http://telemt:9090/metrics` | Prometheus metrics URL. Use `http://127.0.0.1:9090/metrics` with `network_mode: container:telemt`. |
| `TELEMT_METRICS_LISTEN` | `0.0.0.0:9090` | Value used when auto-fixing TeleMT `metrics_listen`. |
| `AUTO_FIX_METRICS_LISTEN` | `yes` | Auto-rewrite `127.0.0.1:*`/`localhost:*` metrics listen in `config.toml`. |
| `DEFAULT_LANG` | `en` | Default UI language. Must match a JSON file name in `LOCALES_DIR` without `.json`. |
| `DEFAULT_THEME` | `light` | Default UI theme. Supported: `light`, `dark`. |
| `LOCALES_DIR` | `/app/locales` | Directory with localization JSON files. |
| `LOG_LEVEL` | `ERROR` | Uvicorn log level. Access logs are disabled to avoid noisy request lines. |
| `TELEMT_ADMIN_VERSION` | image value | Build version printed at container startup. Usually set by the Docker image. |
| `TZ` | image default | Timezone used for metadata timestamps. |

`TZ` uses IANA timezone names, for example:

```text
TZ=Europe/Moscow
TZ=Asia/Yekaterinburg
TZ=UTC
```

## Authentication modes

Default mode is web login only:

```text
ENABLE_WEB_AUTH=yes
ENABLE_BASIC_AUTH=no
```

You can enable only Basic Auth, only web login, both, or neither. Basic Auth is
handled inside the TeleMT Admin container; it does not require an additional
nginx or proxy container.

When both modes are enabled, TeleMT Admin requires both checks: first HTTP Basic
Auth, then the web login form.

If both `ENABLE_WEB_AUTH=no` and `ENABLE_BASIC_AUTH=no`, the admin panel starts
without authentication and prints a warning to the container log.

## Localization

Localization files live in:

```text
/app/locales/en.json
/app/locales/ru.json
```

To add another language, add a new JSON file with the same keys. The language
selector is built automatically from `*.json` files in `LOCALES_DIR`.

Recommended metadata keys:

```json
{
  "language.name": "French",
  "language.nativeName": "Français"
}
```

Set `DEFAULT_LANG` to the file name without `.json` if the new language should
be used by default.

## Security notes

- Always change `WEB_ADMIN_PASS` and/or `BASIC_ADMIN_PASS`.
- Do not disable authentication on public deployments.
- Put the admin panel behind HTTPS.
- Do not expose TeleMT metrics to the public internet.
- Backups contain user secrets. Protect the backups directory.

## Startup and health

At startup, TeleMT Admin prints the effective non-secret settings, the build
version, the GitHub URL, and read/write probes for `config.toml`.

If `config.toml` cannot be read, `/healthz` returns an error so Docker can mark
the container unhealthy. The process keeps running for troubleshooting. If the
config is readable but not writable, the UI switches to read-only mode and write
API endpoints return an error.

## Backup behavior

Before every write to `config.toml`, the admin panel copies the previous config
to `TELEMT_BACKUP_DIR`. Old backups are pruned to `TELEMT_MAX_BACKUPS`.

## Metrics behavior

If `ENABLE_METRICS=no`:

- metrics buttons are hidden/disabled;
- table statistics show `-`;
- the admin panel does not check or modify TeleMT metrics settings.

If `ENABLE_METRICS=yes`, the admin panel reads:

```text
TELEMT_METRICS_URL
```

and expects Prometheus text format.

TeleMT Admin does not need a separate metrics proxy container when TeleMT metrics
are reachable directly. The normal Docker-network setup is:

```text
metrics_listen = "0.0.0.0:9090"
TELEMT_METRICS_URL=http://telemt:9090/metrics
```

Use Docker `network_mode: "container:telemt"` only if your TeleMT instance
answers metrics from its own loopback but closes connections from other
containers. In that fallback mode, set:

```text
TELEMT_METRICS_URL=http://127.0.0.1:9090/metrics
```

---

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
