var tblSaleProducts;
var DEFAULT_TAX_RATE = 15.00;

function getProductImage(product) {
    return (product && product.image) ? product.image : (window.saleDefaultProductImage || '/static/img/imagen.png');
}

function escapeHtml(value) {
    return $('<div>').text(value || '').html();
}

function renderProductImage(product) {
    return '<img src="' + getProductImage(product) + '" class="sale-product-thumb" alt="' + escapeHtml(product.name || 'Producto') + '">';
}

function renderProductOption(product) {
    if (!product.id) {
        return product.text;
    }
    var category = (product.category && product.category.name) || (product.cat && product.cat.name) || 'Sin categoria';
    var price = parseFloat(product.price || product.pvp || 0).toFixed(2);
    var html = '<div class="sale-product-option">';
    html += renderProductImage(product);
    html += '<span>';
    html += '<span class="sale-product-option-name">' + escapeHtml(product.text || product.name) + '</span>';
    html += '<span class="sale-product-option-meta">' + escapeHtml(category) + ' | L ' + price + '</span>';
    html += '</span>';
    html += '</div>';
    return $(html);
}

function getDefaultSaleItems() {
    return {
        cli: '',
        cash_session: '',
        document_type: 'invoice',
        payment_term: 'cash',
        date_joined: '',
        due_date: '',
        discount: 0.00,
        subtotal: 0.00,
        tax_total: 0.00,
        total: 0.00,
        amount_paid: 0.00,
        balance: 0.00,
        observation: '',
        products: []
    };
}

function getTodayInputDate() {
    var today = new Date();
    var month = String(today.getMonth() + 1).padStart(2, '0');
    var day = String(today.getDate()).padStart(2, '0');
    return today.getFullYear() + '-' + month + '-' + day;
}

function getAutoPrintUrl(url) {
    var separator = url.indexOf('?') === -1 ? '?' : '&';
    return url + separator + 'autoprint=1';
}

function openPendingTicketWindow() {
    var printWindow = window.open('', '_blank');
    if (printWindow) {
        printWindow.document.write(
            '<!doctype html><html lang="es"><head><title>Preparando ticket</title></head>' +
            '<body style="font-family:Arial,sans-serif;padding:24px;text-align:center;">' +
            '<h3>Preparando ticket...</h3><p>La impresion se abrira automaticamente.</p>' +
            '</body></html>'
        );
        printWindow.document.close();
    }
    return printWindow;
}

function closePendingTicketWindow(printWindow) {
    if (printWindow && !printWindow.closed) {
        printWindow.close();
    }
}

function getTaxRate(value) {
    if (value === undefined || value === null || value === '') {
        return DEFAULT_TAX_RATE;
    }
    var rate = parseFloat(value);
    return isNaN(rate) ? DEFAULT_TAX_RATE : rate;
}

var saleDetail = {
    items: getDefaultSaleItems(),
    calculate: function () {
        var subtotal = 0.00;
        var taxTotal = 0.00;
        var globalDiscount = parseFloat($('input[name="discount"]').val() || 0);
        var amountPaid = parseFloat($('input[name="amount_paid"]').val() || 0);

        $.each(this.items.products, function (pos, item) {
            item.pos = pos;
            item.price = parseFloat(item.price || item.pvp || 0);
            item.cost = parseFloat(item.cost || 0);
            item.cant = parseInt(item.cant || 1);
            item.tax_rate = getTaxRate(item.tax_rate);
            item.discount = parseFloat(item.discount || 0);
            item.subtotal_before_tax = (item.price * item.cant) - item.discount;
            if (item.subtotal_before_tax < 0) {
                item.subtotal_before_tax = 0;
            }
            item.tax_amount = item.subtotal_before_tax * (item.tax_rate / 100);
            item.subtotal = item.subtotal_before_tax + item.tax_amount;
            subtotal += item.subtotal_before_tax;
            taxTotal += item.tax_amount;
        });

        this.items.discount = globalDiscount;
        this.items.subtotal = subtotal;
        this.items.tax_total = taxTotal;
        this.items.total = (subtotal + taxTotal) - globalDiscount;
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

        item.price = parseFloat(item.price || item.pvp || 0);
        item.cost = parseFloat(item.cost || 0);
        item.cant = parseInt(item.cant || 1);
        item.tax_rate = getTaxRate(item.tax_rate);
        item.discount = parseFloat(item.discount || 0);
        this.items.products.push(item);
        this.list();
    },
    list: function () {
        this.calculate();

        tblSaleProducts = $('#tblSaleProducts').DataTable({
            responsive: true,
            autoWidth: false,
            destroy: true,
            data: this.items.products,
            columns: [
                {"data": "id"},
                {"data": "image"},
                {"data": "name"},
                {
                    data: null,
                    render: function (data, type, row) {
                        return (row.category && row.category.name) || (row.cat && row.cat.name) || '';
                    }
                },
                {"data": "price"},
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
                    targets: [1],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return renderProductImage(row);
                    }
                },
                {
                    targets: [4],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<input type="number" name="price" class="form-control form-control-sm" min="0" step="0.01" value="' + parseFloat(row.price || row.pvp || 0).toFixed(2) + '">';
                    }
                },
                {
                    targets: [5],
                    class: 'text-center',
                    orderable: false,
                    render: function (data, type, row) {
                        return '<input type="number" name="cant" class="form-control form-control-sm" min="1" step="1" value="' + parseInt(row.cant || 1) + '">';
                    }
                },
                {
                    targets: [6],
                    class: 'text-center',
                    orderable: false,
                    render: function (data) {
                        return parseFloat(data || 0).toFixed(2) + '%';
                    }
                },
                {
                    targets: [7],
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

    saleDetail.items.products = window.saleInitialDetail || [];
    saleDetail.list();

    $('.sale-product-search').select2({
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
        minimumInputLength: 1,
        templateResult: renderProductOption,
        templateSelection: function (product) {
            return product.text || product.name || '';
        },
        escapeMarkup: function (markup) {
            return markup;
        }
    }).on('select2:select', function (e) {
        var data = e.params.data;
        data.cant = parseInt(data.cant || 1);
        data.price = parseFloat(data.price || data.pvp || 0);
        data.cost = parseFloat(data.cost || 0);
        data.tax_rate = getTaxRate(data.tax_rate);
        data.discount = parseFloat(data.discount || 0);
        saleDetail.add(data);
        $(this).val(null).trigger('change');
    });

    $('.btnRemoveAll').on('click', function () {
        if (saleDetail.items.products.length === 0) {
            return false;
        }
        alert_action('Notificacion', 'Estas seguro de eliminar todos los productos del detalle?', function () {
            saleDetail.items.products = [];
            saleDetail.list();
        });
    });

    $('#tblSaleProducts tbody')
        .on('click', 'a[rel="remove"]', function () {
            var tr = tblSaleProducts.cell($(this).closest('td, li')).index();
            alert_action('Notificacion', 'Estas seguro de eliminar este producto?', function () {
                saleDetail.items.products.splice(tr.row, 1);
                saleDetail.list();
            });
        })
        .on('change', 'input[name="price"]', function () {
            var tr = tblSaleProducts.cell($(this).closest('td, li')).index();
            saleDetail.items.products[tr.row].price = parseFloat($(this).val() || 0);
            saleDetail.list();
        })
        .on('change', 'input[name="cant"]', function () {
            var tr = tblSaleProducts.cell($(this).closest('td, li')).index();
            saleDetail.items.products[tr.row].cant = parseInt($(this).val() || 1);
            saleDetail.list();
        });

    $('input[name="discount"], input[name="amount_paid"]').on('input', function () {
        saleDetail.calculate();
    });

    function clearSaleForm() {
        saleDetail.items = getDefaultSaleItems();
        $('#saleForm')[0].reset();
        $('select[name="cli"]').val(null).trigger('change');
        $('select[name="cash_session"]').val(null).trigger('change');
        $('select[name="document_type"]').val('invoice').trigger('change');
        $('select[name="payment_term"]').val('cash').trigger('change');
        $('.sale-product-search').val(null).trigger('change');
        $('input[name="date_joined"]').val(getTodayInputDate());
        $('input[name="due_date"]').val('');
        $('input[name="discount"]').val('0.00');
        $('input[name="amount_paid"]').val('0.00');
        $('textarea[name="observation"]').val('');
        saleDetail.list();
    }

    function sendTicketToPrinter(url, printWindow) {
        var printUrl = getAutoPrintUrl(url);
        if (printWindow && !printWindow.closed) {
            printWindow.location.href = printUrl;
            return;
        }
        window.open(printUrl, '_blank');
    }

    function finishSaleSave(data, printWindow) {
        var isCreate = $('input[name="action"]').val() === 'add';
        var finish = function () {
            if (isCreate) {
                clearSaleForm();
                return;
            }
            location.href = window.saleListUrl || '/erp/sale/list/';
        };

        if (data.print_url) {
            sendTicketToPrinter(data.print_url, printWindow);
        }
        if (data.warning) {
            closePendingTicketWindow(printWindow);
            Swal.fire({
                title: 'Venta guardada',
                text: data.warning,
                icon: 'warning'
            }).then(finish);
            return false;
        }
        Swal.fire({
            title: data.print_url ? 'Transaccion confirmada' : 'Venta guardada',
            text: data.print_url
                ? 'La venta se registro y el ticket se envio a impresion.'
                : 'El formulario quedo listo para registrar otra venta.',
            icon: 'success',
            timer: 1400,
            showConfirmButton: false
        }).then(finish);
    }

    function buildSalePayload(printAfterSave) {
        saleDetail.items.cli = $('select[name="cli"]').val();
        saleDetail.items.cash_session = $('select[name="cash_session"]').val();
        saleDetail.items.document_type = $('select[name="document_type"]').val();
        saleDetail.items.payment_term = $('select[name="payment_term"]').val();
        saleDetail.items.date_joined = $('input[name="date_joined"]').val();
        saleDetail.items.due_date = $('input[name="due_date"]').val();
        saleDetail.items.discount = $('input[name="discount"]').val();
        saleDetail.items.amount_paid = $('input[name="amount_paid"]').val();
        saleDetail.items.observation = $('textarea[name="observation"]').val();
        saleDetail.calculate();

        var parameters = new FormData();
        parameters.append('action', $('input[name="action"]').val());
        parameters.append('sale', JSON.stringify(saleDetail.items));
        if (printAfterSave) {
            parameters.append('print_after_save', '1');
        }
        return parameters;
    }

    function saveSale(printAfterSave) {

        if (saleDetail.items.products.length === 0) {
            message_error('Debe ingresar al menos un producto');
            return false;
        }

        var selectedClient = $('select[name="cli"]').val();
        if (!selectedClient) {
            message_error('Debe seleccionar un cliente antes de registrar la venta');
            return false;
        }

        var hasInvalidProduct = saleDetail.items.products.some(function (item) {
            return !item.id || parseInt(item.cant || 0) <= 0;
        });
        if (hasInvalidProduct) {
            message_error('Hay un producto sin identificador valido o con cantidad incorrecta');
            return false;
        }

        var parameters = buildSalePayload(printAfterSave);
        var confirmationText = printAfterSave
            ? 'Se guardara la venta y se abrira el ticket para imprimir. Deseas continuar?'
            : 'Estas seguro de realizar la siguiente accion?';
        var printWindow = null;

        submit_with_ajax(window.location.pathname, 'Notificacion', confirmationText, parameters, function (data) {
            finishSaleSave(data, printWindow);
        }, {
            beforeSend: function () {
                if (printAfterSave) {
                    printWindow = openPendingTicketWindow();
                }
            },
            onError: function () {
                closePendingTicketWindow(printWindow);
            }
        });
    }

    $('#saleForm').on('submit', function (e) {
        e.preventDefault();
        saveSale(false);
    });

    $('#btnSaveAndPrint').on('click', function () {
        saveSale(true);
    });

    $('#clientModalForm').on('submit', function (e) {
        e.preventDefault();

        var parameters = new FormData(this);
        parameters.set('action', 'create_client');

        $.ajax({
            url: window.location.pathname,
            type: 'POST',
            data: parameters,
            dataType: 'json',
            processData: false,
            contentType: false,
        }).done(function (data) {
            if (!data.hasOwnProperty('error')) {
                var option = new Option(data.text, data.id, true, true);
                $('select[name="cli"]').append(option).trigger('change');
                $('#modalClient').modal('hide');
                $('#clientModalForm')[0].reset();
                Swal.fire({
                    title: 'Cliente agregado',
                    text: data.text,
                    icon: 'success',
                    timer: 1400,
                    showConfirmButton: false
                });
                return false;
            }
            message_error(data.error);
        }).fail(function (jqXHR, textStatus, errorThrown) {
            message_error(textStatus + ': ' + errorThrown);
        });
    });

    $('#modalClient').on('shown.bs.modal', function () {
        $('#clientModalForm input[name="names"]').trigger('focus');
    });
});
