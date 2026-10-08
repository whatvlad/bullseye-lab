// Only this worker can reach the loopback bot endpoint (site CSPs block page fetches).
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "bullseye-fills") return false;
  (async () => {
    for (const address of message.addresses.slice(0, 6)) {
      try {
        const response = await fetch(
          `http://127.0.0.1:8765/fills?address=${encodeURIComponent(address)}`,
          { cache: "no-store" }
        );
        if (!response.ok) continue;
        const data = await response.json();
        if (data.mint) return sendResponse({ ok: true, data });
      } catch {
        return sendResponse({ ok: false, error: "bot_offline" });
      }
    }
    sendResponse({ ok: true, data: null });
  })();
  return true;
});
