/* Работа без интернета: кабинет и его файлы сохраняются в браузере.
   Пока интернет есть, всегда берётся свежая версия с сайта, сохранённая — только когда сети нет.
   Записи клиентов здесь не хранятся: они лежат в хранилище браузера, как и раньше. */
const CACHE='tochka-opory-files';
const FILES=['./','index.html','manifest.webmanifest','favicon.png','icon-192.png?v=19','icon-512.png?v=19','icon-maskable.png?v=19',
  'fonts/spectral-cyrillic-400-normal.woff2','fonts/spectral-latin-400-normal.woff2',
  'fonts/spectral-cyrillic-600-normal.woff2','fonts/spectral-latin-600-normal.woff2',
  'fonts/spectral-cyrillic-700-normal.woff2','fonts/spectral-latin-700-normal.woff2',
  'fonts/golos-text-cyrillic-400-normal.woff2','fonts/golos-text-latin-400-normal.woff2',
  'fonts/golos-text-cyrillic-500-normal.woff2','fonts/golos-text-latin-500-normal.woff2',
  'fonts/golos-text-cyrillic-600-normal.woff2','fonts/golos-text-latin-600-normal.woff2',
  'fonts/golos-text-cyrillic-700-normal.woff2','fonts/golos-text-latin-700-normal.woff2',
  'fonts/ibm-plex-mono-cyrillic-400-normal.woff2','fonts/ibm-plex-mono-latin-400-normal.woff2',
  'fonts/ibm-plex-mono-cyrillic-500-normal.woff2','fonts/ibm-plex-mono-latin-500-normal.woff2',
  'fonts/ibm-plex-mono-cyrillic-600-normal.woff2','fonts/ibm-plex-mono-latin-600-normal.woff2'];
self.addEventListener('install',e=>{
  e.waitUntil(caches.open(CACHE).then(c=>Promise.all(FILES.map(f=>c.add(new Request(f,{cache:'reload'})).catch(()=>{}))))
    .then(()=>self.skipWaiting()));
});
self.addEventListener('activate',e=>{
  e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
  const r=e.request;
  if(r.method!=='GET'||new URL(r.url).origin!==location.origin)return;
  e.respondWith(fetch(r).then(res=>{
    if(res&&res.ok){const copy=res.clone();caches.open(CACHE).then(c=>c.put(r,copy)).catch(()=>{})}
    return res;
  }).catch(()=>caches.match(r,{ignoreSearch:r.mode==='navigate'}).then(m=>m||(r.mode==='navigate'?caches.match('index.html'):undefined))
    .then(m=>m||Response.error())));
});
