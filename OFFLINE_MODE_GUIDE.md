# Guia de Implementacion Offline

## Que hace esta implementacion
El dashboard usa tres piezas:

1. `service-worker.js`
   - Cachea recursos estaticos.

2. `offline-storage.js`
   - Guarda respuestas del dashboard en IndexedDB.

3. `dashboard.js`
   - Coordina la carga normal, el fallback al cache y el estado visual offline.

## Flujo normal
1. El usuario abre el dashboard.
2. Se registra el service worker.
3. El frontend pide el resumen al backend.
4. Si responde bien, los datos se pintan y se guardan en cache.

## Flujo offline
1. Falla la red o el servidor.
2. El frontend intenta recuperar el ultimo snapshot del dashboard.
3. Si existe cache, lo muestra.
4. Se activa el indicador offline.

## Flujo de reconexion
1. El navegador vuelve a estar online.
2. El dashboard oculta el indicador.
3. Se hace una nueva solicitud para refrescar la informacion.

## Notas tecnicas
- El cache se organiza por anio y mes.
- La expiracion del cache es de 24 horas.
- Si el navegador no soporta IndexedDB, el dashboard sigue funcionando sin cache local.

## Comandos utiles

### Limpiar cache desde consola
```javascript
window.offlineStorage.clearAll();
```

### Ver espacio usado
```javascript
window.offlineStorage.getStorageInfo().then(console.log);
```

## Limites
- El modo offline cubre lectura del dashboard.
- No sincroniza altas, ediciones o ventas nuevas.
- Algunas metricas avanzadas dependen del modelo actual disponible en el repo.
