(function () {
    function ensureIndicator() {
        if (document.getElementById('dashboard-offline-indicator')) return;
        var div = document.createElement('div');
        div.id = 'dashboard-offline-indicator';
        div.className = 'dashboard-offline-indicator';
        div.innerHTML = '<div class="offline-indicator-content"><i class="fas fa-wifi"></i><span id="offline-indicator-text">Conectando...</span></div>';
        document.body.appendChild(div);
    }

    function updateIndicator(online) {
        ensureIndicator();
        var el = document.getElementById('dashboard-offline-indicator');
        var txt = document.getElementById('offline-indicator-text');
        if (online) {
            el.classList.remove('show');
            if (txt) txt.textContent = 'Conectado';
        } else {
            el.classList.add('show');
            if (txt) txt.textContent = 'Sin conexión - trabajando en modo offline';
        }
    }

    window.addEventListener('online', function () { updateIndicator(true); });
    window.addEventListener('offline', function () { updateIndicator(false); });

    // initial state
    updateIndicator(navigator.onLine);
})();
