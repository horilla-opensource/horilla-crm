# Horilla CRM (Docker Image)

Horilla CRM is a Django + ASGI (Channels) application. This image starts the web server and, on startup, automatically runs:

- `python manage.py migrate --noinput`
- `python manage.py collectstatic --noinput`

It is designed to be used with **PostgreSQL**.

## Image

- **Image**: `your-dockerhub-username/horilla-crm`
- **Tags**: `latest`, `<version>`

## Ports

- **8000/tcp**: Horilla web (Uvicorn ASGI)
- **80/tcp**: Optional Nginx reverse proxy (if you run the provided Nginx config)

## Quick start (recommended): Docker Compose (Postgres + Horilla)

Create a `docker-compose.yml`:

```yaml
services:
  web:
    image: your-dockerhub-username/horilla-crm:latest
    ports:
      - "8000:8000"
    environment:
      # Django
      DEBUG: "0"
      SECRET_KEY: "change-me-to-a-long-random-string"
      ALLOWED_HOSTS: "localhost,127.0.0.1"
      CSRF_TRUSTED_ORIGINS: "http://localhost:8000"

      # Database
      DATABASE_URL: "postgres://horilla_user:horilla_pass@db:5432/horilla_db"

      # Uvicorn (optional)
      PORT: "8000"
      UVICORN_WORKERS: "2"
      UVICORN_LOG_LEVEL: "info"
      UVICORN_RELOAD: "false"
    depends_on:
      - db
    volumes:
      - staticfiles:/app/staticfiles
      - media:/app/media

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: horilla_db
      POSTGRES_USER: horilla_user
      POSTGRES_PASSWORD: horilla_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  staticfiles:
  media:
  postgres_data:
```

Start:

```bash
docker compose up -d
```

Then open `http://localhost:8000`.

### Create an admin user

```bash
docker compose exec web python manage.py createsuperuser
```

## Optional: Nginx reverse proxy (serves `/static/` and `/media/`)

If you want Nginx in front (recommended for production), add this service (it matches the repo’s `docker/nginx.conf` expectations: upstream `web:8000`, static at `/static`, media at `/media`):

```yaml
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - staticfiles:/static:ro
      - media:/media:ro
      # Either bake your own nginx.conf into a custom image,
      # or mount a local nginx.conf that matches the upstream/aliases:
      # - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - web
```

Then browse `http://localhost/`.

When you put Nginx in front, update:

- `ALLOWED_HOSTS` to your domain(s)
- `CSRF_TRUSTED_ORIGINS` to the public URL(s) (for example: `https://crm.example.com`)

## Environment variables

Horilla reads configuration from environment variables (via `django-environ`):

- **`DATABASE_URL`** (recommended): `postgres://USER:PASSWORD@HOST:PORT/DBNAME`
- **`DEBUG`**: `"1"` or `"0"`
- **`SECRET_KEY`**: required in production (set a long random value)
- **`ALLOWED_HOSTS`**: comma-separated list (example: `"example.com,www.example.com"`)
- **`CSRF_TRUSTED_ORIGINS`**: comma-separated list (example: `"https://example.com,https://www.example.com"`)
- **`PORT`**: defaults to `8000`
- **`UVICORN_WORKERS`**: defaults to CPU count
- **`UVICORN_LOG_LEVEL`**: defaults to `info`
- **`UVICORN_RELOAD`**: defaults to `false` (turn on only for development)

## Important note about the database hostname

The container entrypoint waits for PostgreSQL at hostname **`db`** on port **5432** before running migrations.

- If you use Docker Compose, name your database service `db` (as in the examples), or provide a network alias `db`.
- If you use `docker run`, ensure your Postgres container is reachable as `db` on the same user-defined network.

## Using `docker run` (single-host example)

```bash
docker network create horilla-net

docker run -d --name db --network horilla-net \
  -e POSTGRES_DB=horilla_db \
  -e POSTGRES_USER=horilla_user \
  -e POSTGRES_PASSWORD=horilla_pass \
  -v horilla_postgres_data:/var/lib/postgresql/data \
  postgres:16-alpine

docker run -d --name horilla --network horilla-net -p 8000:8000 \
  -e DEBUG=0 \
  -e SECRET_KEY="change-me" \
  -e ALLOWED_HOSTS="localhost,127.0.0.1" \
  -e CSRF_TRUSTED_ORIGINS="http://localhost:8000" \
  -e DATABASE_URL="postgres://horilla_user:horilla_pass@db:5432/horilla_db" \
  -v horilla_staticfiles:/app/staticfiles \
  -v horilla_media:/app/media \
  your-dockerhub-username/horilla-crm:latest
```

## Upgrades and migrations

On every container start, the image runs Django migrations automatically. After upgrading the image tag, restart the container:

```bash
docker compose pull
docker compose up -d
```

## Troubleshooting

- **Container stuck at “Waiting for PostgreSQL…”**
  - Make sure Postgres is reachable as host `db` on port `5432` (same network, correct service name/alias).
- **Static/media not persisting**
  - Use volumes for `/app/staticfiles` and `/app/media` (see compose examples).
- **CSRF errors in browser**
  - Set `CSRF_TRUSTED_ORIGINS` to include your full scheme+host (e.g. `https://crm.example.com`) and update `ALLOWED_HOSTS`.

## Building and publishing to Docker Hub

From the repo root (where the `Dockerfile` is):

```bash
docker login

# Build
docker build -t your-dockerhub-username/horilla-crm:latest .

# (Optional) version tag
docker tag your-dockerhub-username/horilla-crm:latest your-dockerhub-username/horilla-crm:1.0.0

# Push
docker push your-dockerhub-username/horilla-crm:latest
docker push your-dockerhub-username/horilla-crm:1.0.0
```

