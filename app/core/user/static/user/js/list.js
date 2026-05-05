$(function () {
    var config = window.userListConfig || {};

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
                message_error('No se pudo cargar el listado de usuarios: ' + textStatus + ' ' + errorThrown);
            }
        },
        columns: [
            {"data": "id"},
            {"data": "full_name", "defaultContent": ""},
            {"data": "username", "defaultContent": ""},
            {"data": "date_joined", "defaultContent": ""},
            {"data": "image", "defaultContent": ""},
            {"data": "current_organization", "defaultContent": null},
            {"data": "groups", "defaultContent": []},
            {"data": "id"},
        ],
        columnDefs: [
            {
                targets: [-4],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    return '<img src="' + (row.image || '/static/img/imagen.png') + '" class="img-fluid mx-auto d-block" style="width: 20px; height: 20px;">';
                }
            },
            {
                targets: [-3],
                class: 'text-center',
                orderable: false,
                render: function (data) {
                    return data ? '<span class="badge badge-info">' + data.name + '</span>' : '<span class="badge badge-secondary">Sin tienda</span>';
                }
            },
            {
                targets: [-2],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var html = '';
                    $.each(row.roles || [], function (key, value) {
                        html += '<span class="badge badge-success">' + value + '</span> ';
                    });
                    if (!html) {
                        return '<span class="badge badge-secondary">Sin rol</span>';
                    }
                    return html;
                }
            },
            {
                targets: [-1],
                class: 'text-center',
                orderable: false,
                render: function (data, type, row) {
                    var buttons = '';
                    if (config.canChange) {
                        buttons += '<a href="/user/update/' + row.id + '/" class="btn btn-warning btn-xs btn-flat"><i class="fas fa-edit"></i></a> ';
                    }
                    if (config.canDelete && row.id !== config.currentUserId) {
                        buttons += '<a href="/user/delete/' + row.id + '/" type="button" class="btn btn-danger btn-xs btn-flat"><i class="fas fa-trash-alt"></i></a>';
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
