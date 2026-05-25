# Planes local y premium

## Objetivo

Separar el producto en dos formas de venta:

- **Local**: el cliente instala y usa el sistema solo en su PC o red local. No depende de Render.
- **Premium con respaldo en linea**: el cliente mantiene una copia/sincronizacion contra Render para respaldo y recuperacion.

## Variables por plan

### Cliente local

```text
APP_EDITION=local
CLOUD_BACKUP_ENABLED=false
LOCAL_BACKUP_ENABLED=true
LOCAL_BACKUP_INTERVAL_SECONDS=86400
LOCAL_BACKUP_RETENTION=14
LOCAL_BACKUP_DIR=local_backups
LOCAL_BACKUP_INCLUDE_MEDIA=true
```

En este modo Electron ignora `SYNC_REMOTE_URL` y `SYNC_API_TOKEN`, aunque existan por error en `.env`. El cliente trabaja sin internet y el sistema crea un ZIP de respaldo local.

### Cliente premium

```text
APP_EDITION=cloud_backup
CLOUD_BACKUP_ENABLED=true
SYNC_REMOTE_URL=https://tu-app.onrender.com
SYNC_API_TOKEN=la-misma-clave-configurada-en-render
LOCAL_BACKUP_ENABLED=true
```

En este modo Electron usa Render como respaldo remoto. El sync sigue funcionando por cola, intervalo periodico y WebSocket.

## Backup local

Crear respaldo manual:

```bash
venv\Scripts\python.exe manage.py local_backup
```

Crear respaldo en una carpeta especifica:

```bash
venv\Scripts\python.exe manage.py local_backup --output-dir D:\RespaldosERP --keep 30
```

Restaurar respaldo local:

```bash
venv\Scripts\python.exe manage.py restore_local_backup D:\RespaldosERP\erp-local-backup-YYYYMMDD-HHMMSS.zip --yes --restore-media
```

El comando de restauracion no corre en Render y bloquea bases que no parezcan locales, salvo que se use `--allow-non-local-db`.

## Recomendacion comercial

Para clientes sin pago mensual, entrega el modo local con backups automaticos en una carpeta que puedan copiar a USB o disco externo.

Para clientes premium, activa Render como respaldo en linea. Aun asi conviene mantener `LOCAL_BACKUP_ENABLED=true` para tener una segunda defensa en la PC.
