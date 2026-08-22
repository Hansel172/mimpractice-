const SHELL = 'earnings-shell-v1';
const FILES = ['./', 'index.html', 'styles.css', 'app.js', 'manifest.webmanifest'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== SHELL).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.pathname.endsWith('data.json')) {
    // Network-first for data so a refresh always tries live before cache.
    e.respondWith(fetch(e.request)
      .then(r => { const copy = r.clone();
        caches.open(SHELL).then(c => c.put('data.json', copy)); return r; })
      .catch(() => caches.match('data.json')));
    return;
  }
  // Cache-first for the shell so it opens instantly and works offline.
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request)));
});
