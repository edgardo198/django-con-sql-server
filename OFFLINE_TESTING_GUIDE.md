# Guia de Pruebas del Dashboard Offline

## Previo
- Levanta el proyecto con `python manage.py runserver`
- Inicia sesion en el sistema
- Entra al dashboard

## Prueba 1. Registro del Service Worker
1. Abre DevTools.
2. Ve a `Application > Service Workers`.
3. Verifica que `service-worker.js` este registrado.

Resultado esperado:
- El service worker aparece activo.

## Prueba 2. Cache de assets
1. En DevTools ve a `Application > Cache Storage`.
2. Busca `dashboard-cache-v1`.

Resultado esperado:
- Existen entradas para JS y recursos estaticos del dashboard.

## Prueba 3. IndexedDB
1. En DevTools ve a `Application > IndexedDB`.
2. Revisa `DashboardDB`.

Resultado esperado:
- Existe el store `dashboards`.

## Prueba 4. Simular offline
1. Abre la pestana `Network`.
2. Activa `Offline`.
3. Recarga el dashboard.

Resultado esperado:
- El dashboard sigue mostrando datos desde cache.
- Se muestra el indicador de modo offline.

## Prueba 5. Reconexion
1. Desactiva `Offline`.
2. Espera unos segundos.

Resultado esperado:
- El indicador offline desaparece.
- El tablero intenta actualizar los datos.

## Prueba 6. Cambio de filtros
1. Cambia anio y mes.
2. Pulsa actualizar.

Resultado esperado:
- Los KPIs y graficos cambian.
- Si no hay datos, el dashboard no se rompe.

## Prueba 7. Mensajes de error
1. Fuerza un error en la consola o backend.

Resultado esperado:
- Se muestra alerta con `Swal` o `alert`.

## Checklist final
- [ ] Service Worker activo
- [ ] Cache Storage presente
- [ ] IndexedDB creada
- [ ] Dashboard usable offline
- [ ] Reconexion funciona
- [ ] Filtros funcionando
- [ ] Sin errores JS criticos
