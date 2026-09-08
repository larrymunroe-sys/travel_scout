// Travel Scout Progressive Web App Service Worker (Offline Cache)
const CACHE_NAME = "travel-scout-v4.3";
const PRECACHE_URLS = [
  "/static/styles.css?v=4.3",
  "/static/app.js?v=4.3",
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

  // 2. Skip non-GET requests (POST, PUT, DELETE always direct to network)
  if (event.request.method !== "GET") {
    return;
  }

  // 3. NEVER intercept auth routes (session, google oauth, dev-login)
  if (url.pathname.startsWith("/auth/")) {
    return;
  }

  // 4. NEVER intercept navigation requests (HTML pages)
  //    Bypassing SW ensures native browser navigation, cookie handling,
  //    OAuth redirects, and prevents synthetic 503 errors during server spin-up.
  if (event.request.mode === "navigate") {
    return;
  }

  // 5. API routes: network-first, with offline cache fallback if available
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
            if (cached) return cached;
            return Response.json(
              { detail: "Offline — data not cached." },
              { status: 503 }
            );
          });
        })
    );
    return;
  }

  // 6. Static assets (CSS, JS, images, fonts): Network-first
  //    If network fails, return cached version. NEVER return a synthetic 503!
  event.respondWith(
    fetch(event.request)
      .then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((c) => c.put(event.request, clone).catch(() => {}));
        }
        return networkResponse;
      })
      .catch(async () => {
        const cached = await caches.match(event.request);
        if (cached) return cached;
        // If not in cache, fallback to unversioned url or re-attempt
        const fallback = await caches.match(url.pathname);
        if (fallback) return fallback;
        // Let the browser handle the network error naturally, NEVER return synthetic 503
        throw new Error("Offline asset not cached: " + url.pathname);
      })
  );
});
