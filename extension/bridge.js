// Isolated world: find token addresses in the URL, ask the bot, hand fills to the page.
const BASE58 = /[1-9A-HJ-NP-Za-km-z]{32,44}/g;

function candidates() {
  const text = decodeURIComponent(location.pathname + " " + location.search);
  const found = [...new Set(text.match(BASE58) || [])];
  // Pump mints end in "pump"; try them first.
  return found.sort((a, b) => Number(b.endsWith("pump")) - Number(a.endsWith("pump")));
}

function poll() {
  const addresses = candidates();
  if (!addresses.length) {
    window.postMessage({ __bullseye: true, data: null }, location.origin);
    return;
  }
  chrome.runtime.sendMessage({ type: "bullseye-fills", addresses }, (reply) => {
    if (chrome.runtime.lastError || !reply) return;
    window.postMessage(
      { __bullseye: true, data: reply.ok ? reply.data : null, offline: !reply.ok },
      location.origin
    );
  });
}

poll();
setInterval(poll, 3000);
