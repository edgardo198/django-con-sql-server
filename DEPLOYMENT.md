# Despliegue

## 1. Variables de entorno

Usa `.env.example` como referencia y define al menos:

- `DJANGO_ENV=production`
- `DJANGO_DEBUG=false`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CSRF_TRUSTED_ORIGINS`

## 2. Base de datos

SQLite:

```powershell
$env:DJANGO_DB_ENGINE='sqlite'
```

SQL Server:

```powershell
$env:DJANGO_DB_ENGINE='sqlserver'
$env:SQLSERVER_NAME='TuBase'
$env:SQLSERVER_HOST='Servidor\\Instancia'
$env:SQLSERVER_USER='usuario'
$env:SQLSERVER_PASSWORD='password'
```

## 3. Preparacion

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput
.\venv\Scripts\python.exe manage.py check --deploy
```

## 4. Produccion

- Sirve `staticfiles/` y `media/` desde Nginx, Apache o IIS.
- Ejecuta Django detras de un servidor WSGI.
- Si usas proxy HTTPS, habilita `DJANGO_USE_PROXY_SSL_HEADER=true`.
