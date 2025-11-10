
// Service Worker for Dashboard PWA
const CACHE_NAME = 'dashboard-v2';
const urlsToCache = [
  '/',
  '/index.html',
  '/offline.html',
  '/projects.json',
  '/manifest.webmanifest',
  // Add other core assets here
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  // Network-first strategy for API requests, cache-first for assets
  if (event.request.url.includes('/projects.json') || event.request.url.includes('/release-port')) {
    // Network first for dynamic data
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Update cache with fresh response
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(() => {
          // If network fails, try cache
          if (event.request.url.includes('/projects.json')) {
            return caches.match('/projects.json')
              .then(response => {
                if (response) {
                  return response;
                }
                // If not in cache, return a default empty array
                return new Response(JSON.stringify([]), {
                  headers: { 'Content-Type': 'application/json' }
                });
              });
          } else {
            return caches.match(event.request)
              .then(response => response || caches.match('/offline.html'));
          }
        })
    );
  } else {
    // Cache-first for static assets
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          return response || fetch(event.request)
            .catch(() => caches.match('/offline.html'));
        })
    );
  }
});