# TeleMT Admin

[English README](README.md) | [Русский README](README_ru.md) | [GitHub](https://github.com/Vozdr/telemt-admin) | [Docker Hub](https://hub.docker.com/r/w03zd8rc/telemt-admin)

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
