(function () {
  const STORAGE_KEY = 'flaskDocsConversationsV1';
  const TOP_K = 5;
  const $ = (selector) => document.querySelector(selector);
  const view = $('#conversationView');
  const panel = $('#sourcesPanel');
  const form = $('#composerForm');
  const input = $('#questionInput');
  const send = $('#sendButton');
  const list = $('#conversationList');
  const appShell = $('.app-shell');
  const sidebarToggle = $('#sidebarToggle');
  let conversations = readConversations();
  let activeId = conversations[0] && conversations[0].id;
  let busy = false;
  let searchMode = false;
  let controller = null;
  let toastTimer;
  const sourcesToggle = $('#toggleSources');

  function readConversations() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      const restored = Array.isArray(value) ? value.filter((item) => item && item.id && Array.isArray(item.messages)) : [];
      restored.forEach((chat) => chat.messages.forEach((message) => {
        if (message.status === 'streaming') { message.status = 'error'; message.error = 'This answer was interrupted. Retry to ask again.'; }
      }));
      return restored;
    } catch (_) { return []; }
  }
  function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations)); }
  function active() { return conversations.find((item) => item.id === activeId); }
  function id() { return window.crypto && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2); }
  function toast(message) {
    const node = $('#toast'); node.textContent = message; node.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => node.classList.remove('show'), 2600);
  }
  function escapeText(parent, text) { parent.append(document.createTextNode(text)); }

  function appendInline(parent, text, sources) {
    const pattern = /(\[\d+\]|`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
    let cursor = 0; let match;
    while ((match = pattern.exec(text))) {
      escapeText(parent, text.slice(cursor, match.index));
      const token = match[0];
      if (token[0] === '[') {
        const sourceIndex = Number(token.slice(1, -1)) - 1;
        if (sources && sources[sourceIndex]) {
          const citation = document.createElement('button'); citation.className = 'citation'; citation.type = 'button';
          citation.textContent = token; citation.setAttribute('aria-label', 'View source ' + (sourceIndex + 1));
          citation.addEventListener('click', () => window.FlaskDocsSources.onSelect(sourceIndex)); parent.append(citation);
        } else escapeText(parent, token);
      } else if (token[0] === '`') {
        const code = document.createElement('code'); code.textContent = token.slice(1, -1); parent.append(code);
      } else {
        const emphasis = document.createElement(token.startsWith('**') ? 'strong' : 'em');
        emphasis.textContent = token.startsWith('**') ? token.slice(2, -2) : token.slice(1, -1); parent.append(emphasis);
      }
      cursor = pattern.lastIndex;
    }
    escapeText(parent, text.slice(cursor));
  }

  function renderMarkdown(container, markdown, sources) {
    const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n');
    let paragraph = []; let listNode = null; let codeLines = null;
    const flushParagraph = () => {
      if (!paragraph.length) return;
      const p = document.createElement('p'); appendInline(p, paragraph.join(' '), sources); container.append(p); paragraph = [];
    };
    const closeList = () => { listNode = null; };
    lines.forEach((line) => {
      if (/^\s*```/.test(line)) {
        flushParagraph(); closeList();
        if (codeLines) {
          const pre = document.createElement('pre'); const code = document.createElement('code'); code.textContent = codeLines.join('\n'); pre.append(code); container.append(pre); codeLines = null;
        } else codeLines = [];
        return;
      }
      if (codeLines) { codeLines.push(line); return; }
      if (!line.trim()) { flushParagraph(); closeList(); return; }
      const heading = line.match(/^(#{1,3})\s+(.+)$/);
      if (heading) { flushParagraph(); closeList(); const h = document.createElement(heading[1].length === 1 ? 'h2' : 'h3'); appendInline(h, heading[2], sources); container.append(h); return; }
      const item = line.match(/^\s*(?:[-*]|\d+\.)\s+(.+)$/);
      if (item) {
        flushParagraph(); const ordered = /^\s*\d+\./.test(line);
        if (!listNode || listNode.tagName.toLowerCase() !== (ordered ? 'ol' : 'ul')) { closeList(); listNode = document.createElement(ordered ? 'ol' : 'ul'); container.append(listNode); }
        const li = document.createElement('li'); appendInline(li, item[1], sources); listNode.append(li); return;
      }
      closeList(); paragraph.push(line.trim());
    });
    if (codeLines) { const pre = document.createElement('pre'); const code = document.createElement('code'); code.textContent = codeLines.join('\n'); pre.append(code); container.append(pre); }
    flushParagraph();
  }

  function renderMessage(message) {
    const row = document.createElement('article'); row.className = 'message ' + (message.role === 'user' ? 'user' : 'assistant');
    if (message.role !== 'user') row.append(Object.assign(document.createElement('span'), { className: 'message-avatar', textContent: '✦', 'aria-hidden': true }));
    const body = document.createElement('div'); body.className = 'message-body'; const text = document.createElement('div'); text.className = 'message-text';
    if (message.role === 'user') text.textContent = message.content;
    else renderMarkdown(text, message.content, message.sources);
    body.append(text);
    if (message.status === 'streaming') {
      const typing = document.createElement('div'); typing.className = 'typing'; typing.setAttribute('aria-label', 'Answer is streaming');
      for (let index = 0; index < 3; index += 1) typing.append(document.createElement('i'));
      body.append(typing);
    }
    if (message.status === 'error') {
      const note = document.createElement('div'); note.className = 'error-note';
      note.append(document.createTextNode(message.error || 'The answer could not be completed.'));
      const retry = document.createElement('button'); retry.type = 'button'; retry.className = 'retry-button'; retry.textContent = 'Retry';
      retry.addEventListener('click', () => sendQuestion(message.query, true)); note.append(retry); body.append(note);
    }
    row.append(body); return row;
  }

  function renderConversation() {
    view.replaceChildren(); const conversation = active();
    if (!conversation || !conversation.messages.length) { renderWelcome(); return; }
    const stack = document.createElement('div'); stack.className = 'message-list';
    conversation.messages.forEach((message) => stack.append(renderMessage(message)));
    view.append(stack); view.scrollTop = view.scrollHeight;
  }

  function renderWelcome() {
    const welcome = document.createElement('div'); welcome.className = 'welcome';
    const orb = document.createElement('div'); orb.className = 'orb'; orb.setAttribute('aria-hidden', 'true');
    welcome.append(orb);
    const eyebrow = document.createElement('p'); eyebrow.className = 'eyebrow'; eyebrow.textContent = 'Your Flask documentation guide'; welcome.append(eyebrow);
    const title = document.createElement('h1'); title.textContent = 'How can I help you today?'; welcome.append(title);
    const subtitle = document.createElement('p'); subtitle.className = 'welcome-subtitle'; subtitle.textContent = 'Ask a question and get a clear answer grounded in the official Flask docs.'; welcome.append(subtitle);
    const suggestions = document.createElement('div'); suggestions.className = 'suggestions';
    [
      ['↗', 'How do I define a route in Flask?'],
      ['⇄', 'How does Flask handle HTTP requests?'],
      ['⌖', 'How do I access URL parameters?'],
      ['◉', 'How do Flask application contexts work?']
    ].forEach(([icon, question]) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'suggestion';
      const symbol = document.createElement('span'); symbol.className = 'suggestion-icon'; symbol.textContent = icon;
      button.append(symbol, document.createTextNode(question)); const arrow = document.createElement('span'); arrow.className = 'suggestion-arrow'; arrow.textContent = '↗'; button.append(arrow);
      button.addEventListener('click', () => sendQuestion(question)); suggestions.append(button);
    });
    welcome.append(suggestions); view.replaceChildren(welcome);
  }

  function renderHistory() {
    list.replaceChildren(); const filter = ($('#historyFilter').value || '').toLowerCase();
    const sorted = [...conversations].sort((a, b) => b.updatedAt - a.updatedAt).filter((chat) => (chat.title || 'New chat').toLowerCase().includes(filter));
    if (!sorted.length) { const empty = document.createElement('div'); empty.className = 'group-label'; empty.textContent = conversations.length ? 'No matching chats' : 'Your chats will appear here'; list.append(empty); return; }
    const today = new Date(); today.setHours(0, 0, 0, 0); const yesterday = today.getTime() - 86400000;
    const groups = new Map();
    sorted.forEach((chat) => { const time = new Date(chat.updatedAt || Date.now()).setHours(0, 0, 0, 0); const label = time >= today.getTime() ? 'Today' : time >= yesterday ? 'Yesterday' : 'Earlier'; if (!groups.has(label)) groups.set(label, []); groups.get(label).push(chat); });
    groups.forEach((chats, label) => {
      const group = document.createElement('div'); group.className = 'conversation-group'; group.append(Object.assign(document.createElement('div'), { className: 'group-label', textContent: label }));
      chats.forEach((chat) => {
        const row = document.createElement('div'); row.className = 'conversation-row' + (chat.id === activeId ? ' selected' : '');
        const select = document.createElement('button'); select.type = 'button'; select.className = 'conversation-select'; select.textContent = chat.title || 'New chat'; select.title = select.textContent;
        select.addEventListener('click', () => { activeId = chat.id; closeSidebar(); render(); });
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'conversation-delete'; remove.textContent = '×'; remove.setAttribute('aria-label', 'Delete ' + (chat.title || 'conversation'));
        remove.addEventListener('click', () => { conversations = conversations.filter((item) => item.id !== chat.id); if (activeId === chat.id) activeId = conversations[0] && conversations[0].id; save(); render(); });
        row.append(select, remove); group.append(row);
      });
      list.append(group);
    });
  }
  function render() { renderHistory(); renderConversation(); }

  function newConversation() {
    const conversation = { id: id(), title: 'New chat', updatedAt: Date.now(), messages: [] };
    conversations.unshift(conversation); activeId = conversation.id; save(); render(); input.focus(); closeSidebar();
  }
  function updateSidebarToggle() {
    const isMobile = window.matchMedia('(max-width: 760px)').matches;
    const collapsed = appShell.classList.contains('sidebar-collapsed');
    if (isMobile) {
      sidebarToggle.textContent = '‹';
      sidebarToggle.setAttribute('aria-label', 'Close sidebar');
      sidebarToggle.title = 'Close sidebar';
      sidebarToggle.setAttribute('aria-expanded', String($('#sidebar').classList.contains('open')));
    } else {
      sidebarToggle.textContent = collapsed ? '›' : '‹';
      sidebarToggle.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
      sidebarToggle.title = collapsed ? 'Expand sidebar' : 'Collapse sidebar';
      sidebarToggle.setAttribute('aria-expanded', String(!collapsed));
    }
  }
  function closeSidebar() {
    $('#sidebar').classList.remove('open'); $('#mobileScrim').classList.remove('open'); updateSidebarToggle();
  }
  function toggleSidebar() {
    if (window.matchMedia('(max-width: 760px)').matches) { closeSidebar(); return; }
    appShell.classList.toggle('sidebar-collapsed');
    updateSidebarToggle();
  }
  function setSourcesOpen(open) {
    panel.hidden = !open;
    sourcesToggle.setAttribute('aria-expanded', String(open));
    sourcesToggle.classList.toggle('active', open);
  }
  function setSearchMode(enabled) {
    searchMode = enabled; input.placeholder = enabled ? 'Search Flask documentation…' : 'Ask anything about Flask…';
    send.setAttribute('aria-label', enabled ? 'Search documentation' : 'Send question');
    if (enabled) { toast('Search mode on · Enter a topic to explore documentation'); input.focus(); }
  }

  async function runSearch(query) {
    setBusy(true); window.FlaskDocsSources.renderEmpty(panel, 'Searching hybrid index…');
    setSourcesOpen(true);
    try { const results = await window.FlaskDocsAPI.search(query, TOP_K); window.FlaskDocsSources.renderSearch(panel, results, query); }
    catch (error) { window.FlaskDocsSources.renderEmpty(panel, 'Search failed: ' + error.message); }
    finally { setBusy(false); setSearchMode(false); }
  }

  function setBusy(value) {
    busy = value; send.disabled = value; input.disabled = value;
    send.replaceChildren();
    if (value) { send.textContent = '…'; return; }
    const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    icon.setAttribute('viewBox', '0 0 20 20'); icon.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', 'M10 16V4M5.5 8.5 10 4l4.5 4.5'); icon.append(path); send.append(icon);
  }
  async function sendQuestion(rawQuestion, retry) {
    const query = String(rawQuestion || '').trim(); if (!query || busy) return;
    if (searchMode) { input.value = ''; updateCount(); await runSearch(query); return; }
    let conversation = active(); if (!conversation) { conversation = { id: id(), title: 'New chat', updatedAt: Date.now(), messages: [] }; conversations.unshift(conversation); activeId = conversation.id; }
    let userMessage;
    if (retry) {
      const existing = conversation.messages.findLast ? conversation.messages.findLast((m) => m.role === 'user' && m.content === query) : [...conversation.messages].reverse().find((m) => m.role === 'user' && m.content === query);
      userMessage = existing;
    } else {
      userMessage = { role: 'user', content: query, createdAt: Date.now() }; conversation.messages.push(userMessage);
    }
    const assistant = { role: 'assistant', content: '', query, sources: null, status: 'streaming', createdAt: Date.now() };
    conversation.messages.push(assistant); if (!conversation.messages.some((m) => m.role === 'assistant')) conversation.title = query.slice(0, 45);
    if (conversation.title === 'New chat') conversation.title = query.length > 45 ? query.slice(0, 45) + '…' : query;
    conversation.updatedAt = Date.now(); save(); setBusy(true); input.value = ''; updateCount(); render();
    controller = new AbortController();
    try {
      await window.FlaskDocsAPI.stream(query, TOP_K, (event) => {
        if (event.type === 'chunk' && typeof event.content === 'string') { assistant.content += event.content; renderConversation(); }
        if (event.type === 'sources' && Array.isArray(event.sources)) {
          assistant.sources = event.sources;
          window.FlaskDocsSources.renderSources(panel, assistant.sources);
          setSourcesOpen(true);
        }
        if (event.type === 'error') throw new Error(event.message || 'The answer could not be generated.');
      }, controller.signal);
      assistant.status = 'complete';
      if (!assistant.sources) { window.FlaskDocsSources.renderEmpty(panel, 'The API did not return source details for this answer.'); setSourcesOpen(true); }
    } catch (error) {
      assistant.status = 'error'; assistant.error = error.name === 'AbortError' ? 'Request cancelled.' : error.message || 'Could not connect to the API. Check that the backend is running.';
      if (error.name !== 'AbortError') { window.FlaskDocsSources.renderEmpty(panel, 'Sources are unavailable because the request did not finish.'); setSourcesOpen(true); }
    } finally {
      controller = null; conversation.updatedAt = Date.now(); save(); setBusy(false); render();
    }
  }

  function updateCount() { $('#charCount').textContent = input.value.length + ' / 4000'; input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 180) + 'px'; }

  window.FlaskDocsSources.onSelect = (index) => {
    setSourcesOpen(true);
    const card = panel.querySelectorAll('.source-card')[index];
    if (card) { card.scrollIntoView({ behavior: 'smooth', block: 'center' }); card.classList.add('selected'); setTimeout(() => card.classList.remove('selected'), 1300); }
    else toast('Source ' + (index + 1) + ' is not available.');
  };
  window.FlaskDocsSources.onClose = () => setSourcesOpen(false);

  form.addEventListener('submit', (event) => { event.preventDefault(); sendQuestion(input.value); });
  input.addEventListener('input', updateCount);
  input.addEventListener('keydown', (event) => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendQuestion(input.value); } });
  $('#newChat').addEventListener('click', newConversation);
  $('#historyFilter').addEventListener('input', renderHistory);
  $('#searchToggle').addEventListener('click', () => setSearchMode(!searchMode));
  sourcesToggle.addEventListener('click', () => setSourcesOpen(panel.hidden));
  $('#openSidebar').addEventListener('click', () => { $('#sidebar').classList.add('open'); $('#mobileScrim').classList.add('open'); updateSidebarToggle(); });
  sidebarToggle.addEventListener('click', toggleSidebar); $('#mobileScrim').addEventListener('click', closeSidebar);
  window.matchMedia('(max-width: 760px)').addEventListener('change', (event) => {
    if (event.matches) appShell.classList.remove('sidebar-collapsed');
    updateSidebarToggle();
  });
  updateSidebarToggle();
  render();
  window.FlaskDocsSources.renderEmpty(panel, 'Sources will appear here after an answer or documentation search.');
  setSourcesOpen(false);
})();
