$(function () {
    var config = window.organizationListConfig || {};

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
            {"data": "name"},
            {"data": "code"},
            {"data": "phone"},
            {"data": "email"},
            {"data": "users_count"},
            {"data": "is_active"},
            {"data": "id"},
        ],
        columnDefs: [
            {
                targets: [1],
                render: function (data, type, row) {
                    if (config.currentOrganizationId === row.id) {
                        return data + ' <span class="badge badge-info">Activa</span>';
                    }
                    return data;
                }
            },
            {
                targets: [-2],
                class: 'text-center',
                orderable: false,
                render: function (data) {
                    return data ? '<span class="badge badge-success">Activa</span>' : '<span class="badge badge-danger">Inactiva</span>';
                }
            },
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '';
                    if (row.is_active) {
                        buttons += '<a href="/user/organization/switch/' + row.id + '/" class="btn btn-success btn-xs btn-flat"><i class="fas fa-store"></i> Entrar</a> ';
                    }
                    if (config.canChange) {
                        buttons += '<a href="/user/organization/update/' + row.id + '/" class="btn btn-primary btn-xs btn-flat"><i class="fas fa-edit"></i> Editar</a> ';
                    }
                    if (config.canDelete) {
                        buttons += '<a href="/user/organization/delete/' + row.id + '/" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i> Eliminar</a>';
                    }
                    if (!buttons) {
                        return '<span class="text-muted">Sin acciones</span>';
                    }
                    return buttons;
                }
            },
        ],
    });
});
