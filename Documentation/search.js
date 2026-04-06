// search.js — Docs search for Snap Rename Documentation
'use strict';

const SEARCH_INDEX = [
  { id: 'overview', section: 'Getting Started', title: 'Overview', keywords: 'overview intro what is snap rename batch file rename tool preview' },
  { id: 'download', section: 'Getting Started', title: 'Download & Setup', keywords: 'download install setup windows mac linux python web desktop app' },
  { id: 'workspace', section: 'Getting Started', title: 'Loading a Workspace', keywords: 'workspace directory folder loading open files file system access chromium' },
  { id: 'file-table', section: 'Getting Started', title: 'File Table', keywords: 'file table sort select multi-select alphabetical date size extension double click open' },
  { id: 'preview-pane', section: 'Getting Started', title: 'Preview Pane', keywords: 'preview pane file info metadata kind size created modified icon hide show' },
  { id: 'pipeline', section: 'Getting Started', title: 'Pipeline', keywords: 'pipeline steps stack multiple operations order sequence add remove clear' },
  // Application
  { id: 'app-overview', section: 'Application', title: 'Native Application Overview', keywords: 'application windows macos linux gui tui cli parity native cross-platform' },
  { id: 'app-usage', section: 'Application', title: 'Ease of Usage', keywords: 'ease of usage context menu quick actions native system file explorer finder' },
  { id: 'app-cli', section: 'Application', title: 'Terminal Commands (CLI)', keywords: 'terminal commands cli srename troubleshooting path gui command line args terminal linux macos windows' },
  { id: 'app-tui', section: 'Application', title: 'Terminal Interface (TUI)', keywords: 'terminal interface tui textual command palette shortcuts keys keyboard workflow live preview' },
  // Tools
  { id: 'clean', section: 'Rename Tools', title: 'Enhanced Clean Filename', keywords: 'clean spaces duplicates special numbers letters casing normalize dashes underscores capitalize uppercase lowercase remove strip' },
  { id: 'smart', section: 'Rename Tools', title: 'Smart Find & Replace', keywords: 'smart find replace pattern regex action remove replace insert standardize extract 21 patterns' },
  { id: 'normal', section: 'Rename Tools', title: 'Normal Find & Replace', keywords: 'normal find replace text literal phrase case sensitive simple' },
  { id: 'presuf', section: 'Rename Tools', title: 'Prefix / Suffix', keywords: 'prefix suffix add before after name constant text' },
  { id: 'numbering', section: 'Rename Tools', title: 'Sequential Numbering', keywords: 'sequential numbering number counter prefix suffix front end padding base name order' },
  { id: 'metadata', section: 'Rename Tools', title: 'Extended Smart Metadata', keywords: 'metadata smart template tags audio images video movies tv shows podcasts books scanned documents' },
  // Patterns
  { id: 'patterns-numbers', section: 'Smart Pattern', title: '1. Numbers', keywords: 'numbers digits sequences decimal regex remove replace insert' },
  { id: 'patterns-letters', section: 'Smart Pattern', title: '2. Letters', keywords: 'letters alphabet characters a-z alpha remove' },
  { id: 'patterns-spaces', section: 'Smart Pattern', title: '3. Spaces', keywords: 'spaces whitespace replace remove underscore dash' },
  { id: 'patterns-special', section: 'Smart Pattern', title: '4. Special Characters', keywords: 'special characters symbols at hash bang exclamation percent remove strip' },
  { id: 'patterns-dates', section: 'Smart Pattern', title: '5. Dates', keywords: 'dates year month day YYYYMMDD timestamp date format' },
  { id: 'patterns-brackets', section: 'Smart Pattern', title: '6. Brackets / Parentheses', keywords: 'brackets parentheses curly angle square [] () {} <> remove content' },
  { id: 'patterns-consec', section: 'Smart Pattern', title: '7. Consecutive Spaces', keywords: 'consecutive multiple spaces double triple whitespace collapse' },
  { id: 'patterns-underdash', section: 'Smart Pattern', title: '8. Underscores / Dashes', keywords: 'underscores dashes hyphens separators replace space' },
  { id: 'patterns-ext', section: 'Smart Pattern', title: '9. File Extension', keywords: 'file extension suffix rename change replace remove .mp3 .jpg' },
  { id: 'patterns-nonascii', section: 'Smart Pattern', title: '10. Non-ASCII Characters', keywords: 'non ascii unicode accents emoji foreign characters strip remove' },
  { id: 'patterns-leadtrail', section: 'Smart Pattern', title: '11. Leading/Trailing Spaces', keywords: 'leading trailing spaces trim whitespace beginning end' },
  { id: 'patterns-leadnums', section: 'Smart Pattern', title: '12. Leading Numbers', keywords: 'leading numbers prefix digits beginning strip remove' },
  { id: 'patterns-trailnums', section: 'Smart Pattern', title: '13. Trailing Numbers', keywords: 'trailing numbers suffix digits end strip remove' },
  { id: 'patterns-leadunder', section: 'Smart Pattern', title: '14. Leading/Trailing Underscores', keywords: 'leading trailing underscores trim strip' },
  { id: 'patterns-capcap', section: 'Smart Pattern', title: '15. Capitalize First Letter', keywords: 'capitalize first letter title case word beginning' },
  { id: 'patterns-upper', section: 'Smart Pattern', title: '16. Uppercase All Letters', keywords: 'uppercase all letters caps transform' },
  { id: 'patterns-lower', section: 'Smart Pattern', title: '17. Lowercase All Letters', keywords: 'lowercase all letters small transform' },
  { id: 'patterns-swap', section: 'Smart Pattern', title: '18. Swap Words', keywords: 'swap words reverse order first second exchange' },
  { id: 'patterns-charpos', section: 'Smart Pattern', title: '19. Character Position', keywords: 'character position insert specific index 1-based stem extension insert text at position' },
  { id: 'patterns-exact', section: 'Smart Pattern', title: '20. Custom Exact', keywords: 'custom exact literal text phrase match find all occurrences' },
  { id: 'patterns-regex', section: 'Smart Pattern', title: '21. Custom Regex', keywords: 'custom regex regular expression pattern advanced javascript global' },
  // Actions
  { id: 'actions', section: 'Rename Tools', title: 'All 8 Actions', keywords: 'actions remove replace with insert before insert after standardize extract insert stem extension' },
  // Apply & Undo
  { id: 'apply', section: 'Apply & Undo', title: 'Applying Renames', keywords: 'apply rename all selected conflict copies confirm modal success' },
  { id: 'undo', section: 'Apply & Undo', title: 'Undo', keywords: 'undo revert reverse last batch rename history session' },
  { id: 'dragdrop', section: 'Apply & Undo', title: 'Drag & Drop', keywords: 'drag drop files import add copy conflict replace keep both' },
  { id: 'metadata-tags', section: 'Reference', title: 'Metadata Tags Reference', keywords: 'tags artist album track title year genre show season episode author camera resolution original modified created size_kb exif_date codec duration original type' },
];

const input = document.getElementById('search-input');
const resultsBox = document.getElementById('search-results');

function doSearch(q) {
  q = q.trim().toLowerCase();
  if (!q) { resultsBox.classList.add('hidden'); resultsBox.innerHTML = ''; return; }

  const matches = SEARCH_INDEX.filter(item =>
    item.title.toLowerCase().includes(q) ||
    item.keywords.toLowerCase().includes(q) ||
    item.section.toLowerCase().includes(q)
  );

  if (!matches.length) {
    resultsBox.innerHTML = '<div class="search-no-results">No results for "' + q + '"</div>';
    resultsBox.classList.remove('hidden');
    return;
  }

  resultsBox.innerHTML = matches.slice(0, 10).map(item => `
    <div class="search-result-item" data-href="#${item.id}">
      <div class="sri-section">${item.section}</div>
      <div class="sri-title">${highlight(item.title, q)}</div>
    </div>
  `).join('');
  resultsBox.classList.remove('hidden');

  resultsBox.querySelectorAll('.search-result-item').forEach(el => {
    el.addEventListener('click', () => {
      const href = el.dataset.href;
      const target = document.querySelector(href);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      resultsBox.classList.add('hidden');
      input.value = '';
    });
  });
}

function highlight(text, q) {
  const re = new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')})`, 'gi');
  return text.replace(re, '<mark style="background:rgba(108,99,255,0.3);color:inherit;border-radius:2px">$1</mark>');
}

input.addEventListener('input', () => doSearch(input.value));
input.addEventListener('focus', () => { if (input.value.trim()) doSearch(input.value); });

document.addEventListener('click', e => {
  if (!e.target.closest('.search-wrap') && !e.target.closest('.search-results')) {
    resultsBox.classList.add('hidden');
  }
});
input.addEventListener('keydown', e => {
  if (e.key === 'Escape') { resultsBox.classList.add('hidden'); input.blur(); }
});
