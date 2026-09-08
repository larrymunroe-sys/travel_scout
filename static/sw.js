// Travel Scout Progressive Web App Service Worker (Offline Cache)
const CACHE_NAME = "travel-scout-v4.2";
const PRECACHE_URLS = [
  "/static/styles.css",
  "/static/app.js",
  "/static/manifest.json",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
];

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(PRECACHE_URLS).catch((err) => {
        console.warn("Precache failed for some assets:", err);
      });
    })
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("Removing outdated service worker cache:", key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => {
      return caches.open(CACHE_NAME).then((cache) => {
        return Promise.all([
          cache.delete("/"),
          cache.delete("/index.html"),
          cache.delete("/auth/me")
        ]);
      });
    }).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // 1. ONLY handle http/https — skip chrome-extension://, data:, blob:, etc.
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    return;
  }

  // 2. Skip non-GET requests
  if (event.request.method !== "GET") {
    return;
  }

  // 3. NEVER intercept auth routes
  if (url.pathname.startsWith("/auth/")) {
    return;
  }

  // 4. Navigation requests: network-only, inline offline fallback
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(
          "<!DOCTYPE html><html><head><title>Travel Scout - Offline</title></head>" +
          "<body style='font-family:system-ui;text-align:center;padding:4rem;background:#0f172a;color:#e2e8f0;'>" +
          "<h1>\u{1F30D} Travel Scout</h1>" +
          "<p>You appear to be offline. Please check your internet connection and reload.</p>" +
          "<button onclick='location.reload()' style='margin-top:1rem;padding:0.75rem 1.5rem;font-size:1rem;" +
          "background:#38bdf8;color:#0f172a;border:none;border-radius:8px;cursor:pointer;font-weight:700;'>Retry</button>" +
          "</body></html>",
          { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } }
        );
      })
    );
    return;
  }

  // 5. API routes: network-first, cache fallback
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((c) => c.put(event.request, clone).catch(() => {}));
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then((cached) => {
            return cached || Response.json(
              { detail: "Offline — data not cached." },
              { status: 503 }
            );
          });
        })
    );
    return;
  }

  // 6. Static assets: network-first, cache fallback
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((c) => c.put(event.request, clone).catch(() => {}));
        }
        return networkResponse;
      })
      .catch(() => {
        return caches.match(event.request).then((cached) => {
          return cached || new Response("", { status: 503 });
        });
      })
  );
});
