// Renders markdown from bot messages into safe HTML
export function renderMarkdown(text) {
  let safe = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');

  // Bold & Italic
  safe = safe.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  safe = safe.replace(/\*(.+?)\*/g, '<em>$1</em>');

  const lines = safe.split('\n');
  let result = [];
  let inList = false;
  let tableRows = [];

  function flushTable() {
    if (tableRows.length === 0) return;
    const dataRows = tableRows.filter(r => !r.match(/^\|?[\s-:|]+\|?$/));
    if (dataRows.length === 0) { tableRows = []; return; }
    let html = '<table>';
    dataRows.forEach((row, i) => {
      const cells = row.split('|').map(c => c.trim()).filter(c => c !== '');
      if (i === 0) {
        html += '<thead><tr>' + cells.map(c => '<th>' + c + '</th>').join('') + '</tr></thead><tbody>';
      } else {
        html += '<tr>' + cells.map(c => '<td>' + c + '</td>').join('') + '</tr>';
      }
    });
    html += '</tbody></table>';
    result.push(html);
    tableRows = [];
  }

  for (const line of lines) {
    const trimmed = line.trim();

    // Table rows
    if (trimmed.includes('|') && (trimmed.startsWith('|') || trimmed.match(/^[^|]+\|/))) {
      if (inList) { result.push('</ul>'); inList = false; }
      tableRows.push(trimmed);
      continue;
    } else {
      flushTable();
    }

    // List items
    if (trimmed.startsWith('- ')) {
      if (!inList) { result.push('<ul>'); inList = true; }
      result.push('<li>' + trimmed.slice(2) + '</li>');
      continue;
    } else if (inList) {
      result.push('</ul>');
      inList = false;
    }

    // Horizontal rule
    if (trimmed.match(/^-{3,}$/)) {
      result.push('<hr>');
    } else if (trimmed.startsWith('#### ')) {
      result.push('<span class="sb-section-header">' + trimmed.slice(5) + '</span>');
    } else if (trimmed.startsWith('### ')) {
      result.push('<span class="sb-section-header">' + trimmed.slice(4) + '</span>');
    } else if (trimmed.startsWith('## ')) {
      result.push('<p><strong>' + trimmed.slice(3) + '</strong></p>');
    } else if (trimmed.startsWith('# ')) {
      result.push('<p><strong>' + trimmed.slice(2) + '</strong></p>');
    } else if (trimmed === '') {
      result.push('<br>');
    } else {
      result.push('<p>' + trimmed + '</p>');
    }
  }

  if (inList) result.push('</ul>');
  flushTable();

  return result.join('');
}
