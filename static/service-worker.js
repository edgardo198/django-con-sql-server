const CACHE_NAME = 'dashboard-cache-v1';
const STATIC_ASSETS = [
    '/static/dashboard/js/dashboard.js',
    '/static/dashboard/js/offline-storage.js',
    '/static/css/mystyle.css',
    '/static/js/functions.js',
    '/static/lib/highcharts-8.1.2/highcharts.js',
    '/static/lib/highcharts-8.1.2/modules/exporting.js',
    '/static/lib/highcharts-8.1.2/modules/export-data.js',
    '/static/lib/highcharts-8.1.2/modules/accessibility.js',
    '/static/lib/adminlte/css/adminlte.min.css',
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(STATIC_ASSETS).catch(() => Promise.resolve()))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => Promise.all(
            cacheNames.map((cacheName) => {
                if (cacheName !== CACHE_NAME) {
                    return caches.delete(cacheName);
                }
                return Promise.resolve();
            })
        )).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    if (event.request.method !== 'GET') {
        return;
    }

    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirstStrategy(event.request));
        return;
    }

    if (isApiRequest(url) || url.pathname === '/') {
        event.respondWith(networkFirstStrategy(event.request));
        return;
    }

    event.respondWith(networkFirstStrategy(event.request));
});

function cacheFirstStrategy(request) {
    return caches.match(request).then((response) => {
        if (response) {
            return response;
        }

        return fetch(request).then((networkResponse) => {
            if (!networkResponse || networkResponse.status !== 200 || networkResponse.type === 'error') {
                return networkResponse;
            }

            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
                cache.put(request, responseToCache);
            });
            return networkResponse;
        });
    });
}

function networkFirstStrategy(request) {
    return fetch(request)
        .then((response) => {
            if (!response || response.status !== 200) {
                return response;
            }

            if (isApiRequest(request.url)) {
                const responseToCache = response.clone();
                caches.open(CACHE_NAME).then((cache) => {
                    cache.put(request, responseToCache);
                });
            }

            return response;
        })
        .catch(() => caches.match(request).then((response) => {
            if (response) {
                return response;
            }
            return createOfflineResponse(request);
        }));
}

function createOfflineResponse(request) {
    if (isApiRequest(request.url)) {
        return new Response(
            JSON.stringify({
                error: 'Sin conexion a Internet. Los datos mostrados pueden no ser actuales.',
                offline: true,
            }),
            {
                status: 200,
                statusText: 'OK (Offline)',
                headers: { 'Content-Type': 'application/json' },
            }
        );
    }

    return new Response(
        '<html><body><h1>Offline</h1><p>Sin conexion a Internet</p></body></html>',
        {
            status: 200,
            statusText: 'OK (Offline)',
            headers: { 'Content-Type': 'text/html' },
        }
    );
}

function isStaticAsset(pathname) {
    return /\.(js|css|jpg|jpeg|png|gif|svg|woff|woff2|ttf|eot|ico)$/.test(pathname) ||
        pathname.indexOf('/static/') !== -1;
}

function isApiRequest(url) {
    return url.indexOf('/ajax') !== -1 || url.indexOf('/api') !== -1 || url.indexOf('action=') !== -1;
}
