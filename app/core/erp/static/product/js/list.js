$(function () {
    var config = window.productListConfig || {};

    if ($.fn.DataTable.isDataTable('#data')) {
        try {
            $('#data').DataTable().clear().destroy();
        } catch (e) {
            // swallow any destroy errors
        }
    }

    var table = $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            data: function (d) {
                d.action = 'searchdata';
                d.search = $('#search').val().trim();
                d.stock_status = $('#stock_status').val();
            },
            dataSrc: ""
        },
        columns: [
            {"data": "id"},
            {"data": "name"},
            {
                data: null,
                render: function (data, type, row) {
                    return (row.category && row.category.name) || (row.cat && row.cat.name) || '';
                }
            },
            {"data": "image"},
            {"data": "pvp"},
            {"data": "id"},
        ],
        columnDefs: [
            {
                targets: [-3],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    return '<img src="'+data+'" class="img-fluid d-block mx-auto" style="width: 20px; height: 20px;">';
                }
            },
            {
                targets: [-2],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    return '$'+parseFloat(data).toFixed(2);
                }
            },
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '';
                    if (config.canChange) {
                        buttons += '<a href="/erp/product/update/' + row.id + '/" class="btn btn-primary btn-xs btn-flat"><i class="fas fa-edit"></i> Editar</a> ';
                    }
                    if (config.canDelete) {
                        buttons += '<a href="/erp/product/delete/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i> Eliminar</a>';
                    }
                    if (!buttons) {
                        return '<span class="text-muted">Sin acciones</span>';
                    }
                    return buttons;
                }
            },
        ],
        initComplete: function (settings, json) {
            $('#btnSearch').on('click', function () {
                table.ajax.reload();
            });
            $('#btnClear').on('click', function () {
                $('#search').val('');
                $('#stock_status').val('');
                table.ajax.reload();
            });
            $('#search').on('keyup', function (e) {
                if (e.which === 13) {
                    table.ajax.reload();
                }
            });
            $('#stock_status').on('change', function () {
                table.ajax.reload();
            });
        }
    });
});
