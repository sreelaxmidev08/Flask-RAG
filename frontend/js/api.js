(function () {
  const DEFAULT_BASE = 'http://localhost:8000';
  const API_KEY = 'flaskDocsApiBase';

  function baseUrl() {
    const saved = localStorage.getItem(API_KEY);
    return (saved || DEFAULT_BASE).replace(/\/+$/, '');
  }

  function endpoint(path, params) {
    const url = new URL(baseUrl() + path);
    Object.entries(params || {}).forEach(([key, value]) => url.searchParams.set(key, value));
    return url;
  }

  async function checkHealth() {
    const response = await fetch(baseUrl() + '/health', { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error('API returned ' + response.status);
    return response.json();
  }

  async function search(query, topK, signal) {
    const response = await fetch(endpoint('/search', { q: query, size: topK, mode: 'hybrid' }), {
      signal,
      headers: { Accept: 'application/json' }
    });
    if (!response.ok) throw new Error(await safeError(response));
    const payload = await response.json();
    return Array.isArray(payload.results) ? payload.results : [];
  }

  async function stream(query, topK, onEvent, signal) {
    const response = await fetch(endpoint('/stream', { q: query, top_k: topK }), {
      signal,
      headers: { Accept: 'text/event-stream' }
    });
    if (!response.ok) throw new Error(await safeError(response));
    if (!response.body) throw new Error('This browser does not support response streaming.');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let receivedDone = false;
    const dispatch = (block) => {
      const data = block.split('\n').filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).replace(/^ /, '')).join('\n');
      if (!data) return;
      let event;
      try { event = JSON.parse(data); } catch (_) { throw new Error('The API sent an unreadable streaming event.'); }
      if (event.type === 'done') receivedDone = true;
      onEvent(event);
    };

    try {
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
        buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        let boundary;
        while ((boundary = buffer.indexOf('\n\n')) !== -1) {
          dispatch(buffer.slice(0, boundary));
          buffer = buffer.slice(boundary + 2);
        }
        if (done) break;
      }
      if (buffer.trim()) dispatch(buffer);
      if (!receivedDone) throw new Error('The connection ended before the answer was complete. Please try again.');
    } catch (error) {
      if (signal && signal.aborted) throw error;
      try { await reader.cancel(); } catch (_) { /* Reader may already be closed. */ }
      throw error;
    }
  }

  async function safeError(response) {
    try {
      const data = await response.json();
      return (data.detail && (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))) || ('Request failed (' + response.status + ')');
    } catch (_) { return 'Request failed (' + response.status + ')'; }
  }

  window.FlaskDocsAPI = {
    baseUrl,
    setBaseUrl(value) {
      const parsed = new URL(value);
      if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error('Use an http:// or https:// API address.');
      localStorage.setItem(API_KEY, parsed.origin + parsed.pathname.replace(/\/$/, ''));
    },
    checkHealth,
    search,
    stream
  };
})();
