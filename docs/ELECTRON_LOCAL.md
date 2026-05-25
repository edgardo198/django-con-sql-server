# Electron local

Esta app sigue siendo una aplicacion Django. Electron solo agrega una ventana de escritorio y arranca el servidor local en `127.0.0.1`.

## Que se agrego

- `package.json` con scripts para abrir Electron.
- `electron/main.js` para iniciar Django, migrar la base local y cargar `/login/`.
- Base local configurable. En produccion local se recomienda PostgreSQL en la PC/oficina; SQLite queda como opcion de desarrollo.
- Bootstrap automatico del usuario `superadmin` la primera vez que se crea la base local.

## Credenciales web vs local

La version web y la version Electron pueden convivir, pero no deben depender de la misma conexion para operar localmente.

En produccion el modo recomendado es:

```text
Render web       -> PostgreSQL de Render
Electron local   -> PostgreSQL local en 127.0.0.1
Sincronizacion   -> /sync/pull/ y /sync/push/ cuando hay red
```

Electron lee `DJANGO_DB_ENGINE` y `POSTGRES_*` desde `.env`. Si necesitas una base distinta solo para Electron, puedes usar `ELECTRON_DB_ENGINE` y `ELECTRON_POSTGRES_*`.

Ejemplo local:

```text
DJANGO_DB_ENGINE=postgresql
POSTGRES_NAME=Tienda
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=Edgardo
POSTGRES_PASSWORD=tu-password-local
```

Las credenciales de Render funcionaran en Electron cuando esos usuarios existan en la base local. Eso puede ocurrir por sincronizacion desde Render o por bootstrap manual del usuario local.

## Sincronizacion con Render

La sincronizacion usa endpoints Django protegidos por token:

```text
GET  /sync/status/
GET  /sync/pull/
POST /sync/push/
```

En Render debes configurar la misma clave secreta:

```text
SYNC_API_TOKEN=una-clave-larga-y-secreta
```

En la maquina local/Electron configura esas variables en PowerShell o guardalas en `.env`:

```bash
set SYNC_REMOTE_URL=https://tu-app.onrender.com
set SYNC_API_TOKEN=una-clave-larga-y-secreta
npm run electron
```

Electron lee `SYNC_REMOTE_URL`, `SYNC_API_TOKEN` y las variables de sincronizacion desde `.env` antes de iniciar. Si la base local ya existia antes de configurar sync, ejecuta una sincronizacion manual para traer usuarios y datos base.

Electron intentara sincronizar al arrancar y luego cada 5 minutos. Puedes cambiar el intervalo:

```bash
set SYNC_INTERVAL_SECONDS=120
set SYNC_RETRY_SECONDS=30
set SYNC_DEBOUNCE_SECONDS=5
set SYNC_CONNECTIVITY_TIMEOUT_SECONDS=10
```

Antes de cada sincronizacion, Electron revisa `https://tu-app.onrender.com/sync/status/`. Si no hay internet, el token falla o Render no tiene `/sync/` desplegado, la app local sigue funcionando y reintenta despues de `SYNC_RETRY_SECONDS`.

Cada vez que guardas o eliminas datos locales, Django crea una entrada en `SyncOutbox`. Electron revisa esa cola cada `SYNC_DEBOUNCE_SECONDS`; si hay cambios pendientes, sincroniza de inmediato en lugar de esperar al intervalo completo.

Cuando `SYNC_REMOTE_URL` y `SYNC_API_TOKEN` estan configurados, Electron guarda media en base de datos (`StoredMediaFile`) para que logos/fotos/imagenes tambien puedan sincronizarse. En Render ya queda recomendado `DJANGO_USE_DATABASE_MEDIA_STORAGE=true`.

Tambien puedes ejecutar la sincronizacion manual:

```bash
venv\Scripts\python.exe manage.py sync_with_remote --remote https://tu-app.onrender.com --token una-clave-larga-y-secreta
```

Para borrar los datos locales y reconstruirlos desde Render, usa:

```bash
venv\Scripts\python.exe manage.py reset_local_from_remote --remote https://tu-app.onrender.com --token una-clave-larga-y-secreta --yes
```

Ese comando no borra nada si Render no responde correctamente en `/sync/status/`.

Importante: el primer ciclo debe hacerse con red para traer usuarios, tiendas, productos y datos base desde Render. Luego puedes trabajar sin conexion; los cambios locales se guardan en una cola (`SyncOutbox`) y se suben cuando vuelva la red.

Cuando `SYNC_REMOTE_URL` esta configurado, Electron intenta hacer un `pull` inicial antes de crear el usuario local `superadmin`. Si logra traer usuarios desde Render, omite el bootstrap local. Si no hay red o no hay usuarios todavia, crea el acceso local de emergencia.

La sincronizacion actual usa resolucion conservadora: si detecta que un registro local fue actualizado despues que el remoto, conserva el local y registra un conflicto en `SyncConflict`. Para operacion con varias cajas editando el mismo producto a la vez, conviene definir una politica de stock por movimientos antes de usarlo en produccion pesada.

## Operacion en produccion

Antes de usarlo con datos reales:

1. Define `SYNC_API_TOKEN` en Render y en cada equipo local. Usa una clave larga, distinta al `DJANGO_SECRET_KEY`.
2. Ejecuta migraciones en Render para crear las tablas `sync_*`.
3. En el primer arranque local, abre Electron con red para descargar usuarios, tiendas, productos, inventario y media.
4. Usa `SyncConflict` en el admin de Django para revisar conflictos. El sistema conserva el dato local si este es mas reciente que el remoto.
5. Manten respaldos de la base de Render y de la base PostgreSQL local de cada equipo.

La cola `SyncOutbox` se deduplica por registro antes de enviarse: si un producto se edita varias veces offline, se sube el ultimo estado, no una cadena de cambios repetidos. Las eliminaciones se envian como tombstones para que no reaparezcan al volver a sincronizar.

## Uso

Instala dependencias de Node una vez:

```bash
npm install
```

Instala dependencias de Python si el entorno virtual aun no esta listo:

```bash
venv\Scripts\python.exe -m pip install -r requirements.txt
```

Abre la app:

```bash
npm run electron
```

En el primer arranque con SQLite se crea `local.sqlite3`. Con PostgreSQL debes tener creada la base local y el usuario de PostgreSQL; Electron ejecuta migraciones al iniciar.

Si necesitas crear o actualizar el acceso local:

```text
usuario: superadmin
password: la clave definida en SUPERADMIN_PASSWORD o la clave sincronizada desde Render
```

Para cambiar esa clave en el primer arranque:

```bash
set SUPERADMIN_PASSWORD=TuClaveSegura123!
npm run electron
```

Si la base local ya existe, Electron no vuelve a resetear el password salvo que lo fuerces:

```bash
set ELECTRON_BOOTSTRAP_ACCESS=1
npm run electron
```

## Que falta para un instalador 100% portable

Para usarlo en otra computadora sin preparar nada, todavia falta empaquetar:

- Runtime de Python o una estrategia de instalacion de Python.
- Dependencias de `requirements.txt`.
- Dependencias de Node ya descargadas.
- Un instalador con `electron-builder` o herramienta equivalente.
- Plan de respaldo/sincronizacion para PostgreSQL local si habra mas de una caja o equipo.

Para trabajar localmente en esta maquina, basta con `venv`, `node_modules` y PostgreSQL local configurado en `.env`.
