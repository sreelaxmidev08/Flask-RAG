(function () {
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function scoreText(source) {
    const fields = ['rerank_score', 'reranker_score', 'rrf_score', 'score'];
    const field = fields.find((key) => Number.isFinite(Number(source[key])));
    return field ? field.replace('_', ' ') + ' · ' + Number(source[field]).toFixed(4) : '';
  }

  function sourceCard(source, index, clickable) {
    const card = element('article', 'source-card');
    const top = element('div', 'source-card-top');
    top.append(element('span', 'source-number', index + 1));
    const heading = element('div');
    heading.append(element('div', 'source-title', source.title || 'Flask documentation'));
    top.append(heading);
    card.append(top);
    if (source.source_file) card.append(element('div', 'source-file', source.source_file));
    if (source.content) card.append(element('p', 'source-snippet', source.content));
    const score = scoreText(source);
    if (score) card.append(element('div', 'source-score', score));
    if (clickable) {
      card.tabIndex = 0;
      card.setAttribute('role', 'button');
      card.setAttribute('aria-label', 'Open source ' + (index + 1) + ': ' + (source.title || 'documentation'));
      card.addEventListener('click', () => window.FlaskDocsSources.onSelect(index));
      card.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); window.FlaskDocsSources.onSelect(index); }
      });
    }
    return card;
  }

  function appendHeaderActions(head, count) {
    const actions = element('div', 'source-actions');
    actions.append(element('span', 'source-count', count));
    const close = element('button', 'source-close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', 'Close sources panel');
    close.addEventListener('click', () => window.FlaskDocsSources.onClose());
    actions.append(close);
    head.append(actions);
  }

  function renderPanel(panel, sources, options) {
    panel.hidden = false;
    panel.replaceChildren();
    const head = element('div', 'source-head');
    const titleGroup = element('div');
    titleGroup.append(element('h2', '', options.title || 'Sources'));
    titleGroup.append(element('p', '', options.subtitle || 'Retrieved from Flask documentation'));
    head.append(titleGroup);
    appendHeaderActions(head, String(sources.length));
    panel.append(head);
    if (!sources.length) panel.append(element('p', 'source-empty', options.emptyText || 'No matching documentation was found.'));
    sources.forEach((source, index) => panel.append(sourceCard(source, index, options.clickable)));
  }

  window.FlaskDocsSources = {
    onSelect: function () {},
    onClose: function () {},
    renderSources(panel, sources) { renderPanel(panel, sources, { title: 'Sources', subtitle: 'References used for this answer', clickable: false }); },
    renderSearch(panel, results, query) {
      panel.hidden = false;
      panel.replaceChildren();
      const head = element('div', 'source-head');
      const group = element('div');
      group.append(element('h2', '', 'Explore docs'));
      group.append(element('p', '', 'Hybrid results for “' + query + '”'));
      head.append(group);
      appendHeaderActions(head, String(results.length));
      panel.append(head);
      const list = element('section', 'search-results');
      list.append(element('h3', '', 'Retrieved passages'));
      if (!results.length) list.append(element('p', 'source-empty', 'No matching documentation was found.'));
      results.forEach((item, index) => list.append(sourceCard(item, index, false)));
      panel.append(list);
    },
    renderEmpty(panel, message) {
      panel.hidden = false;
      panel.replaceChildren();
      const head = element('div', 'source-head');
      const group = element('div'); group.append(element('h2', '', 'Sources')); group.append(element('p', '', 'References used for this answer'));
      head.append(group);
      appendHeaderActions(head, '0');
      panel.append(head, element('p', 'source-empty', message || 'Sources are unavailable.'));
    }
  };
})();
