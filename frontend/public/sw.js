// QUARK PWA service worker — 앱 셸 정적 자산만 최소 캐싱.
// 채팅 SSE(/api), MQTT WS(/mqtt), 그 외 실시간 데이터는 절대 가로채지 않는다.

const CACHE_NAME = "quark-shell-v3";
const APP_SHELL = ["/", "/manifest.webmanifest", "/icons/icon-192-v2.png", "/icons/icon-512-v2.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (url.origin !== self.location.origin) return;
  if (request.method !== "GET") return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/mqtt") || url.pathname.startsWith("/ws")) return;

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      })
      .catch(() => caches.match(request).then((cached) => cached ?? Response.error()))
  );
});

self.addEventListener("push", (event) => {
  let payload = { title: "Quark", body: "" };
  try {
    if (event.data) payload = event.data.json();
  } catch {
    // non-JSON payload — fall back to defaults
  }
  event.waitUntil(
    self.registration.showNotification(payload.title || "Quark", {
      body: payload.body || "",
      icon: "/icons/icon-192-v2.png",
      badge: "/icons/icon-192-v2.png",
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow("/"));
});
