const CACHE_NAME = 'society-hub-v1';
const ASSETS = [
    '/',
    '/index.html',
    '/admin.html',
    '/manifest.json',
    'https://cdn.tailwindcss.com',
    'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css'
];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(ASSETS).catch(err => {
                console.warn('Failed to cache completely, might be cross-origin restrictions:', err);
            });
        })
    );
});

self.addEventListener('fetch', (e) => {
    if (e.request.url.includes('/api/')) {
        // Network first for API calls, fallback to cache
        e.respondWith(
            fetch(e.request).then(res => {
                const reqCopy = res.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(e.request, reqCopy));
                return res;
            }).catch(() => caches.match(e.request))
        );
    } else {
        // Cache first for static assets
        e.respondWith(
            caches.match(e.request).then(res => {
                return res || fetch(e.request);
            })
        );
    }
});
