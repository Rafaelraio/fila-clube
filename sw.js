// cache simples: casca do app offline, dados sempre da rede quando houver, imagens guardadas depois do primeiro uso
var CACHE = 'fila-v2';
var CASCA = ['./', 'index.html', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', function (e) { e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(CASCA); }).then(function () { return self.skipWaiting(); })); });
self.addEventListener('activate', function (e) { e.waitUntil(caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); })); }).then(function () { return self.clients.claim(); })); });
self.addEventListener('fetch', function (e) {
  var url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.indexOf('/data/') >= 0) {
    e.respondWith(fetch(e.request).then(function (r) { var c = r.clone(); caches.open(CACHE).then(function (k) { k.put(e.request, c); }); return r; }).catch(function () { return caches.match(e.request); }));
    return;
  }
  e.respondWith(caches.match(e.request).then(function (hit) {
    return hit || fetch(e.request).then(function (r) { if (url.pathname.indexOf('/img/') >= 0 || CASCA.some(function (p) { return url.pathname.endsWith(p.replace('./', '')); })) { var c = r.clone(); caches.open(CACHE).then(function (k) { k.put(e.request, c); }); } return r; });
  }));
});

self.addEventListener('push', function (e) {
  var d = {};
  try { d = e.data ? e.data.json() : {}; } catch (x) { d = { title: 'Hora de postar', body: e.data ? e.data.text() : '' }; }
  var op = { body: d.body || '', icon: 'icon-192.png', badge: 'icon-192.png', tag: d.tag || 'fila', data: { url: d.url || './' }, vibrate: [200, 100, 200], renotify: true };
  if (d.image) op.image = d.image;
  e.waitUntil(self.registration.showNotification(d.title || 'Hora de postar', op));
});
self.addEventListener('notificationclick', function (e) {
  e.notification.close();
  var url = (e.notification.data && e.notification.data.url) || './';
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (ws) {
    for (var i = 0; i < ws.length; i++) { if ('focus' in ws[i]) { ws[i].navigate(url); return ws[i].focus(); } }
    return clients.openWindow(url);
  }));
});
