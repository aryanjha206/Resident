const CACHE_NAME = 'society-hub-v2';
const ASSETS = [
    '/',
    '/index.html',
    '/admin.html',
    '/guard.html',
    '/manifest.json',
    '/sw.js',
    '/icons/icon-192.svg',
    '/icons/icon-512.svg'
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (e) => {
    if (e.request.method !== 'GET') return;
    const url = new URL(e.request.url);

    if (e.request.url.includes('/api/')) {
        // Network first for API calls, fallback to cache
        e.respondWith(
            fetch(e.request).then(res => {
                const reqCopy = res.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(e.request, reqCopy));
                return res;
            }).catch(() => caches.match(e.request))
        );
    } else if (url.origin === self.location.origin) {
        e.respondWith(
            caches.match(e.request).then((cached) => {
                if (cached) return cached;
                return fetch(e.request).then((response) => {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(e.request, copy));
                    return response;
                });
            })
        );
    } else {
        e.respondWith(
            fetch(e.request).catch(() => caches.match(e.request))
        );
    }
});
