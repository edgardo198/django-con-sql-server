# Manual de usuario del sistema

## 1. Objetivo del sistema

Este sistema permite administrar una o varias tiendas desde una misma plataforma. Sus funciones principales son:

- Registrar ventas, imprimir tickets y controlar saldos pendientes.
- Registrar compras a proveedores y actualizar inventario al confirmar.
- Administrar productos, categorias, clientes y proveedores.
- Controlar caja, movimientos de efectivo y cuentas por cobrar.
- Configurar datos fiscales, CAI, rangos de facturacion e impuestos.
- Administrar tiendas, usuarios, roles y permisos.
- Consultar dashboard, reportes e indicadores de ventas e inventario.

El sistema trabaja por tienda activa. Esto significa que las ventas, compras, productos, clientes, proveedores, caja y reportes se muestran segun la tienda seleccionada por el usuario.

## 2. Acceso al sistema

1. Abra la direccion del sistema en el navegador.
2. Ingrese su usuario y password.
3. Presione **Iniciar sesion**.
4. Al entrar vera el dashboard de la tienda activa.

Si el usuario tiene acceso a varias tiendas, puede cambiar la tienda desde el selector ubicado en la barra superior. Todas las operaciones posteriores se registraran en la tienda seleccionada.

## 3. Navegacion general

El sistema puede mostrarse con menu vertical o menu horizontal. En ambos casos contiene las mismas secciones:

- **Inicio**: dashboard general.
- **Ventas**: ventas, reporte de ventas y clientes.
- **Compras**: compras y proveedores.
- **Inventario**: productos, categorias y movimientos de inventario.
- **Finanzas**: cajas, movimientos de caja, cuentas por cobrar, tasas de impuesto y datos fiscales.
- **Administracion**: tiendas y usuarios.

Desde el menu de usuario se puede cambiar entre menu vertical y horizontal.

## 4. Roles y permisos

Las opciones visibles dependen del rol asignado.

### Super Admin

Puede crear, editar, eliminar y ver todos los modulos:

- Tiendas.
- Usuarios.
- Categorias.
- Productos.
- Clientes.
- Proveedores.
- Tasas de impuesto.
- Datos fiscales.
- Cajas.
- Movimientos de caja.
- Movimientos de inventario.
- Compras.
- Ventas.
- Pagos.

### Admin de Tienda

Administra una o varias tiendas asignadas. Puede gestionar usuarios de menor nivel y operar los modulos principales de la tienda.

### Subgerente

Puede operar ventas, compras, productos, clientes, proveedores, caja y consultar inventario. Tiene permisos reducidos para configuraciones sensibles.

### Vendedor

Puede registrar ventas, clientes, caja y consultar productos/inventario. No administra usuarios, tiendas ni configuraciones fiscales.

## 5. Dashboard

Ruta: **Inicio / Dashboard**

El dashboard muestra indicadores de la tienda activa:

- Ventas del periodo.
- Ventas del mes.
- Total de productos y unidades en inventario.
- Producto mas vendido.
- Cliente con mayor facturacion.
- Graficos anuales y diarios.
- Productos con stock bajo.
- Movimientos recientes.

Uso recomendado:

1. Seleccione la tienda activa.
2. Entre a **Inicio**.
3. Revise las tarjetas de resumen.
4. Use los graficos para analizar ventas por fecha, producto y cliente.
5. Revise alertas de stock bajo antes de hacer compras.

## 6. Tiendas

Ruta: **Administracion / Tiendas**

Una tienda representa una sucursal, empresa o punto de venta.

### Crear tienda

1. Entre a **Administracion / Tiendas**.
2. Presione **Nuevo registro**.
3. Complete:
   - Nombre de la tienda.
   - Codigo interno.
   - RTN.
   - Telefono.
   - Correo.
   - Direccion.
   - Logo.
   - Estado activo.
4. Presione **Guardar registro**.

### Editar tienda

1. En el listado, presione el boton de editar.
2. Actualice la informacion.
3. Guarde los cambios.

### Cambiar tienda activa

1. En la barra superior, abra el selector de tienda.
2. Elija la tienda con la que desea trabajar.
3. Verifique que el nombre de la tienda aparezca en la barra superior.

Importante: antes de vender, comprar o crear productos, confirme que esta en la tienda correcta.

## 7. Usuarios

Ruta: **Administracion / Usuarios**

Los usuarios acceden al sistema y reciben permisos mediante roles.

### Crear usuario

1. Entre a **Administracion / Usuarios**.
2. Presione **Nuevo registro**.
3. Complete:
   - Nombres.
   - Apellidos.
   - Email.
   - Username.
   - Password.
   - Imagen.
   - Roles.
   - Tiendas disponibles.
   - Tienda activa.
4. Presione **Guardar registro**.

### Editar usuario

1. Abra el listado de usuarios.
2. Presione editar.
3. Modifique datos, roles o tiendas.
4. Si no desea cambiar la password, deje el campo password vacio.
5. Guarde.

### Reglas importantes

- Cada usuario debe tener al menos un rol.
- La tienda activa debe estar dentro de las tiendas disponibles.
- Un administrador solo puede asignar roles y tiendas que tenga permitidos.
- Para desactivar un acceso, edite el usuario o retire permisos segun corresponda.

## 8. Categorias

Ruta: **Inventario / Categorias**

Las categorias organizan los productos.

### Crear categoria

1. Entre a **Inventario / Categorias**.
2. Presione **Nuevo registro**.
3. Ingrese:
   - Nombre.
   - Descripcion.
   - Estado activo.
4. Guarde.

### Uso recomendado

Cree categorias antes de registrar productos. Ejemplos:

- Abarrotes.
- Lacteos.
- Tecnologia.
- Servicios.
- Medicamentos.

## 9. Tasas de impuesto

Ruta: **Finanzas / Tasas de impuesto**

Define los impuestos aplicables a productos.

### Crear tasa

1. Entre a **Finanzas / Tasas de impuesto**.
2. Presione **Nuevo registro**.
3. Complete:
   - Nombre, por ejemplo `ISV 15`.
   - Porcentaje, por ejemplo `15.00`.
   - Codigo, por ejemplo `ISV15`.
   - Predeterminada, si sera la tasa principal.
   - Activa.
4. Guarde.

Si marca una tasa como predeterminada, el sistema desmarca las demas tasas predeterminadas de la misma tienda.

## 10. Productos

Ruta: **Inventario / Productos**

Los productos son los articulos o servicios que se venden y compran.

### Crear producto

1. Entre a **Inventario / Productos**.
2. Presione **Nuevo registro**.
3. Complete:
   - Nombre.
   - Categoria.
   - Imagen.
   - Codigo de barras.
   - Codigo interno.
   - Descripcion.
   - Unidad.
   - Costo.
   - Precio de venta.
   - Stock.
   - Stock minimo.
   - Tasa de impuesto.
   - Permite fraccion.
   - Es servicio.
   - Activo.
4. Guarde.

### Codigo de barras

El campo **codigo de barras** permite usar lector en ventas y compras. Puede ser un codigo real del producto o un codigo interno propio.

Buenas practicas:

- No repita el mismo codigo de barras dentro de la misma tienda.
- Use **codigo interno** para referencias propias.
- Si el producto es servicio, marque **Es servicio** para que no descuente inventario.
- Si se vende por libra, metro o litro, marque **Permite fraccion** cuando aplique.

### Stock minimo

El stock minimo ayuda a identificar productos que deben reponerse. El dashboard muestra alertas cuando el stock llega o baja de ese minimo.

## 11. Proveedores

Ruta: **Compras / Proveedores**

Los proveedores se usan al registrar compras.

### Crear proveedor

1. Entre a **Compras / Proveedores**.
2. Presione **Nuevo registro**.
3. Complete:
   - Nombre.
   - RTN.
   - Contacto.
   - Telefono.
   - Correo.
   - Direccion.
   - Activo.
4. Guarde.

Solo los proveedores activos aparecen al crear compras.

## 12. Clientes

Ruta: **Ventas / Clientes**

Los clientes se usan al registrar ventas y cuentas por cobrar.

### Crear cliente

1. Entre a **Ventas / Clientes**.
2. Presione **Nuevo registro**.
3. Complete:
   - Nombres.
   - Apellidos.
   - Identidad.
   - RTN.
   - Fecha de nacimiento.
   - Direccion.
   - Telefono.
   - Correo.
   - Sexo.
   - Limite de credito.
   - Cliente a credito.
   - Activo.
4. Guarde.

### Crear cliente desde una venta

1. Entre a **Ventas / Ventas**.
2. Presione **Nuevo registro**.
3. En el campo Cliente, presione **Nuevo cliente**.
4. Complete los datos del cliente.
5. Guarde.
6. El cliente queda seleccionado en la venta actual.

## 13. Datos fiscales

Ruta: **Finanzas / Datos fiscales**

Los datos fiscales se usan para emitir facturas y tickets con informacion de la tienda.

### Configurar datos fiscales

1. Entre a **Finanzas / Datos fiscales**.
2. Cree o edite el registro de la tienda.
3. Complete:
   - Razon social.
   - Nombre comercial.
   - RTN.
   - Direccion fiscal.
   - Telefono.
   - Correo.
   - CAI vigente.
   - Fecha inicio CAI.
   - Fecha fin CAI.
   - Prefijo fiscal.
   - Rango inicial.
   - Rango final.
   - Siguiente numero.
   - Leyenda para factura.
4. Guarde.

Importante:

- Si la venta se confirma como factura, el sistema asigna numero fiscal usando estos datos.
- Si el CAI esta vencido o el rango se agoto, la confirmacion de factura puede fallar.
- Mantenga actualizado el campo **Siguiente numero** segun el correlativo autorizado.

## 14. Cajas

Ruta: **Finanzas / Cajas**

La caja controla el dinero esperado por ventas, ingresos y egresos.

### Abrir caja

1. Entre a **Finanzas / Cajas**.
2. Presione **Nuevo registro**.
3. Ingrese:
   - Monto de apertura.
   - Observaciones.
4. Guarde.

La caja queda en estado **Abierta**.

### Cerrar caja

1. Entre a **Finanzas / Cajas**.
2. En una caja abierta, presione **Cerrar**.
3. Ingrese:
   - Monto de cierre.
   - Observacion.
4. Guarde.

El sistema calcula:

- Monto esperado.
- Diferencia entre monto contado y monto esperado.
- Fecha de cierre.

## 15. Movimientos de caja

Ruta: **Finanzas / Movimientos de caja**

Permite registrar entradas o salidas manuales de efectivo.

### Crear movimiento

1. Entre a **Finanzas / Movimientos de caja**.
2. Presione **Nuevo registro**.
3. Seleccione una caja abierta.
4. Elija el tipo de movimiento.
5. Ingrese monto.
6. Escriba descripcion y referencia.
7. Guarde.

El sistema recalcula el monto esperado de la caja.

### Eliminar movimiento

1. En el listado, presione eliminar.
2. Confirme la accion.
3. El sistema recalcula la caja relacionada.

## 16. Compras

Ruta: **Compras / Compras**

Las compras registran entrada de mercaderia. Una compra primero queda en borrador y actualiza inventario cuando se confirma.

### Crear compra

1. Entre a **Compras / Compras**.
2. Presione **Nuevo registro**.
3. Seleccione el proveedor.
4. Ingrese:
   - Numero interno.
   - Factura proveedor.
   - Condicion de pago.
   - Fecha de compra.
   - Fecha de vencimiento, si aplica.
   - Monto pagado.
   - Observacion.
5. Agregue productos al detalle.
6. Revise subtotal, ISV, total y saldo.
7. Presione **Guardar registro**.

### Agregar productos a una compra

Puede hacerlo de dos formas:

1. **Buscador de productos**:
   - Escriba nombre, codigo, codigo interno o descripcion.
   - Seleccione el producto.
   - Ajuste costo y cantidad en la tabla.

2. **Lector de codigo de barras**:
   - Coloque el cursor en **Lector de codigo de barras**.
   - Escanee el producto o escriba el codigo.
   - Presione Enter o el boton **Agregar**.
   - Si el producto ya existe en la compra, aumenta la cantidad.

### Editar compra

1. En el listado de compras, presione editar.
2. Solo se pueden editar compras en estado **Borrador**.
3. Modifique proveedor, fechas, productos, costos o cantidades.
4. Guarde.

### Confirmar compra

1. En el listado, busque una compra en borrador.
2. Presione **Confirmar**.
3. El sistema:
   - Cambia el estado a confirmada.
   - Aumenta el stock de los productos.
   - Registra movimientos de inventario.

### Anular compra

1. Busque una compra confirmada.
2. Presione **Anular**.
3. Ingrese motivo si se solicita.
4. El sistema:
   - Cambia el estado a anulada.
   - Resta del inventario las unidades que habia agregado.
   - Registra movimiento de anulacion.

## 17. Ventas

Ruta: **Ventas / Ventas**

Las ventas registran salidas de producto y cobros a clientes. Pueden guardarse en borrador o guardarse e imprimirse.

### Crear venta

1. Entre a **Ventas / Ventas**.
2. Presione **Nuevo registro**.
3. Seleccione cliente.
4. Seleccione caja abierta, si cobrara en efectivo o desea registrar movimiento de caja.
5. Seleccione:
   - Documento.
   - Condicion.
   - Fecha de venta.
   - Fecha de vencimiento, si es credito.
6. Agregue productos al detalle.
7. Ingrese descuento general si aplica.
8. Ingrese monto pagado.
9. Revise subtotal, ISV, total y saldo.
10. Presione **Guardar registro** o **Guardar e imprimir ticket**.

### Agregar productos a una venta

Puede hacerlo de dos formas:

1. **Buscador de productos**:
   - Escriba nombre, codigo de barras, codigo interno, descripcion o categoria.
   - Seleccione el producto.
   - Ajuste precio y cantidad en la tabla.

2. **Lector de codigo de barras**:
   - Coloque el cursor en **Lector de codigo de barras**.
   - Escanee el producto o escriba el codigo.
   - Presione Enter o **Agregar**.
   - Si el producto ya esta en la venta, aumenta la cantidad.

### Guardar venta

Al presionar **Guardar registro**, la venta se guarda. Si queda en borrador, no descuenta inventario hasta confirmarse.

### Guardar e imprimir ticket

Al presionar **Guardar e imprimir ticket**, el sistema intenta:

1. Guardar la venta.
2. Confirmarla.
3. Descontar inventario.
4. Registrar movimiento de caja si hay monto pagado y caja seleccionada.
5. Abrir el ticket para impresion.

Si la venta se guarda pero no puede confirmarse, el sistema muestra una advertencia. Causas comunes:

- Stock insuficiente.
- CAI vencido.
- Rango fiscal agotado.
- Faltan datos fiscales.

### Confirmar venta

1. En el listado, busque una venta en borrador.
2. Presione **Confirmar**.
3. El sistema:
   - Valida stock.
   - Asigna numero fiscal si es factura.
   - Descuenta inventario.
   - Registra movimiento de inventario.
   - Registra cobro en caja si aplica.

### Anular venta

1. Busque una venta confirmada.
2. Presione **Anular**.
3. Ingrese motivo si se solicita.
4. El sistema:
   - Cambia estado a anulada.
   - Devuelve stock al inventario.
   - Registra movimiento de anulacion.

### Imprimir ticket

Desde una venta confirmada o al guardar e imprimir, el sistema abre el ticket termico. Use la opcion de impresion del navegador o impresora configurada.

## 18. Cuentas por cobrar

Ruta: **Finanzas / Cuentas por cobrar**

Muestra ventas confirmadas con saldo pendiente.

### Consultar cuentas

1. Entre a **Finanzas / Cuentas por cobrar**.
2. Use filtros por cliente o estado de vencimiento:
   - Vencidas.
   - Vencen hoy.
   - Abiertas.
   - Sin fecha de vencimiento.
3. Revise totales, facturas pendientes y saldo.

### Ver detalle

1. En una cuenta pendiente, abra el detalle.
2. Revise:
   - Datos de la venta.
   - Cliente.
   - Total.
   - Pagado.
   - Saldo.
   - Historial de abonos.

### Registrar abono

1. En el detalle de cuenta por cobrar, presione **Registrar abono**.
2. Complete:
   - Caja, si el pago es en efectivo.
   - Metodo de pago.
   - Monto.
   - Referencia.
   - Observacion.
   - Fecha de pago.
3. Guarde.

Reglas:

- El abono debe ser mayor que cero.
- No puede ser mayor que el saldo pendiente.
- Si el metodo es efectivo, debe seleccionar una caja abierta.

## 19. Movimientos de inventario

Ruta: **Inventario / Movimientos de inventario**

Este modulo es de consulta. Muestra entradas y salidas generadas por compras, ventas y anulaciones.

Use este listado para auditar:

- Producto.
- Tipo de movimiento.
- Cantidad.
- Stock anterior.
- Stock posterior.
- Referencia.
- Fecha.

Los movimientos se generan automaticamente al confirmar o anular compras y ventas.

## 20. Reporte de ventas

Ruta: **Ventas / Reporte de ventas**

Permite analizar ventas por periodo.

### Usar reporte

1. Entre a **Ventas / Reporte de ventas**.
2. Seleccione el periodo:
   - Dia.
   - Semana.
   - Mes.
   - Rango de fechas.
3. Consulte filas y resumen.
4. Use el reporte para revisar facturacion, clientes y comportamiento de ventas.

## 21. Flujo diario recomendado

### Inicio del dia

1. Iniciar sesion.
2. Seleccionar tienda activa.
3. Abrir caja con monto inicial.
4. Revisar dashboard y productos con stock bajo.
5. Verificar que productos tengan precio, impuesto y codigo de barras cuando aplique.

### Durante el dia

1. Registrar ventas.
2. Usar lector de codigo de barras para agilizar ventas.
3. Crear clientes nuevos desde venta si es necesario.
4. Registrar movimientos de caja manuales para ingresos o egresos.
5. Registrar compras cuando entre mercaderia.

### Cierre del dia

1. Revisar ventas del dia.
2. Revisar cuentas por cobrar.
3. Contar efectivo fisico.
4. Cerrar caja con monto real.
5. Revisar diferencia.
6. Consultar reporte de ventas.

## 22. Flujo recomendado para inventario

1. Crear categorias.
2. Crear tasas de impuesto.
3. Crear productos con costo, precio, stock minimo y codigo de barras.
4. Crear proveedores.
5. Registrar compras.
6. Confirmar compras para aumentar stock.
7. Vender productos.
8. Confirmar ventas para descontar stock.
9. Revisar movimientos de inventario.
10. Reponer productos con stock bajo.

## 23. Uso del lector de codigo de barras

El sistema acepta lectores que funcionan como teclado. La mayoria de lectores escribe el codigo y envia Enter automaticamente.

### Preparacion

1. Conecte el lector al equipo.
2. Abra una venta o compra.
3. Haga clic en el campo **Lector de codigo de barras**.
4. Escanee el producto.

### En ventas

- Busca el producto por codigo de barras o codigo interno.
- Agrega el producto a la venta.
- Si ya existe, suma una unidad.
- Permite cambiar cantidad y precio manualmente.

### En compras

- Busca el producto por codigo de barras o codigo interno.
- Agrega el producto a la compra.
- Si ya existe, suma una unidad.
- Permite cambiar cantidad y costo manualmente.

### Errores comunes

- **No se encontro un producto activo con ese codigo**: revise que el producto exista, este activo y pertenezca a la tienda activa.
- **Producto duplicado**: el sistema no permite repetir codigo de barras dentro de la misma tienda.
- **Escaneo en tienda incorrecta**: cambie la tienda activa antes de registrar la operacion.

## 24. Estados de documentos

### Ventas

- **Borrador**: registrada, editable, no descuenta stock.
- **Confirmada**: valida stock, asigna numero fiscal si aplica, descuenta stock.
- **Anulada**: devuelve stock y deja constancia de anulacion.

### Compras

- **Borrador**: registrada, editable, no aumenta stock.
- **Confirmada**: aumenta stock y genera movimientos de inventario.
- **Anulada**: revierte el stock agregado.

## 25. Consejos y buenas practicas

- Siempre revise la tienda activa antes de operar.
- Abra caja antes de empezar a vender en efectivo.
- Mantenga actualizados los datos fiscales antes de confirmar facturas.
- Use codigos de barras para reducir errores de captura.
- Registre compras antes de vender productos nuevos.
- No elimine documentos confirmados; use anulacion para conservar historial.
- Revise cuentas por cobrar diariamente.
- Cierre caja al final de cada jornada.
- Use roles para limitar acceso a funciones sensibles.
- Revise stock bajo con frecuencia.

## 26. Solucion de problemas frecuentes

### No aparece una opcion del menu

El usuario no tiene permiso para ese modulo. Un administrador debe revisar su rol.

### No aparece un producto al vender o comprar

Verifique:

- Producto activo.
- Producto pertenece a la tienda activa.
- Codigo de barras o codigo interno correcto.
- Categoria e impuesto configurados.

### No puedo confirmar una venta

Revise:

- Stock disponible.
- Datos fiscales configurados.
- CAI vigente.
- Rango fiscal disponible.
- Cliente activo.

### No puedo registrar abono en efectivo

Debe existir una caja abierta y seleccionada.

### El saldo no queda en cero

Revise monto pagado, descuentos, impuesto y total. En cuentas por cobrar puede registrar abonos posteriores.

### La caja tiene diferencia

Compare:

- Monto de apertura.
- Ventas cobradas.
- Movimientos manuales.
- Abonos recibidos.
- Monto fisico contado.

## 27. Resumen de rutas principales

- Inicio: `/erp/dashboard/`
- Ventas: `/erp/sale/list/`
- Crear venta: `/erp/sale/add/`
- Reporte de ventas: `/report/sale/`
- Clientes: `/erp/client/list/`
- Compras: `/erp/purchase/list/`
- Crear compra: `/erp/purchase/add/`
- Proveedores: `/erp/supplier/list/`
- Productos: `/erp/product/list/`
- Categorias: `/erp/category/list/`
- Movimientos de inventario: `/erp/inventory-movement/list/`
- Cajas: `/erp/cash-session/list/`
- Movimientos de caja: `/erp/cash-movement/list/`
- Cuentas por cobrar: `/erp/accounts-receivable/list/`
- Tasas de impuesto: `/erp/tax-rate/list/`
- Datos fiscales: `/erp/fiscal-data/`
- Tiendas: `/user/organization/list/`
- Usuarios: `/user/list/`

## 28. Recomendacion de capacitacion

Para entrenar usuarios nuevos:

1. Explicar tienda activa y roles.
2. Crear un cliente.
3. Crear categoria, impuesto y producto con codigo de barras.
4. Abrir caja.
5. Registrar una compra y confirmarla.
6. Registrar una venta con lector de codigo de barras.
7. Guardar e imprimir ticket.
8. Registrar una venta a credito.
9. Registrar abono en cuentas por cobrar.
10. Cerrar caja.
11. Revisar dashboard y reporte de ventas.

