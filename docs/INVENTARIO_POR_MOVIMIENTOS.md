# Inventario por movimientos

## Regla principal

El stock actual de un producto se mantiene como un valor cacheado en `Product.stock`, pero ya no debe editarse como la fuente principal de verdad. La fuente auditable es `InventoryMovement`.

Cada entrada o salida registra:

- producto
- tipo de movimiento
- cantidad
- stock anterior
- stock posterior
- referencia del documento
- usuario y fecha

## Tipos de entrada

- `purchase`: compra confirmada
- `sale_cancel`: anulacion de venta
- `adjustment_in`: ajuste manual de entrada
- `return_sale`: devolucion de cliente

## Tipos de salida

- `sale`: venta confirmada
- `purchase_cancel`: anulacion de compra
- `adjustment_out`: ajuste manual de salida
- `return_purchase`: devolucion a proveedor

## Flujo operativo

1. Crear producto con stock inicial genera un movimiento `adjustment_in`.
2. Confirmar compra genera movimiento `purchase`.
3. Anular compra genera movimiento `purchase_cancel`.
4. Confirmar venta genera movimiento `sale`.
5. Anular venta genera movimiento `sale_cancel`.
6. Cambiar manualmente el stock del producto genera `adjustment_in` o `adjustment_out`.

Si un movimiento de salida deja el stock negativo, se rechaza la operacion.

## Mantenimiento

Para corregir productos viejos desde el ultimo movimiento registrado:

```bash
venv\Scripts\python.exe manage.py recalculate_stock_from_movements --dry-run
venv\Scripts\python.exe manage.py recalculate_stock_from_movements
```

El comando no inventa movimientos historicos. Solo alinea `Product.stock` con el ultimo `stock_after` disponible por producto.
