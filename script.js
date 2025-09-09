(function () {
  const TABS_CONTAINER_ID = 'tabs';
  const CONTENT_CONTAINER_ID = 'content';
  const TEXT_FILE = 'The Secret Lives of Urban Wildlife.txt';

  /**
   * Heuristic: Treat non-empty lines that look like titles as section headings.
   * - Title case or sentence case lines without trailing period are headings
   * - Fallback: first line is document title, following title-like lines start sections
   */
  function parseSectionsFromText(raw) {
    const lines = raw.split(/\r?\n/);
    const sections = [];
    let current = null;

    const isLikelyHeading = (line) => {
      const trimmed = line.trim();
      if (!trimmed) return false;
      if (trimmed.length > 120) return false; // too long for a heading
      const endsWithPeriod = /[.!?]$/.test(trimmed);
      if (endsWithPeriod) return false;
      const words = trimmed.split(/\s+/);
      const capitalizedWords = words.filter(w => /^[A-Z][\w'\-]*$/.test(w));
      const ratio = capitalizedWords.length / Math.max(1, words.length);
      return ratio >= 0.4 || /^[A-Z]/.test(trimmed);
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      if (!trimmed) continue;

      if (isLikelyHeading(trimmed)) {
        // Start a new section
        if (current) sections.push(current);
        current = { title: trimmed, body: [] };
      } else {
        if (!current) {
          // Prepend to an implicit introduction section
          current = { title: 'Introduction', body: [] };
        }
        current.body.push(trimmed);
      }
    }
    if (current) sections.push(current);

    // Merge body lines and clean up
    return sections.map(sec => ({
      title: sec.title,
      body: sec.body.join('\n\n')
    }));
  }

  function slugify(text) {
    return text.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .trim()
      .replace(/\s+/g, '-')
      .slice(0, 60);
  }

  function render(sections) {
    const tabsEl = document.getElementById(TABS_CONTAINER_ID);
    const contentEl = document.getElementById(CONTENT_CONTAINER_ID);
    tabsEl.innerHTML = '';
    contentEl.innerHTML = '';

    tabsEl.setAttribute('role', 'tablist');

    sections.forEach((sec, index) => {
      const id = slugify(sec.title) || `section-${index + 1}`;

      const btn = document.createElement('button');
      btn.className = 'tab';
      btn.setAttribute('role', 'tab');
      btn.setAttribute('aria-controls', id);
      btn.textContent = sec.title;
      if (index === 0) btn.setAttribute('aria-selected', 'true');

      btn.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(b => b.setAttribute('aria-selected', 'false'));
        btn.setAttribute('aria-selected', 'true');
        showSection(id);
      });

      tabsEl.appendChild(btn);

      const sectionEl = document.createElement('section');
      sectionEl.id = id;
      sectionEl.hidden = index !== 0;

      const h2 = document.createElement('h2');
      h2.className = 'section-title';
      h2.textContent = sec.title;

      const p = document.createElement('div');
      p.className = 'section-body';
      p.textContent = sec.body;

      sectionEl.appendChild(h2);
      sectionEl.appendChild(p);
      contentEl.appendChild(sectionEl);
    });
  }

  function showSection(id) {
    document.querySelectorAll('#content section').forEach(sec => {
      sec.hidden = sec.id !== id;
    });
  }

  async function init() {
    try {
      const res = await fetch(encodeURI(TEXT_FILE), { cache: 'no-store' });
      if (!res.ok) throw new Error(`Failed to load text: ${res.status}`);
      const txt = await res.text();
      const sections = parseSectionsFromText(txt);
      if (!sections.length) throw new Error('No content sections parsed.');
      render(sections);
    } catch (err) {
      const contentEl = document.getElementById(CONTENT_CONTAINER_ID);
      contentEl.innerHTML = '';
      const pre = document.createElement('pre');
      pre.style.whiteSpace = 'pre-wrap';
      pre.textContent = `Error: ${err.message}\nMake sure the text file is served alongside index.html.`;
      contentEl.appendChild(pre);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();


