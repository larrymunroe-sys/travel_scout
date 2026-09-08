// Travel Scout Progressive Web App Service Worker (Offline Cache)
const CACHE_NAME = "travel-scout-v4.1";
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
      // Evict any dynamic or auth responses that may have been cached previously
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

  // 1. Skip non-GET requests (POST, PUT, DELETE go straight to network)
  if (event.request.method !== "GET") {
    return;
  }

  // 2. NEVER intercept or cache auth routes (always direct live network)
  if (url.pathname.startsWith("/auth/")) {
    return;
  }

  // 3. Navigation requests (HTML pages): Network-only, NO cache fallback
  //    Dynamic HTML depends on session cookies; serving stale cached HTML
  //    would show logged-out UI to a logged-in user and vice versa.
  if (event.request.mode === "navigate" || url.pathname === "/" || url.pathname === "/index.html") {
    event.respondWith(
      fetch(event.request).catch(() => {
        return new Response(
          "<!DOCTYPE html><html><head><title>Travel Scout - Offline</title></head>" +
          "<body style='font-family:system-ui;text-align:center;padding:4rem;background:#0f172a;color:#e2e8f0;'>" +
          "<h1>🌍 Travel Scout</h1>" +
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

  // 4. API routes: Network-first, with offline cache fallback
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then((cached) => {
            return cached || new Response(
              JSON.stringify({ detail: "You are offline and this data is not cached." }),
              { status: 503, headers: { "Content-Type": "application/json" } }
            );
          });
        })
    );
    return;
  }

  // 5. Static assets (CSS, JS, images, fonts): Network-first with cache fallback
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
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
