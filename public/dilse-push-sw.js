self.addEventListener("push", (event) => {
  event.waitUntil((async () => {
    let payload = {};
    try {
      payload = event.data ? event.data.json() : {};
    } catch (_) {
      payload = {};
    }

    const openWindows = await self.clients.matchAll({
      type: "window",
      includeUncontrolled: true,
    });
    if (openWindows.some((client) => client.visibilityState === "visible")) {
      return;
    }

    await self.registration.showNotification("DilSe", {
      body: "A DilSe response is waiting for you.",
      tag: `dilse-response-${payload.message_id || "new"}`,
      renotify: true,
      data: {
        url: payload.url || "/",
      },
    });
  })());
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil((async () => {
    const targetUrl = new URL(
      event.notification.data?.url || "/",
      self.location.origin,
    ).href;
    const openWindows = await self.clients.matchAll({
      type: "window",
      includeUncontrolled: true,
    });
    for (const client of openWindows) {
      if ("focus" in client) {
        await client.navigate(targetUrl);
        return client.focus();
      }
    }
    return self.clients.openWindow(targetUrl);
  })());
});
