/* Dashboard interactivity: populate filters, render KPIs and charts using Highcharts
   Relies on `window.dashboardBootstrap` provided by template with keys:
   available_years, initial_year, initial_month, initial_overview
*/
(function () {
    var bootstrap = window.dashboardBootstrap || {};
    var overview = bootstrap.initial_overview || {};

    function $(s) { return document.querySelector(s); }

    function formatCurrency(v) {
        return 'L ' + parseFloat(v || 0).toFixed(2);
    }

    function populateFilters() {
        var years = bootstrap.available_years || [];
        var yearSelect = document.getElementById('dashboard-year');
        var monthSelect = document.getElementById('dashboard-month');
        if (!yearSelect) return;
        yearSelect.innerHTML = '';
        years.forEach(function (y) {
            var opt = document.createElement('option');
            opt.value = y; opt.textContent = y;
            yearSelect.appendChild(opt);
        });
        yearSelect.value = bootstrap.initial_year || (new Date()).getFullYear();
        monthSelect.value = bootstrap.initial_month || (new Date()).getMonth() + 1;
    }

    function renderKPIs(data) {
        if (!data || !data.summary) return;
        var s = data.summary;
        var setText = function (id, text) { var el = document.getElementById(id); if (el) el.textContent = text; };
        setText('kpi-revenue-year', formatCurrency(s.revenue_year));
        setText('kpi-revenue-month', formatCurrency(s.revenue_month));
        setText('kpi-profit-month', formatCurrency(s.profit_month));
        setText('kpi-average-ticket', formatCurrency(s.average_ticket));
        setText('kpi-sales-count', s.sales_count_year);
        setText('kpi-sales-count-month', 'Ventas del mes: ' + s.sales_count_month);
        setText('kpi-low-stock-count', s.low_stock_count);
        setText('kpi-stock-units', 'Existencias totales: ' + s.total_stock_units + ' | Productos: ' + s.total_products);
        setText('kpi-top-product', s.top_product.name || 'Sin ventas');
        setText('kpi-top-client', s.top_client.name || 'Sin ventas');
        setText('kpi-best-month', (s.best_month && s.best_month.name) ? s.best_month.name : 'Sin datos');
        setText('insight-month', data.filters.selected_month_name + ' ' + data.filters.selected_year);
        setText('insight-best-month', (s.best_month && s.best_month.name) ? s.best_month.name : 'Sin datos');
        setText('insight-best-month-value', formatCurrency((s.best_month && s.best_month.value) || 0));
        setText('insight-top-product', s.top_product.name || 'Sin ventas');
        setText('insight-top-product-value', (s.top_product.quantity || 0) + ' unidades');
        setText('insight-top-client', s.top_client.name || 'Sin ventas');
        setText('insight-top-client-value', formatCurrency(s.top_client.value || 0));
        setText('kpi-inventory-movements', 'Movimientos del mes: ' + (s.inventory_movements_month || 0));
    }

    function renderInventory(data) {
        var list = document.getElementById('inventory-low-stock');
        if (!list) return;
        list.innerHTML = '';
        var items = (data.inventory && data.inventory.low_stock_products) || [];
        if (!items.length) {
            list.innerHTML = '<div class="dashboard-empty-state">No hay alertas de inventario por ahora.</div>';
            return;
        }
        items.forEach(function (it) {
            var div = document.createElement('div');
            div.className = 'inventory-item';
            div.innerHTML = '<div><strong>' + it.name + '</strong><small>' + (it.category || '') + '</small></div>' +
                '<div><span class="inventory-badge">' + it.stock + '</span><small>Min: ' + it.min_stock + '</small></div>';
            list.appendChild(div);
        });
    }

    function renderRecentMovements(data) {
        var list = document.getElementById('inventory-recent-movements');
        if (!list) return;
        list.innerHTML = '';
        var items = (data.inventory && data.inventory.recent_movements) || [];
        if (!items.length) {
            list.innerHTML = '<div class="dashboard-empty-state">Todavia no hay movimientos registrados.</div>';
            return;
        }
        items.forEach(function (it) {
            var div = document.createElement('div');
            div.className = 'inventory-item';
            div.innerHTML = '<div><strong>' + it.product + '</strong><small>' + it.type + ' • ' + it.reference + '</small></div>' +
                '<div><span class="inventory-badge">' + it.quantity + '</span><small>' + it.date_joined + '</small></div>';
            list.appendChild(div);
        });
    }

    function renderChartSalesYearly(data) {
        if (!window.Highcharts) return;
        var cfg = data.charts && data.charts.sales_yearly;
        if (!cfg) return;
        Highcharts.chart('chart-sales-yearly', {
            chart: { type: 'column' },
            title: { text: 'Comparativo anual' },
            xAxis: { categories: cfg.categories },
            yAxis: { title: { text: 'Ventas' } },
            series: cfg.series
        });
    }

    function renderChartSalesDaily(data) {
        if (!window.Highcharts) return;
        var cfg = data.charts && data.charts.sales_daily;
        if (!cfg) return;
        Highcharts.chart('chart-sales-daily', {
            chart: { type: 'line' },
            title: { text: 'Ventas diarias' },
            xAxis: { categories: cfg.categories },
            yAxis: { title: { text: 'Ventas' } },
            series: cfg.series
        });
    }

    function renderTopProducts(data) {
        if (!window.Highcharts) return;
        var cfg = data.charts && data.charts.top_products;
        if (!cfg) return;
        Highcharts.chart('chart-top-products', {
            chart: { type: 'pie' },
            title: { text: 'Participación por producto' },
            series: [{ name: 'Valor', colorByPoint: true, data: cfg }]
        });
    }

    function renderTopClients(data) {
        if (!window.Highcharts) return;
        var cfg = data.charts && data.charts.top_clients;
        if (!cfg) return;
        Highcharts.chart('chart-top-clients', {
            chart: { type: 'column' },
            title: { text: 'Clientes con mayor facturación' },
            xAxis: { categories: cfg.categories },
            yAxis: { title: { text: 'Facturación' } },
            series: cfg.series
        });
    }

    function refreshDashboard() {
        var year = document.getElementById('dashboard-year').value;
        var month = document.getElementById('dashboard-month').value;
        var params = new FormData();
        params.append('action', 'get_dashboard_overview');
        params.append('year', year);
        params.append('month', month);

        fetch(window.location.pathname, { method: 'POST', body: params })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && !data.error) {
                    renderKPIs(data);
                    renderInventory(data);
                    renderRecentMovements(data);
                    renderChartSalesYearly(data);
                    renderChartSalesDaily(data);
                    renderTopProducts(data);
                    renderTopClients(data);
                } else {
                    console.error('Dashboard error', data.error);
                }
            }).catch(function (err) { console.error(err); });
    }

    function init() {
        populateFilters();
        renderKPIs(overview);
        renderInventory(overview);
        renderRecentMovements(overview);
        renderChartSalesYearly(overview);
        renderChartSalesDaily(overview);
        renderTopProducts(overview);
        renderTopClients(overview);

        var btn = document.getElementById('dashboard-refresh');
        if (btn) btn.addEventListener('click', refreshDashboard);
        var exportBtn = document.getElementById('dashboard-export-csv');
        if (exportBtn) exportBtn.addEventListener('click', function () {
            var year = document.getElementById('dashboard-year').value;
            var month = document.getElementById('dashboard-month').value;
            var params = new FormData();
            params.append('action', 'export_sales_csv');
            params.append('year', year);
            params.append('month', month);

            fetch(window.location.pathname, { method: 'POST', body: params })
                .then(function (r) { return r.blob(); })
                .then(function (blob) {
                    var url = window.URL.createObjectURL(blob);
                    var a = document.createElement('a');
                    a.href = url;
                    a.download = 'ventas_' + year + '_' + (('0' + month).slice(-2)) + '.csv';
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                }).catch(function (err) { console.error('Export error', err); });
        });
    }

    document.addEventListener('DOMContentLoaded', init);
})();
