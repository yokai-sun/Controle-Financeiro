// Service worker mínimo: só existe para o app poder ser instalado no celular (PWA).
// Não guarda nada em cache: o app sempre carrega a versão atual do servidor.
// Ao ativar, apaga caches de versões antigas que podiam mostrar telas desatualizadas.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});
