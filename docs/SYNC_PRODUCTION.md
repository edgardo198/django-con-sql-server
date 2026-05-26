# Sincronizacion en produccion

## Objetivo

Mantener una base principal en Render y una base PostgreSQL local por equipo/oficina Electron. La app local puede operar sin conexion a internet y sube sus cambios cuando vuelve la red.

## Variables requeridas en Render

```text
APP_EDITION=cloud_backup
CLOUD_BACKUP_ENABLED=true
SYNC_NODE_ROLE=central
SYNC_API_TOKEN=clave-larga-secreta
DJANGO_USE_DATABASE_MEDIA_STORAGE=true
DJANGO_SERVE_MEDIA=true
```

`render.yaml` ya incluye `SYNC_API_TOKEN` con `generateValue: true`. Si Render genera la clave, copiala desde el panel de Render y usala en cada equipo local.

## Variables requeridas en cada equipo local

```bash
set APP_EDITION=cloud_backup
set CLOUD_BACKUP_ENABLED=true
set SYNC_NODE_ROLE=local
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

Si `CLOUD_BACKUP_ENABLED=false`, Electron trabaja como producto local y no intentara usar Render aunque existan `SYNC_REMOTE_URL` o `SYNC_API_TOKEN`.

## Flujo recomendado

1. Desplegar Render con migraciones aplicadas.
2. Crear usuarios, tiendas, productos y datos base en Render.
3. En cada PC, crear la base PostgreSQL local, instalar dependencias y arrancar Electron con internet una primera vez.
4. Confirmar que el login local funciona con el usuario de Render.
5. Trabajar offline si se cae la red.
6. Al volver la red, dejar Electron abierto para que suba la cola `SyncOutbox`.

## Direccion de datos

Cada caja usa siempre el servidor y la base local. Render funciona como panel central y respaldo en nube.

- Local sube a Render: ventas, compras, pagos, cierres de caja, movimientos de caja e inventario.
- Render baja a local: tiendas, productos, precios, categorias, proveedores, impuestos, datos fiscales, usuarios y archivos media.
- Clientes sincronizan en ambos sentidos.
- Inventario se conserva por tienda usando la relacion `organization`.
- Todos los registros sincronizados usan `SyncIdentity.sync_uuid` y la cola `SyncOutbox`.

El rol se define con `SYNC_NODE_ROLE`. Usa `local` en cajas y `central` en Render. Si no se configura, Render se detecta por la variable `RENDER`; fuera de Render el rol por defecto es `local`.

## Panel de estado

Los superusuarios pueden revisar la sincronizacion en:

```text
/sync/panel/
```

El panel muestra rol del nodo, cola pendiente, fallos, conflictos, ultima descarga/subida y el boton **Sincronizar ahora**. Tambien incluye la seccion **Configuracion**, donde el superusuario puede guardar la URL de Render y el token sin editar archivos `.env`.

Datos que puede guardar el superusuario desde tienda:

- URL de Render, por ejemplo `https://tu-app.onrender.com`.
- Token de sincronizacion, el mismo `SYNC_API_TOKEN` configurado en Render.

El token se guarda en la base local y no se vuelve a mostrar en pantalla. Si el campo queda vacio al guardar despues, se conserva el token existente.

El panel tambien incluye el boton **Activar/Desactivar sincronizacion**, disponible solo para superusuarios desde la interfaz de tienda.

Cuando el superusuario pausa la sincronizacion:

- El boton **Sincronizar ahora** queda bloqueado.
- `sync_with_remote` sale sin subir ni bajar datos.
- `sync_pending_count` devuelve `0`, para que Electron no despierte la sincronizacion por cola pendiente.
- `sync_periodically` queda esperando y revisa de nuevo cada `SYNC_INTERVAL_SECONDS`.

Las tareas automaticas siguen usando `SYNC_INTERVAL_SECONDS`; Electron revisa la cola cada pocos segundos y ejecuta una sincronizacion cuando hay cambios pendientes y la sincronizacion esta activa.

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
