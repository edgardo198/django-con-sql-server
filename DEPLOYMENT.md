# Despliegue en Render

Este proyecto ya incluye los archivos necesarios para desplegar en Render:

- `.python-version`: fija Python `3.8.18`, necesario para Django `3.0.1`.
- `build.sh`: instala dependencias, recolecta estaticos y ejecuta `check --deploy`.
- `start.sh`: aplica migraciones, crea/actualiza el super admin inicial y arranca Gunicorn.
- `Procfile`: comando web compatible con plataformas tipo Render/Heroku.
- `render.yaml`: blueprint opcional para crear el servicio web y PostgreSQL desde Render.

## Opcion recomendada: Blueprint

1. Sube el repositorio a GitHub/GitLab/Bitbucket.
2. En Render, usa **New > Blueprint** y selecciona este repo.
3. Render leera `render.yaml`, creara un servicio web y una base PostgreSQL.
4. Cuando termine el deploy, revisa en **Environment** el valor generado de `SUPERADMIN_PASSWORD`.

## Opcion manual

Crear primero una base de datos PostgreSQL en Render y copiar su **Internal Database URL**.

Crear despues un **Web Service** con:

```bash
Build Command: bash build.sh
Start Command: bash start.sh
```

Variables de entorno minimas:

```bash
PYTHON_VERSION=3.8.18
DJANGO_ENV=production
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=<generar en Render>
DJANGO_USE_PROXY_SSL_HEADER=true
DJANGO_SECURE_SSL_REDIRECT=true
DATABASE_URL=<Internal Database URL de Render PostgreSQL>
SUPERADMIN_USERNAME=superadmin
SUPERADMIN_EMAIL=superadmin@example.com
SUPERADMIN_PASSWORD=<clave segura inicial>
```

No hace falta definir `DJANGO_ALLOWED_HOSTS` si usaras el subdominio `.onrender.com`, porque el proyecto acepta automaticamente `RENDER_EXTERNAL_HOSTNAME`. Si usaras dominio propio, agrega:

```bash
DJANGO_ALLOWED_HOSTS=tu-app.onrender.com,tu-dominio.com,www.tu-dominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=tu-app.onrender.com,tu-dominio.com,www.tu-dominio.com
```

## Base de datos

Render recomienda PostgreSQL para Django. Este proyecto acepta `DATABASE_URL`, por ejemplo:

```bash
DATABASE_URL=postgresql://usuario:password@host:5432/base
```

Tambien conserva soporte por variables separadas:

```bash
DJANGO_DB_ENGINE=postgresql
POSTGRES_NAME=TuBase
POSTGRES_HOST=host
POSTGRES_PORT=5432
POSTGRES_USER=usuario
POSTGRES_PASSWORD=password
```

SQLite solo sirve para pruebas locales; en Render se pierde al reiniciar o redeplegar. Microsoft SQL Server requiere drivers ODBC del sistema y normalmente conviene desplegar con Docker si realmente necesitas SQL Server.

## Archivos subidos por usuarios

Render no conserva `media/` en el disco normal entre deploys. Para produccion usa una de estas opciones:

- Persistent Disk de Render montado en `media/`.
- Un almacenamiento externo como S3, Cloudinary o similar.

## Comandos locales utiles

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput
.\venv\Scripts\python.exe manage.py check --deploy
```
