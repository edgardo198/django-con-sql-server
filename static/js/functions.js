function message_error(obj) {
    var html = '';
    if (typeof (obj) === 'object') {
        html = '<ul style="text-align: left;">';
        $.each(obj, function (key, value) {
            html += '<li>' + key + ': ' + value + '</li>';
        });
        html += '</ul>';
    } else {
        html = '<p>' + obj + '</p>';
    }
    Swal.fire({
        title: 'Error!',
        html: html,
        icon: 'error'
    });
}

function submit_with_ajax(url, title, content, parameters, callback, options) {
    options = options || {};
    $.confirm({
        theme: 'material',
        title: title,
        icon: 'fa fa-info',
        content: content,
        columnClass: 'small',
        typeAnimated: true,
        cancelButtonClass: 'btn-primary',
        draggable: true,
        dragWindowBorder: false,
        buttons: {
            info: {
                text: "Si",
                btnClass: 'btn-primary',
                action: function () {
                    $.ajax({
                        url: url, //window.location.pathname
                        type: 'POST',
                        data: parameters,
                        dataType: 'json',
                        processData: false,
                        contentType: false,
                        beforeSend: function () {
                            if (typeof options.beforeSend === 'function') {
                                options.beforeSend();
                            }
                        },
                    }).done(function (data) {
                        if (!data.hasOwnProperty('error')) {
                            if (typeof callback === 'function') {
                                callback(data);
                            }
                            return false;
                        }
                        if (typeof options.onError === 'function') {
                            options.onError(data.error, data);
                        }
                        message_error(data.error);
                    }).fail(function (jqXHR, textStatus, errorThrown) {
                        if (typeof options.onError === 'function') {
                            options.onError(textStatus + ': ' + errorThrown, jqXHR);
                        }
                        message_error(textStatus + ': ' + errorThrown);
                    }).always(function (data) {
                        if (typeof options.complete === 'function') {
                            options.complete(data);
                        }
                    });
                }
            },
            danger: {
                text: "No",
                btnClass: 'btn-red',
                action: function () {

                }
            },
        }
    })
}

function alert_action(title, content, callback) {
    $.confirm({
        theme: 'material',
        title: title,
        icon: 'fa fa-info',
        content: content,
        columnClass: 'small',
        typeAnimated: true,
        cancelButtonClass: 'btn-primary',
        draggable: true,
        dragWindowBorder: false,
        buttons: {
            info: {
                text: "Si",
                btnClass: 'btn-primary',
                action: function () {
                    callback();
                }
            },
            danger: {
                text: "No",
                btnClass: 'btn-red',
                action: function () {
                      
                }
            },
        }
    })
}

function init_form_assistance() {
    var startedForms = [];

    function getFieldLabel($field) {
        var id = $field.attr('id');
        var $label = id ? $('label[for="' + id + '"]').first() : $();
        if ($label.length) {
            return $.trim($label.text().replace(':', ''));
        }
        return $field.attr('placeholder') || $field.attr('name') || 'este campo';
    }

    function getEmptyRequiredFields($form) {
        var fields = [];
        $form.find('input, select, textarea').each(function () {
            var $field = $(this);
            var type = ($field.attr('type') || '').toLowerCase();
            if (!$field.prop('required') || $field.prop('disabled') || type === 'hidden' || type === 'submit' || type === 'button') {
                return;
            }
            if (!$.trim($field.val() || '')) {
                fields.push(getFieldLabel($field));
            }
        });
        return fields;
    }

    function ensureAssistant($form) {
        var $assistant = $form.find('.form-assistant-hint').first();
        if ($assistant.length) {
            return $assistant;
        }

        $assistant = $(
            '<div class="form-assistant-hint d-none" role="status" aria-live="polite">' +
                '<div class="form-assistant-icon"><i class="fas fa-lightbulb"></i></div>' +
                '<div class="form-assistant-body">' +
                    '<strong>Te puedo ayudar a terminar esta forma.</strong>' +
                    '<p class="mb-0 form-assistant-message"></p>' +
                '</div>' +
                '<button type="button" class="form-assistant-close" aria-label="Cerrar sugerencia">&times;</button>' +
            '</div>'
        );

        var $target = $form.find('.modal-body').first();
        if (!$target.length) {
            $target = $form.find('.card-body').first();
        }
        if ($target.length) {
            $target.prepend($assistant);
        } else {
            $form.prepend($assistant);
        }
        return $assistant;
    }

    function buildSuggestion($form) {
        var emptyRequiredFields = getEmptyRequiredFields($form);
        if (emptyRequiredFields.length) {
            return 'Revisa los campos obligatorios pendientes: ' + emptyRequiredFields.slice(0, 3).join(', ') + '.';
        }
        return 'Si ya revisaste los datos, puedes guardar. Usa Cancelar para salir sin cambios.';
    }

    function showAssistant($form) {
        if (!$form.length || $form.data('assistant-dismissed') || !$form.is(':visible')) {
            return;
        }
        var $assistant = ensureAssistant($form);
        $assistant.find('.form-assistant-message').text(buildSuggestion($form));
        $assistant.removeClass('d-none');
    }

    function scheduleAssistant($form) {
        clearTimeout($form.data('assistant-idle-timer'));
        clearTimeout($form.data('assistant-long-timer'));

        $form.data('assistant-idle-timer', setTimeout(function () {
            showAssistant($form);
        }, 30000));

        $form.data('assistant-long-timer', setTimeout(function () {
            showAssistant($form);
        }, 90000));
    }

    $('form').each(function () {
        var $form = $(this);
        var method = ($form.attr('method') || 'get').toLowerCase();
        if (method === 'get' || $form.data('assistant-ready')) {
            return;
        }
        $form.data('assistant-ready', true);
        startedForms.push($form);
        scheduleAssistant($form);
    });

    $(document).on('input change focus', 'form input, form select, form textarea', function () {
        var $form = $(this).closest('form');
        if ($form.data('assistant-ready')) {
            scheduleAssistant($form);
        }
    });

    $(document).on('click', '.form-assistant-close', function () {
        var $assistant = $(this).closest('.form-assistant-hint');
        $assistant.addClass('d-none');
        $assistant.closest('form').data('assistant-dismissed', true);
    });

    $(document).on('submit', 'form', function () {
        clearTimeout($(this).data('assistant-idle-timer'));
        clearTimeout($(this).data('assistant-long-timer'));
    });
}

$(function () {
    init_form_assistance();
});
