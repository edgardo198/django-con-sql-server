var tblPurchaseProducts;

var purchaseDetail = {
    items: {
        supplier: '',
        number: '',
        supplier_invoice: '',
        payment_term: 'cash',
        date_joined: '',
        due_date: '',
        subtotal: 0.00,
        tax_total: 0.00,
        total: 0.00,
        amount_paid: 0.00,
        balance: 0.00,
        observation: '',
        products: []
    },
    calculate: function () {
        var subtotal = 0.00;
        var taxTotal = 0.00;
        var amountPaid = parseFloat($('input[name="amount_paid"]').val() || 0);

        $.each(this.items.products, function (pos, item) {
            item.pos = pos;
            item.cost = parseFloat(item.cost || 0);
            item.cant = parseInt(item.cant || 1);
            item.tax_rate = parseFloat(item.tax_rate || 0);
            item.subtotal_before_tax = item.cost * item.cant;
            item.tax_amount = item.subtotal_before_tax * (item.tax_rate / 100);
            item.subtotal = item.subtotal_before_tax + item.tax_amount;
            subtotal += item.subtotal_before_tax;
            taxTotal += item.tax_amount;
        });

        this.items.subtotal = subtotal;
        this.items.tax_total = taxTotal;
        this.items.total = subtotal + taxTotal;
        this.items.amount_paid = amountPaid;
        this.items.balance = this.items.total - amountPaid;

        $('input[name="subtotal"]').val(this.items.subtotal.toFixed(2));
        $('input[name="tax_total"]').val(this.items.tax_total.toFixed(2));
        $('input[name="iva"]').val(this.items.tax_total.toFixed(2));
        $('input[name="total"]').val(this.items.total.toFixed(2));
        $('input[name="balance"]').val(this.items.balance.toFixed(2));
    },
    add: function (item) {
        var existing = this.items.products.find(function (product) {
            return String(product.id) === String(item.id);
        });

        if (existing) {
            existing.cant = parseInt(existing.cant || 1) + 1;
            this.list();
            return;
        }

        item.cost = parseFloat(item.cost || 0);
        item.cant = parseInt(item.cant || 1);
        item.tax_rate = parseFloat(item.tax_rate || 0);
        this.items.products.push(item);
        this.list();
    },
    list: function () {
        this.calculate();

        tblPurchaseProducts = $('#tblPurchaseProducts').DataTable({
            responsive: true,
            autoWidth: false,
            destroy: true,
            data: this.items.products,
            columns: [
                {"data": "id"},
                {"data": "name"},
                {
                    data: null,
                    render: function (data, type, row) {
                        return (row.category && row.category.name) || (row.cat && row.cat.name) || '';
                    }
                },
                {"data": "cost"},
                {"data": "cant"},
                {"data": "tax_rate"},
                {"data": "subtotal"},
            ],
            columnDefs: [
                {
                    targets: [0],
                    class: 'text-center',
                    orderable: false,
                    render: function () {
                        return '<a rel="remove" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
                    }
                },
                {
                    targets: [3],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<input type="number" name="cost" class="form-control form-control-sm" min="0" step="0.01" value="' + parseFloat(row.cost || 0).toFixed(2) + '">';
                    }
                },
                {
                    targets: [4],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<input type="number" name="cant" class="form-control form-control-sm" min="1" step="1" value="' + parseInt(row.cant || 1) + '">';
                    }
                },
                {
                    targets: [5],
                    class: 'text-center',
                    orderable: false,
                    render: function (data) {
                        return parseFloat(data || 0).toFixed(2) + '%';
                    }
                },
                {
                    targets: [6],
                    class: 'text-center',
                    orderable: false,
                    render: function (data) {
                        return 'L ' + parseFloat(data || 0).toFixed(2);
                    }
                }
            ]
        });
    }
};

$(function () {
    $('.select2').select2({
        theme: 'bootstrap4',
        language: 'es'
    });

    purchaseDetail.items.products = window.purchaseInitialDetail || [];
    purchaseDetail.list();

    $('.purchase-product-search').select2({
        theme: 'bootstrap4',
        language: 'es',
        allowClear: true,
        ajax: {
            delay: 250,
            type: 'POST',
            url: window.location.pathname,
            data: function (params) {
                return {
                    term: params.term,
                    action: 'search_products'
                };
            },
            processResults: function (data) {
                return {
                    results: data
                };
            }
        },
        placeholder: 'Ingrese una descripcion',
        minimumInputLength: 1
    }).on('select2:select', function (e) {
        var data = e.params.data;
        data.cant = parseInt(data.cant || 1);
        data.cost = parseFloat(data.cost || 0);
        data.tax_rate = parseFloat(data.tax_rate || 0);
        purchaseDetail.add(data);
        $(this).val(null).trigger('change');
    });

    $('.btnRemoveAll').on('click', function () {
        if (purchaseDetail.items.products.length === 0) {
            return false;
        }
        alert_action('Notificacion', 'Estas seguro de eliminar todos los productos del detalle?', function () {
            purchaseDetail.items.products = [];
            purchaseDetail.list();
        });
    });

    $('#tblPurchaseProducts tbody')
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblPurchaseProducts.cell($(this).closest('td, li')).index();
            alert_action('Notificacion', 'Estas seguro de eliminar este producto?', function () {
                purchaseDetail.items.products.splice(tr.row, 1);
                purchaseDetail.list();
            });
        })
        .on('change', 'input[name="cost"]', function () {
            var tr = tblPurchaseProducts.cell($(this).closest('td, li')).index();
            purchaseDetail.items.products[tr.row].cost = parseFloat($(this).val() || 0);
            purchaseDetail.list();
        })
        .on('change', 'input[name="cant"]', function () {
            var tr = tblPurchaseProducts.cell($(this).closest('td, li')).index();
            purchaseDetail.items.products[tr.row].cant = parseInt($(this).val() || 1);
            purchaseDetail.list();
        });

    $('input[name="amount_paid"]').on('input', function () {
        purchaseDetail.calculate();
    });

    $('form').on('submit', function (e) {
        e.preventDefault();

        if (purchaseDetail.items.products.length === 0) {
            message_error('Debe ingresar al menos un producto');
            return false;
        }

        purchaseDetail.items.supplier = $('select[name="supplier"]').val();
        if (!purchaseDetail.items.supplier) {
            message_error('Debe seleccionar un proveedor antes de registrar la compra');
            return false;
        }

        var hasInvalidProduct = purchaseDetail.items.products.some(function (item) {
            return !item.id || parseInt(item.cant || 0) <= 0;
        });
        if (hasInvalidProduct) {
            message_error('Hay un producto sin identificador valido o con cantidad incorrecta');
            return false;
        }

        purchaseDetail.items.number = $('input[name="number"]').val();
        purchaseDetail.items.supplier_invoice = $('input[name="supplier_invoice"]').val();
        purchaseDetail.items.payment_term = $('select[name="payment_term"]').val();
        purchaseDetail.items.date_joined = $('input[name="date_joined"]').val();
        purchaseDetail.items.due_date = $('input[name="due_date"]').val();
        purchaseDetail.items.amount_paid = $('input[name="amount_paid"]').val();
        purchaseDetail.items.observation = $('textarea[name="observation"]').val();

        var parameters = new FormData();
        parameters.append('action', $('input[name="action"]').val());
        parameters.append('purchase', JSON.stringify(purchaseDetail.items));

        submit_with_ajax(window.location.pathname, 'Notificacion', 'Estas seguro de realizar la siguiente accion?', parameters, function () {
            location.href = '/erp/purchase/list/';
        });
    });
});
