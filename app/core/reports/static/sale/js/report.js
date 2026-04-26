var date_range = null;
var reportConfig = window.reportConfig || {};
var date_now = moment().format('YYYY-MM-DD');
var default_start_date = reportConfig.defaultStartDate || moment().startOf('month').format('YYYY-MM-DD');
var default_end_date = reportConfig.defaultEndDate || date_now;
var current_period = reportConfig.defaultPeriod || 'month';

var periodLabels = {
    day: 'Hoy',
    week: 'Semana',
    month: 'Mes',
    custom: 'Rango manual'
};

function formatCurrency(value) {
    return 'L. ' + parseFloat(value || 0).toFixed(2);
}

function showReportError(message) {
    if (typeof message_error === 'function') {
        message_error(message);
        return;
    }
    $('#report-js-warning').removeClass('d-none').append('<div>' + message + '</div>');
}

function getBaseDate() {
    var baseDate = moment(default_end_date, 'YYYY-MM-DD');
    return baseDate.isValid() ? baseDate : moment();
}

function getPeriodRange(period) {
    var baseDate = getBaseDate();
    var startDate = moment(default_start_date, 'YYYY-MM-DD');
    var endDate = moment(default_end_date, 'YYYY-MM-DD');

    if (period === 'day') {
        startDate = baseDate.clone();
        endDate = baseDate.clone();
    } else if (period === 'week') {
        startDate = baseDate.clone().startOf('isoWeek');
        endDate = baseDate.clone();
    } else if (period === 'month') {
        startDate = baseDate.clone().startOf('month');
        endDate = baseDate.clone();
    } else if (period === 'custom' && date_range !== null) {
        startDate = date_range.startDate.clone();
        endDate = date_range.endDate.clone();
    }

    return {
        startDate: startDate,
        endDate: endDate,
        label: periodLabels[period] || periodLabels.month
    };
}

function setDateRangeInput(range) {
    var input = $('input[name="date_range"]');
    var picker = input.data('daterangepicker');
    var startText = range.startDate.format('YYYY-MM-DD');
    var endText = range.endDate.format('YYYY-MM-DD');

    if (picker) {
        picker.setStartDate(startText);
        picker.setEndDate(endText);
    }
    input.val(startText + ' - ' + endText);
}

function updateActivePeriodButtons() {
    $('.btnReportPeriod').removeClass('active');
    $('.btnReportPeriod[data-period="' + current_period + '"]').addClass('active');
}

function updateRangeLabel(range, response) {
    var label = (response && response.period_label) || range.label;
    var startDate = (response && response.start_date) || range.startDate.format('YYYY-MM-DD');
    var endDate = (response && response.end_date) || range.endDate.format('YYYY-MM-DD');
    $('#active-range-label').text(label + ': ' + startDate + ' al ' + endDate);
}

function updateSummary(summary) {
    summary = summary || {};
    $('#summary-total').text(formatCurrency(summary.total));
    $('#summary-subtotal').text(formatCurrency(summary.subtotal));
    $('#summary-tax').text(formatCurrency(summary.iva));
    $('#summary-profit').text(formatCurrency(summary.profit));
    $('#summary-sales-count').text(summary.sales_count || 0);
    $('#summary-average-ticket').text(formatCurrency(summary.average_ticket));
}

function setReportLoading(isLoading) {
    $('#btnRefreshReport, .btnReportPeriod').prop('disabled', isLoading);
    $('#btnRefreshReport').html(
        isLoading
            ? '<i class="fas fa-spinner fa-spin"></i> Cargando'
            : '<i class="fas fa-sync"></i> Actualizar'
    );
}

function buildReportParameters() {
    var range = getPeriodRange(current_period);
    var startDate = range.startDate.format('YYYY-MM-DD');
    var endDate = range.endDate.format('YYYY-MM-DD');

    setDateRangeInput(range);
    updateActivePeriodButtons();
    updateRangeLabel(range);

    return {
        range: range,
        parameters: {
            action: 'search_report',
            period: current_period,
            start_date: startDate,
            end_date: endDate
        }
    };
}

function renderPlainRows(rows) {
    var tbody = $('#data tbody');
    tbody.empty();

    if (!rows.length) {
        tbody.append('<tr><td colspan="10" class="text-center text-muted">No hay ventas para el periodo seleccionado</td></tr>');
        return;
    }

    $.each(rows, function (index, row) {
        tbody.append(
            '<tr>' +
            '<td>' + row.id + '</td>' +
            '<td>' + row.organization + '</td>' +
            '<td>' + row.client + '</td>' +
            '<td>' + row.date_joined + '</td>' +
            '<td class="text-center">' + row.items_count + '</td>' +
            '<td class="text-center">' + formatCurrency(row.subtotal) + '</td>' +
            '<td class="text-center">' + formatCurrency(row.tax_total || row.iva) + '</td>' +
            '<td class="text-center">' + formatCurrency(row.total) + '</td>' +
            '<td class="text-center">' + formatCurrency(row.profit) + '</td>' +
            '<td class="text-center">' + row.status + '</td>' +
            '</tr>'
        );
    });
}

function generate_report_fallback(reportRequest) {
    setReportLoading(true);
    $('#report-js-warning').removeClass('d-none');

    $.ajax({
        url: window.location.pathname,
        type: 'POST',
        data: reportRequest.parameters,
        dataType: 'json'
    }).done(function (json) {
        if (json.error) {
            showReportError(json.error);
            updateSummary({});
            renderPlainRows([]);
            return;
        }
        updateSummary(json.summary || {});
        updateRangeLabel(reportRequest.range, json);
        renderPlainRows(json.rows || []);
    }).fail(function (jqXHR, textStatus, errorThrown) {
        showReportError(textStatus + ': ' + errorThrown);
        updateSummary({});
        renderPlainRows([]);
    }).always(function () {
        setReportLoading(false);
    });
}

function getExportButtons() {
    if (!($.fn.dataTable && $.fn.dataTable.Buttons)) {
        return [];
    }

    return [
        {
            extend: 'excelHtml5',
            text: '<i class="fas fa-file-excel"></i> Descargar Excel',
            titleAttr: 'Excel',
            className: 'btn btn-success btn-flat',
            title: function () {
                return 'Reporte de ventas - ' + $('#active-range-label').text();
            }
        },
        {
            extend: 'pdfHtml5',
            text: '<i class="fas fa-file-pdf"></i> Descargar Pdf',
            titleAttr: 'PDF',
            className: 'btn btn-danger btn-flat',
            title: function () {
                return 'Reporte de ventas - ' + $('#active-range-label').text();
            },
            download: 'open',
            orientation: 'landscape',
            pageSize: 'LEGAL',
            customize: function (doc) {
                doc.styles = {
                    header: {
                        fontSize: 18,
                        bold: true,
                        alignment: 'center'
                    },
                    subheader: {
                        fontSize: 13,
                        bold: true
                    },
                    small: {
                        fontSize: 8
                    },
                    tableHeader: {
                        bold: true,
                        fontSize: 10,
                        color: 'white',
                        fillColor: '#134e4a',
                        alignment: 'center'
                    }
                };
                if (doc.content[1] && doc.content[1].table) {
                    doc.content[1].table.widths = ['5%', '13%', '16%', '10%', '7%', '10%', '8%', '10%', '10%', '11%'];
                    doc.content[1].margin = [0, 28, 0, 0];
                }
                doc.footer = function (page, pages) {
                    return {
                        columns: [
                            {
                                alignment: 'left',
                                text: ['Fecha de creacion: ', {text: date_now}]
                            },
                            {
                                alignment: 'right',
                                text: ['pagina ', {text: page.toString()}, ' de ', {text: pages.toString()}]
                            }
                        ],
                        margin: 20
                    };
                };
            }
        }
    ];
}

function generate_report() {
    var reportRequest = buildReportParameters();

    if (!$.fn.DataTable) {
        generate_report_fallback(reportRequest);
        return;
    }

    var exportButtons = getExportButtons();
    var tableOptions = {
        responsive: true,
        autoWidth: false,
        destroy: true,
        deferRender: true,
        processing: true,
        ajax: {
            url: window.location.pathname,
            type: 'POST',
            data: reportRequest.parameters,
            beforeSend: function () {
                setReportLoading(true);
            },
            dataSrc: function (json) {
                if (json.error) {
                    showReportError(json.error);
                    updateSummary({});
                    return [];
                }
                updateSummary(json.summary || {});
                updateRangeLabel(reportRequest.range, json);
                return json.rows || [];
            },
            error: function (jqXHR, textStatus, errorThrown) {
                showReportError(textStatus + ': ' + errorThrown);
                updateSummary({});
            },
            complete: function () {
                setReportLoading(false);
            }
        },
        order: false,
        paging: false,
        ordering: false,
        info: false,
        searching: false,
        language: {
            emptyTable: 'No hay ventas para el periodo seleccionado',
            loadingRecords: 'Cargando reporte...',
            processing: 'Procesando...'
        },
        columns: [
            {"data": "id"},
            {"data": "organization"},
            {"data": "client"},
            {"data": "date_joined"},
            {"data": "items_count"},
            {"data": "subtotal"},
            {
                data: null,
                render: function (data, type, row) {
                    return (row.tax_total !== undefined && row.tax_total !== null) ? row.tax_total : (row.iva || 0);
                }
            },
            {"data": "total"},
            {"data": "profit"},
            {"data": "status"}
        ],
        columnDefs: [
            {
                targets: [5, 6, 7, 8],
                class: 'text-center',
                orderable: false,
                render: function (data) {
                    return formatCurrency(data);
                }
            },
            {
                targets: [4, 9],
                class: 'text-center',
                orderable: false
            }
        ]
    };

    if (exportButtons.length) {
        tableOptions.dom = 'Bfrtip';
        tableOptions.buttons = exportButtons;
    }

    $('#data').DataTable(tableOptions);
}

$(function () {
    var initialRange = getPeriodRange(current_period);

    $('input[name="date_range"]').daterangepicker({
        startDate: initialRange.startDate,
        endDate: initialRange.endDate,
        locale: {
            format: 'YYYY-MM-DD',
            applyLabel: '<i class="fas fa-chart-pie"></i> Aplicar',
            cancelLabel: '<i class="fas fa-times"></i> Cancelar'
        }
    }).on('apply.daterangepicker', function (ev, picker) {
        current_period = 'custom';
        date_range = picker;
        generate_report();
    }).on('cancel.daterangepicker', function () {
        current_period = reportConfig.defaultPeriod || 'month';
        date_range = null;
        generate_report();
    });

    $('.btnReportPeriod').on('click', function () {
        current_period = $(this).data('period');
        date_range = null;
        generate_report();
    });

    $('#btnRefreshReport').on('click', function () {
        generate_report();
    });

    generate_report();
});
