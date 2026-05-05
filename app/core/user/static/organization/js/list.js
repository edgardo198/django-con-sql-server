$(function () {
    var config = window.organizationListConfig || {};

    function getCSRFHeader() {
        if (typeof window.getCSRFToken === 'function') {
            return window.getCSRFToken();
        }
        return $('meta[name="csrf-token"]').attr('content') || '';
    }

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
            beforeSend: function (xhr) {
                xhr.setRequestHeader('X-CSRFToken', getCSRFHeader());
            },
            dataSrc: function (json) {
                if (Array.isArray(json)) {
                    return json;
                }
                if (json && Array.isArray(json.data)) {
                    return json.data;
                }
                if (json && json.error) {
                    message_error(json.error);
                }
                return [];
            },
            error: function (xhr, textStatus, errorThrown) {
                message_error('No se pudo cargar el listado de tiendas: ' + textStatus + ' ' + errorThrown);
            }
        },
        columns: [
            {"data": "id"},
            {"data": "name", "defaultContent": ""},
            {"data": "code", "defaultContent": ""},
            {"data": "phone", "defaultContent": ""},
            {"data": "email", "defaultContent": ""},
            {"data": "users_count", "defaultContent": 0},
            {"data": "is_active", "defaultContent": false},
            {"data": "id"},
        ],
        columnDefs: [
            {
                targets: [1],
                render: function (data, type, row) {
                    if (config.currentOrganizationId === row.id) {
                        return (data || '') + ' <span class="badge badge-info">Activa</span>';
                    }
                    return data || '';
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
