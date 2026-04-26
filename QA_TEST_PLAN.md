# Plan de pruebas QA del ERP

## Perfil de pruebas

Comando para crear o actualizar el perfil:

```bash
python manage.py create_qa_profile
```

Credenciales por defecto:

- Usuario: `qa_tester`
- Password: `QaTest123!`
- Tienda activa: `Tienda QA`
- Rol: `Admin de Tienda`

Datos base creados:

- Categoria: `Categoria QA`
- Proveedor: `Proveedor QA`
- Cliente: `Cliente QA`
- Producto: `Producto QA`
- Impuesto: `ISV QA 15`
- Datos fiscales: `Empresa QA S.A.`
- Caja abierta: monto inicial `L 100.00`

## Pruebas de navegacion

1. Iniciar sesion con `qa_tester`.
2. Confirmar que el sidebar muestra: Dashboard, Tiendas, Categorias, Productos, Proveedores, Clientes, Tasas de impuesto, Datos fiscales, Compras, Ventas, Cajas, Movimientos de caja, Movimientos de inventario, Usuarios si aplica.
3. Abrir cada opcion del menu.
4. Resultado esperado: cada pagina carga con estado HTTP 200, titulo visible y sin errores `Reverse`, `TemplateSyntaxError` o permisos incorrectos.

## Catalogos

### Categorias

1. Abrir `/erp/category/list/`.
2. Crear una categoria nueva.
3. Editar nombre y descripcion.
4. Eliminar solo si no tiene productos asociados.
5. Resultado esperado: la lista refleja cambios y no aparecen categorias de otra tienda.

### Productos

1. Abrir `/erp/product/list/`.
2. Crear un producto con categoria, impuesto, costo, precio, stock y stock minimo.
3. Probar busqueda por nombre o codigo.
4. Probar filtro de stock bajo.
5. Editar categoria/precio/stock.
6. Resultado esperado: `category` y `cat` quedan sincronizados y el producto aparece en ventas/compras.

### Clientes

1. Abrir `/erp/client/list/`.
2. Crear cliente con identidad, RTN, telefono, email y credito.
3. Editar datos de contacto.
4. Resultado esperado: el cliente aparece en ventas y respeta la tienda activa.

### Proveedores

1. Abrir `/erp/supplier/list/`.
2. Crear proveedor con RTN, contacto, telefono, email y direccion.
3. Editar proveedor.
4. Resultado esperado: el proveedor aparece en compras.

### Tasas de impuesto

1. Abrir `/erp/tax-rate/list/`.
2. Crear una tasa activa.
3. Marcar una tasa como predeterminada.
4. Resultado esperado: solo una tasa queda como predeterminada por tienda.

## Fiscal

### Datos fiscales

1. Abrir `/erp/fiscal-data/`.
2. Completar razon social, RTN, CAI, rango y prefijo fiscal.
3. Guardar y volver a abrir.
4. Resultado esperado: se redirige a edicion si la tienda ya tiene datos fiscales.

## Caja

### Cajas

1. Abrir `/erp/cash-session/list/`.
2. Abrir caja con monto inicial.
3. Cerrar caja con monto contado.
4. Resultado esperado: estado cambia de `Abierta` a `Cerrada`, diferencia se calcula correctamente.

### Movimientos de caja

1. Abrir `/erp/cash-movement/list/`.
2. Crear ingreso o egreso sobre una caja abierta.
3. Resultado esperado: el monto esperado de la caja se recalcula.

## Compras

1. Abrir `/erp/purchase/list/`.
2. Crear compra seleccionando proveedor y productos.
3. Confirmar compra.
4. Ver movimientos de inventario.
5. Anular compra.
6. Resultado esperado: al confirmar aumenta stock y genera movimiento `Compra`; al anular revierte stock y genera movimiento `Anulacion compra`.

## Ventas

1. Abrir `/erp/sale/list/`.
2. Crear venta con cliente y productos.
3. Confirmar venta.
4. Descargar PDF de factura.
5. Anular venta.
6. Resultado esperado: al confirmar descuenta stock, asigna numero fiscal si es factura, PDF abre correctamente; al anular devuelve stock.

## Dashboard y reportes

1. Abrir `/erp/dashboard/`.
2. Cambiar filtros de anio/mes.
3. Ver KPIs, graficas y snapshots de inventario.
4. Abrir `/report/sale/`.
5. Buscar ventas por rango de fechas.
6. Resultado esperado: los totales solo consideran la tienda activa.

## Pruebas automaticas

Ejecutar:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Resultado esperado actual:

- `check`: sin errores.
- `test`: suite completa en verde.
- `makemigrations --check --dry-run`: `No changes detected`.
