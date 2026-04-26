$(function () {
    var config = window.clientListConfig || {};

    $('#data').DataTable({
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            data: {
                'action': 'searchdata'
            },
            dataSrc: ""
        },
        columns: [
            {"data": "id"},
            {"data": "names"},
            {"data": "surnames"},
            {"data": "dni"},
            {"data": "date_birthday"},
            {"data": "gender.name"},
            {"data": "id"},
        ],
        columnDefs: [
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '';
                    if (config.canChange) {
                        buttons += '<a href="/erp/client/update/' + row.id + '/" class="btn btn-primary btn-xs btn-flat"><i class="fas fa-edit"></i> Editar</a> ';
                    }
                    if (config.canDelete) {
                        buttons += '<a href="/erp/client/delete/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i> Eliminar</a>';
                    }
                    if (!buttons) {
                        return '<span class="text-muted">Sin acciones</span>';
                    }
                    return buttons;
                }
            },
        ],
        initComplete: function (settings, json) {

        }
    });
});
