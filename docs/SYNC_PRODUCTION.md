# Sincronizacion en produccion

## Objetivo

Mantener una base principal en Render y una base PostgreSQL local por equipo/oficina Electron. La app local puede operar sin conexion a internet y sube sus cambios cuando vuelve la red.

## Variables requeridas en Render

```text
SYNC_API_TOKEN=clave-larga-secreta
DJANGO_USE_DATABASE_MEDIA_STORAGE=true
DJANGO_SERVE_MEDIA=true
```

`render.yaml` ya incluye `SYNC_API_TOKEN` con `generateValue: true`. Si Render genera la clave, copiala desde el panel de Render y usala en cada equipo local.

## Variables requeridas en cada equipo local

```bash
set DJANGO_DB_ENGINE=postgresql
set POSTGRES_NAME=Tienda
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5432
set POSTGRES_USER=usuario_local
set POSTGRES_PASSWORD=password_local
set SYNC_REMOTE_URL=https://tu-app.onrender.com
set SYNC_API_TOKEN=la-misma-clave-de-render
set SYNC_INTERVAL_SECONDS=300
set SYNC_RETRY_SECONDS=30
set SYNC_DEBOUNCE_SECONDS=5
set SYNC_WEBSOCKET_ENABLED=true
set SYNC_WEBSOCKET_PATH=/ws/sync/
set SYNC_WEBSOCKET_RETRY_SECONDS=30
set SYNC_CONNECTIVITY_TIMEOUT_SECONDS=10
npm run electron
```

Tambien puedes dejar esas variables guardadas en `.env`. Electron lee la configuracion local de PostgreSQL y las variables de sincronizacion desde `.env` antes de iniciar.

Con estas variables, Electron:

- Usa PostgreSQL local en la PC/oficina.
- Guarda media en base de datos para poder sincronizar archivos.
- Hace pull inicial antes de crear un superadmin local.
- Revisa `/sync/status/` antes de sincronizar.
- Sincroniza al iniciar y luego cada intervalo.
- Si detecta cambios locales pendientes en `SyncOutbox`, sincroniza de inmediato.
- Mantiene un WebSocket con Render en `/ws/sync/`; cuando Render avisa cambios, Electron ejecuta sync de inmediato.
- Si no hay internet o Render no responde, no bloquea la app local; reintenta cada `SYNC_RETRY_SECONDS`.

## Flujo recomendado

1. Desplegar Render con migraciones aplicadas.
2. Crear usuarios, tiendas, productos y datos base en Render.
3. En cada PC, crear la base PostgreSQL local, instalar dependencias y arrancar Electron con internet una primera vez.
4. Confirmar que el login local funciona con el usuario de Render.
5. Trabajar offline si se cae la red.
6. Al volver la red, dejar Electron abierto para que suba la cola `SyncOutbox`.

## Verificaciones manuales

Estado del servidor:

```bash
curl -H "X-Sync-Token: TU_TOKEN" https://tu-app.onrender.com/sync/status/
```

Sincronizacion manual desde la PC:

```bash
venv\Scripts\python.exe manage.py sync_with_remote --remote https://tu-app.onrender.com --token TU_TOKEN
```

Reconstruir la base local desde Render:

```bash
venv\Scripts\python.exe manage.py reset_local_from_remote --remote https://tu-app.onrender.com --token TU_TOKEN --yes
```

Ese comando primero valida `/sync/status/`. Si Render no responde correctamente, no borra datos locales.

## Operacion y soporte

Tablas clave en el admin:

- `SyncOutbox`: cambios pendientes o con error.
- `SyncState`: ultima sincronizacion por servidor.
- `SyncConflict`: cambios que requieren revision.
- `SyncRunLock`: evita dos sincronizaciones simultaneas.
- `SyncTombstone`: eliminaciones propagadas.

## Politica de conflictos

La politica actual es conservadora:

- Si el registro remoto es mas nuevo, se aplica localmente.
- Si el registro local es mas nuevo, se conserva local y se registra un `SyncConflict`.
- Si un registro se edito varias veces offline, se envia el ultimo estado.

Para cajas multiples vendiendo el mismo producto, el punto sensible es stock/facturacion. El sistema sincroniza ventas y movimientos, pero antes de operacion intensiva con varias cajas conviene definir reglas finales para:

- Numeracion fiscal offline.
- Conflictos de stock negativo.
- Cierre de caja por equipo.

## Respaldo

Mantener respaldo de:

- Base PostgreSQL de Render.
- Base PostgreSQL local en cada PC/oficina.
- Carpeta del proyecto local si se usa media fuera de base.

Con sync remoto activo, Electron usa media en base de datos para reducir el riesgo de archivos sueltos no sincronizados.
