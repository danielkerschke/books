"""Build the reader for one volume from the proofread pages.

    python build.py v1      # proof/v1/*.md  ->  ../reader/band-1/

Pages are read in book order (Vorrede rV…, then p001…), joined into one stream of blocks,
and cut into chapters at every `##` heading. Footnotes are renumbered per chapter.
Missing pages are reported and skipped (so a partial build works while proofreading runs).
"""
import html, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VOL = sys.argv[1]
ROMAN = ['V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV']

BOOK = 'Das Erkenntnisproblem'
SUB = 'in der Philosophie und Wissenschaft der neueren Zeit'
VOLUMES = {
    'v1': dict(
        band='Erster Band', out='band-1', last=601, roman=ROMAN[:6], year=1911,
        # sections printed with a number only ("I."): short labels from the printed table of contents
        labels={
            'buch-1-kapitel-1': ['Gott und Welt', 'Verstand und Sinnlichkeit', 'Die symbolische Verwendung der Mathematik',
                                 'Objekt und Funktion des Denkens'],
            'buch-1-kapitel-3': ['Montaigne'],
            'buch-2-kapitel-1': ['Girolamo Fracastoro', 'Telesio', 'Campanella',
                                 'Der Begriff der Weltseele', 'Einheit und Vielheit', 'Der Begriff des Minimums'],
            'buch-3-kapitel-2': ['Die Idee der rationalen Erkenntnis', 'Das Problem der Ethik',
                                 'Die Anfänge der modernen Psychologie', 'Der psychologische Idealismus',
                                 'Bayle und Montaigne', 'Vernunft und Offenbarung'],
        },
        byline='Ernst Cassirer · Zweite, durchgesehene Auflage · Berlin 1911',
        books={1: 'Erstes Buch · Die Renaissance des Erkenntnisproblems',
               2: 'Zweites Buch · Die Entdeckung des Naturbegriffs',
               3: 'Drittes Buch · Die Grundlegung des Idealismus'},
        # one entry per `##` heading, in order: slug, book, chapter number label, title
        chapters=[
            ('vorrede', None, '', 'Vorrede'),
            ('einleitung', None, '', 'Einleitung'),
            ('buch-1-kapitel-1', 1, 'Erstes Kapitel', 'Nikolaus Cusanus'),
            ('buch-1-kapitel-2', 1, 'Zweites Kapitel', 'Der Humanismus und der Kampf der Platonischen und Aristotelischen Philosophie'),
            ('buch-1-kapitel-3', 1, 'Drittes Kapitel', 'Der Skepticismus'),
            ('buch-2-kapitel-1', 2, 'Erstes Kapitel', 'Die Naturphilosophie'),
            ('buch-2-kapitel-2', 2, 'Zweites Kapitel', 'Die Entstehung der exakten Wissenschaft'),
            ('buch-3-kapitel-1', 3, 'Erstes Kapitel', 'Descartes'),
            ('buch-3-kapitel-2', 3, 'Zweites Kapitel', 'Die Fortbildung der Cartesischen Philosophie'),
        ]),
    'v2': dict(
        band='Zweiter Band', out='band-2', last=762, roman=[], year=1922,
        labels={
            'buch-4-kapitel-3': ['Die Definition des Wissens', 'Begriff und Wort', 'Raum und Zeit'],
            'buch-5-kapitel-2': ['Vernunftwahrheiten und Tatsachenwahrheiten', 'Das Alphabet der Gedanken',
                                 'Der Symbolbegriff', 'Das Postulat des „absoluten Verstandes“'],
            'buch-5-kapitel-4': ['Herbert von Cherbury', 'Die Schule von Cambridge'],
            'buch-7-kapitel-2': ['Isaac Watts’ Enquiry concerning Space'],
            'buch-7-kapitel-3': ['Der Wahrheitsbegriff bei Leibniz und Wolff',
                                 'Der Satz des Widerspruchs und der Satz vom zureichenden Grunde'],
            'buch-7-kapitel-4': ['Fortbildung und Kritik von Lockes Psychologie',
                                 'Das psychologische und das logische Wahrheitskriterium'],
            'buch-8-kapitel-1': ['Die Schriften des Jahres 1763', 'Die „Träume eines Geistersehers“ (1765)',
                                 'Von den „Träumen eines Geistersehers“ bis zur „Dissertation“ (1765–69)',
                                 'Vorbereitung und Abschluß der Dissertation (1769–70)',
                                 'Der Fortschritt zur Vernunftkritik (1772–1781)'],
            'buch-8-kapitel-2': ['Der metaphysische Gegensatz von Subjekt und Objekt und seine geschichtliche Entwicklung',
                                 'Das „Ding an sich“'],
        },
        byline='Ernst Cassirer · Dritte Auflage · Berlin 1922',
        books={4: 'Viertes Buch · Die Anfänge des Empirismus',
               5: 'Fünftes Buch · Fortbildung und Vollendung des Rationalismus',
               6: 'Sechstes Buch · Das Erkenntnisproblem im System des Empirismus',
               7: 'Siebentes Buch · Von Newton zu Kant',
               8: 'Achtes Buch · Die kritische Philosophie'},
        chapters=[
            ('buch-4-kapitel-1', 4, 'Erstes Kapitel', 'Bacon'),
            ('buch-4-kapitel-2', 4, 'Zweites Kapitel', 'Gassendi'),
            ('buch-4-kapitel-3', 4, 'Drittes Kapitel', 'Hobbes'),
            ('buch-5-kapitel-1', 5, 'Erstes Kapitel', 'Spinoza'),
            ('buch-5-kapitel-2', 5, 'Zweites Kapitel', 'Leibniz'),
            ('buch-5-kapitel-3', 5, 'Drittes Kapitel', 'Tschirnhaus'),
            ('buch-5-kapitel-4', 5, 'Viertes Kapitel', 'Der Rationalismus in der englischen Philosophie'),
            ('buch-6-kapitel-1', 6, 'Erstes Kapitel', 'Locke'),
            ('buch-6-kapitel-2', 6, 'Zweites Kapitel', 'Berkeley'),
            ('buch-6-kapitel-3', 6, 'Drittes Kapitel', 'Hume'),
            ('buch-7-kapitel-1', 7, 'Erstes Kapitel', 'Das Problem der Methode'),
            ('buch-7-kapitel-2', 7, 'Zweites Kapitel', 'Raum und Zeit'),
            ('buch-7-kapitel-3', 7, 'Drittes Kapitel', 'Die Ontologie. — Der Satz des Widerspruchs und der Satz vom zureichenden Grunde'),
            ('buch-7-kapitel-4', 7, 'Viertes Kapitel', 'Das Problem des Bewußtseins. — Subjektive und objektive Begründung der Erkenntnis'),
            ('buch-8-kapitel-1', 8, 'Erstes Kapitel', 'Die Entstehung der kritischen Philosophie'),
            ('buch-8-kapitel-2', 8, 'Zweites Kapitel', 'Die Vernunftkritik'),
        ]),
    'v3': dict(
        band='Dritter Band', band_sub='Die nachkantischen Systeme', out='band-3', last=483, roman=ROMAN[:4],
        year=1920, labels={}, byline='Ernst Cassirer · Berlin 1920', books={},
        chapters=[
            ('vorwort', None, '', 'Vorwort'),
            ('einleitung', None, '', 'Einleitung'),
            ('kapitel-1', None, 'Erstes Kapitel', 'Der »Gegenstand der Erfahrung« und das »Ding an sich«'),
            ('kapitel-2', None, 'Zweites Kapitel', 'Fichte'),
            ('kapitel-3', None, 'Drittes Kapitel', 'Schelling'),
            ('kapitel-4', None, 'Viertes Kapitel', 'Hegel'),
            ('kapitel-5', None, 'Fünftes Kapitel', 'Herbart'),
            ('kapitel-6', None, 'Sechstes Kapitel', 'Schopenhauer'),
            ('kapitel-7', None, 'Siebentes Kapitel', 'Fries'),
        ]),
}
V = VOLUMES[VOL]
PROOF = os.path.join(HERE, 'proof', VOL)
OUT = os.path.join(HERE, '..', 'reader', V['out'])
TITLE = '%s · %s' % (BOOK, V['band'])

warnings = []
def warn(*a): warnings.append(' '.join(str(x) for x in a))

# ------------------------------------------------------------------ inline markup
TAGS = {'g': ('<span class="sp">', '</span>'), 'i': ('<i>', '</i>'), 'b': ('<b>', '</b>'),
        'sup': ('<sup>', '</sup>'), 'sub': ('<sub>', '</sub>')}
def inline(t):
    t = re.sub(r"(?<=\w)'(?=\w)", '’', t)          # l'homme -> l’homme (the print uses ’)
    t = re.sub(r'(?<=\d)\s?[—–]\s?(?=\d)', '–', t)    # number ranges: one consistent en dash (§ 103–105)
    t = html.escape(t, quote=False)
    for tag, (o, c) in TAGS.items():
        t = t.replace('&lt;%s&gt;' % tag, o).replace('&lt;/%s&gt;' % tag, c)
    t = re.sub(r'\{\?([^}]*)\}', r'<span class="unsure" title="unsichere Lesung">\1</span>', t)
    return t

def join(a, b, marker=''):
    """Join text continued across a page (or note) break; undo a hyphen split there.
    The page marker goes after the rejoined word (or at the start of the continuation)."""
    a = a.rstrip()
    m = re.search(r'([A-Za-zÄÖÜäöüß])-((?:</?\w+>)*)$', a)
    # "Problem- und Begriffsgeschichte": a real hyphen before a conjunction stays
    conj = re.match(r'(?:</?\w+>)*(und|oder|bzw|wie|als|sowie|noch)\b', b)
    if m and not conj and re.match(r'(?:</?\w+>)*[a-zäöüß]', b):
        left = a[:m.start() + 1]
        right = m.group(2) + b
        w = re.match(r'\S*', right).group(0)
        # don't leave the marker in front of trailing punctuation or a note reference
        w = re.match(r'(.*?)([.,;:!?)“‘\x00\d]*)$', w).group(1) if w else w
        joined = left + w + marker + right[len(w):]
        return re.sub(r'</(\w+)><\1>', '', joined), True   # "<g>Naturphiloso</g><g>phie</g>" -> one span
    return a + ' ' + marker + b, False

# ------------------------------------------------------------------ read pages into a block stream
def page_names():
    return ['r' + r for r in V['roman']] + ['p%03d' % n for n in range(1, V['last'] + 1)]

def label(name):
    return name[1:] if name.startswith('r') else str(int(name[1:]))

blocks = []          # dicts: kind in h1 h2 h3 h4 p quote break; text; notes (page-local refs resolved later)
notes = []           # global list of note texts, index = note id
missing = []
last_para = None     # block that a '+ ' continuation attaches to
last_note = None
for name in page_names():
    path = os.path.join(PROOF, name + '.md')
    if not os.path.exists(path):
        missing.append(name); last_para = last_note = None; continue
    text = open(path, encoding='utf-8').read().replace('\r\n', '\n').strip('\n')
    body, sep, foot = text.partition('\n---\n')
    if not sep and text.startswith('---\n'):
        body, foot = '', text[4:]
    pg = label(name)
    marker = '\x01%s\x01' % pg     # page-marker placeholder; becomes a span after escaping
    # notes of this page: printed number -> global id
    local = {}
    for line in [l for l in foot.split('\n') if l.strip()]:
        m = re.match(r'\[\^(\+|\d+)\]\s*(.*)$', line)
        if not m:
            if last_note is not None:
                notes[last_note] += ' ' + line.strip()
            else:
                warn(name, 'stray footnote line', line[:60])
            continue
        if m.group(1) == '+':
            if last_note is None:
                warn(name, 'note continuation without a previous note'); notes.append(m.group(2)); last_note = len(notes) - 1
            else:
                notes[last_note] = join(notes[last_note], m.group(2))[0]
        else:
            notes.append(m.group(2)); last_note = len(notes) - 1
            if m.group(1) in local: warn(name, 'duplicate note', m.group(1))
            local[m.group(1)] = last_note
    used = set()
    def ref(m):
        n = m.group(1)
        if n not in local:
            warn(name, 'reference without note', n); return ''
        used.add(n)
        return '\x00%d\x00' % local[n]
    first = True
    for raw in [b for b in re.split(r'\n\s*\n', body) if b.strip()]:
        raw = ' '.join(l.strip() for l in raw.split('\n'))
        raw = re.sub(r'\[\^(\d+)\]', ref, raw)
        mk = marker if first else ''
        if first and raw.startswith('+ '):
            raw = raw[2:]
            if last_para is None:
                warn(name, 'continuation without a previous paragraph')
                blocks.append({'kind': 'p', 'text': mk + raw}); last_para = blocks[-1]
            else:
                last_para['text'] = join(last_para['text'], raw, mk)[0]
            first = False
            continue
        if raw.startswith('+ '):
            warn(name, "'+' marker not on the first block"); raw = raw[2:]
        m = re.match(r'(#{1,4}) (.*)$', raw)
        if m:
            blocks.append({'kind': 'h%d' % len(m.group(1)), 'text': m.group(2).strip(), 'marker': mk})
            last_para = None
        elif raw == '***':
            blocks.append({'kind': 'break', 'text': mk}); last_para = None
        elif raw.startswith('> '):
            blocks.append({'kind': 'quote', 'text': mk + raw[2:]}); last_para = blocks[-1]
        else:
            blocks.append({'kind': 'p', 'text': mk + raw}); last_para = blocks[-1]
        first = False
    if first:   # page had no body text (e.g. only notes): keep the page marker
        blocks.append({'kind': 'marker', 'text': marker})
    for n in local:
        if n not in used:
            # the print has a note but no reference mark: keep the note, with a marked reference at the
            # end of the page's text (class "orphan"), rather than inventing a position in the sentence
            warn(name, 'note without reference (kept, marked at page end)', n)
            target = last_para if last_para is not None else (blocks[-1] if blocks else None)
            if target is not None:
                target['text'] = target['text'].rstrip() + '\x02%d\x02' % local[n]

# ------------------------------------------------------------------ cut into chapters
chapters = []
pending = []
for b in blocks:
    if b['kind'] == 'h2':
        if len(chapters) >= len(V['chapters']):
            warn('more ## headings than configured chapters:', b['text'][:60]); continue
        slug, book, num, title = V['chapters'][len(chapters)]
        first = [{'kind': 'marker', 'text': b.get('marker', '')}]
        squash = lambda s: re.sub(r'[\W_]+', '', s).lower()   # ignore case, punctuation, quote style
        if squash(b['text']) not in (squash(title), squash(num + title)):
            first.append({'kind': 'h3', 'text': b['text'], 'marker': ''})   # e.g. "Vorrede zur ersten Auflage."
        chapters.append({'slug': slug, 'book': book, 'num': num, 'title': title, 'blocks': pending + first, 'printed': b['text']})
        pending = []
    elif b['kind'] == 'h1':
        pending.append({'kind': 'marker', 'text': b.get('marker', '')})
    elif chapters and not pending:
        chapters[-1]['blocks'].append(b)
    else:
        pending.append(b)
if pending: warn('text before the first chapter heading dropped:', len(pending), 'blocks')

# ------------------------------------------------------------------ write HTML
def head(title, js=True):
    return ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>%s</title>\n<link rel="stylesheet" href="style.css">\n%s</head>\n<body>\n<div class="page">\n'
            % (html.escape(title), '<script src="reader.js" defer></script>\n' if js else ''))

def slugify(s):
    s = re.sub(r'<[^>]+>', '', s).lower()
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')):
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:60]

SECNUM = re.compile(r'^((?:[IVX]+|[A-Z]|\d+)\.|[A-Za-z]\))\s*(.*)$')
os.makedirs(OUT, exist_ok=True)
for f in os.listdir(OUT):
    if f.endswith('.html'): os.remove(os.path.join(OUT, f))
PB = lambda m: '<span class="pb" id="s-%s" data-p="%s" title="%s, S. %s"></span>' % (m.group(1), m.group(1), V['year'], m.group(1))
toc = []
for i, ch in enumerate(chapters):
    body, contents, ids = [], [], set()
    numbers = {}   # global note id -> chapter note number
    def refs(t):
        def r(m):
            g = int(m.group(2))
            if g not in numbers: numbers[g] = len(numbers) + 1
            n = numbers[g]
            if m.group(1) == '\x02':
                return ('<sup class="fn orphan" title="Verweiszeichen fehlt im Druck"><a href="#n%d" id="r%d">%d</a></sup>'
                        % (n, n, n))
            return '<sup class="fn"><a href="#n%d" id="r%d">%d</a></sup>' % (n, n, n)
        return re.sub('([\x00\x02])(\\d+)[\x00\x02]', r, t)
    carry = ''
    labels = list(V.get('labels', {}).get(ch['slug'], []))
    after_letter = False
    for b in ch['blocks']:
        k, t = b['kind'], b['text']
        if k == 'marker':
            carry += t; continue
        if k in ('h3', 'h4'):
            raw = t.rstrip('.') if not t.endswith('..') else t
            m = SECNUM.match(raw)
            if re.fullmatch(r'[IVX]+', raw):
                m = re.match(r'(.*)()$', raw + '.')
            num, title = (m.group(1), m.group(2)) if m else ('', raw)
            printed_title = title
            if num and not title:   # number only (e.g. "I."): label it from the table of contents
                if labels: title = labels.pop(0)
                else: warn(ch['slug'], 'no table-of-contents label for section', num)
            # depth: Roman numerals under a lettered part "A)" and a) b) c) are sub-sections
            if re.fullmatch(r'[IVX]+\.', num): depth = 1 if after_letter else 0
            elif re.fullmatch(r'[A-Z][.)]|\d+\.', num): after_letter = True; depth = 0   # Roman numerals after these nest
            elif re.fullmatch(r'[a-z]\)', num): depth = 1
            else: depth = 0
            if k == 'h4': depth = 1
            sid = slugify(num + ' ' + title) or 'abschnitt'
            while sid in ids: sid += '-x'
            ids.add(sid)
            tag, cls = ('h2', 'section') if k == 'h3' else ('h3', 'subsection')
            numhtml = '<span class="num">%s</span> ' % inline(num) if num else ''
            shown = inline(printed_title) if printed_title else '<span class="toc-label">%s</span>' % inline(title)
            body.append('<%s class="%s" id="%s">%s%s%s</%s>' % (tag, cls, sid, carry + b.get('marker', ''), numhtml, shown, tag))
            carry = ''
            contents.append(('h4' if depth else 'h3', sid, num, title))
            continue
        h = carry + refs(inline(t).replace('\x00', '\x00'))
        carry = ''
        if k == 'p': body.append('<p>%s</p>' % h)
        elif k == 'quote': body.append('<blockquote><p>%s</p></blockquote>' % h)
        elif k == 'break': body.append('<p class="center">%s* * *</p>' % h)
    if carry: body.append('<p>%s</p>' % carry)
    note_items = []
    for g, n in sorted(numbers.items(), key=lambda x: x[1]):
        note_items.append('<li id="n%d" value="%d">%s <a class="back" href="#r%d" aria-label="zurück zum Text">↩</a></li>'
                          % (n, n, re.sub('\x00\\d+\x00', '', inline(notes[g])), n))
    pages = re.findall('\x01([^\x01]+)\x01', '\n'.join(body))
    prev = (chapters[i - 1]['slug'] + '.html', chapters[i - 1]['title']) if i else ('index.html', 'Inhalt')
    nxt = (chapters[i + 1]['slug'] + '.html', chapters[i + 1]['title']) if i + 1 < len(chapters) else None
    out = [head('%s — %s' % (ch['title'], TITLE))]
    out.append('<nav class="topnav"><a href="index.html">← %s</a></nav>\n' % TITLE)
    out.append('<header class="chapter-head">')
    if ch['book']: out.append('<p class="part">%s</p>' % V['books'][ch['book']])
    if ch['num']: out.append('<p class="chapter-num">%s</p>' % ch['num'])
    out.append('<h1 class="chapter">\n  <span class="chapter-main">%s</span>\n</h1>\n</header>\n' % ch['title'])
    out.append('<nav class="chapter-contents" aria-label="In diesem Kapitel">\n<p class="label">In diesem Kapitel</p>\n<ol>')
    if not any(c[0] == 'h3' for c in contents):
        out.append('  <li><a href="#text"><span class="num">·</span> Text</a></li>')
    for k, sid, num, title in contents:
        out.append('  <li%s><a href="#%s"><span class="num">%s</span> %s</a></li>'
                   % (' class="sub"' if k == 'h4' else '', sid, inline(num) or '·', inline(title)))
    if note_items: out.append('  <li class="aux"><a href="#anmerkungen">Anmerkungen</a></li>')
    out.append('</ol>\n</nav>\n')
    out.append('<div class="chapter-text" id="text">\n' + '\n\n'.join(body) + '\n</div>\n')
    if note_items:
        out.append('<section class="notes" id="anmerkungen">\n<h2 id="notes-h">Anmerkungen</h2>\n<ol>\n%s\n</ol>\n</section>\n' % '\n'.join(note_items))
    nav = ['<nav class="topnav chapter-nav">', '<a class="prev" href="%s">← %s</a>' % prev]
    if nxt: nav.append('<a class="next" href="%s">%s →</a>' % nxt)
    out.append('\n'.join(nav + ['</nav>']) + '\n</div>\n</body>\n</html>\n')
    page_html = re.sub('\x01([^\x01]+)\x01', PB, '\n'.join(out))
    open(os.path.join(OUT, ch['slug'] + '.html'), 'w', encoding='utf-8', newline='\n').write(page_html)
    toc.append((ch, contents, pages))
    print('%-18s pages %s–%s  notes %d  sections %d' % (ch['slug'], pages[0] if pages else '?', pages[-1] if pages else '?', len(note_items), len(contents)))

# ------------------------------------------------------------------ index
ix = [head(TITLE, js=False), '<nav class="topnav"><a href="../bibliothek/">← Bibliothek</a></nav>\n',
      '<h1 class="book-title">%s</h1>' % BOOK, '<p class="subtitle">%s</p>' % SUB,
      '<p class="subtitle">%s</p>' % (V['band'] + (' · ' + V['band_sub'] if V.get('band_sub') else '')),
      '<p class="byline">%s</p>\n' % V['byline']]
def entry(ch, contents, pages):
    li = ['  <li>\n    <div class="entry">',
          '      <a href="%s.html">%s%s</a>' % (ch['slug'], '<span class="ch-num">%s</span>' % ch['num'] if ch['num'] else '', ch['title'])]
    secs = [c for c in contents if c[0] == 'h3']
    if secs:
        li.append('      <ol class="sections">')
        for k, sid, num, title in secs:
            li.append('        <li><span class="num">%s</span><a href="%s.html#%s">%s</a></li>' % (inline(num), ch['slug'], sid, inline(title)))
        li.append('      </ol>')
    li.append('    </div>')
    if pages: li.append('    <span class="range">S. %s–%s</span>' % (pages[0], pages[-1]))
    li.append('  </li>')
    return '\n'.join(li)
ix.append('<ol class="toc">\n%s\n</ol>\n' % '\n'.join(entry(*t) for t in toc if not t[0]['book']))
for bk, name in V['books'].items():
    items = [t for t in toc if t[0]['book'] == bk]
    if items:
        ix.append('<h2 class="toc-part">%s</h2>' % name)
        ix.append('<ol class="toc">\n%s\n</ol>\n' % '\n'.join(entry(*t) for t in items))
ix.append('</div>\n</body>\n</html>\n')
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8', newline='\n').write('\n'.join(ix))

# ------------------------------------------------------------------ shared assets
src = os.path.join(HERE, '..', '..', 'substanzbegriff', 'reader')
shutil.copyfile(os.path.join(src, 'style.css'), os.path.join(OUT, 'style.css'))
with open(os.path.join(OUT, 'style.css'), 'a', encoding='utf-8', newline='\n') as f:
    f.write('\n/* Erkenntnisproblem additions */\n'
            '.chapter-text blockquote { margin: 1.2rem 0 1.2rem 1.5rem; font-size: 0.94em; }\n'
            '.chapter-text blockquote p { text-indent: 0; }\n'
            '.unsure { border-bottom: 1px dotted var(--muted); }\n'
            'sup.fn.orphan { opacity: 0.55; }\n'
            '.pb::before { content: "|" attr(data-p); }\n')
js = open(os.path.join(src, 'reader.js'), encoding='utf-8').read()
js = js.replace("'<p class=\"label\"><a href=\"index.html\">Substanzbegriff und Funktionsbegriff</a> · '",
                "'<p class=\"label\"><a href=\"index.html\">' + document.querySelector('.topnav a').textContent.replace(/^← /, '') + '</a> · '")
if 'Substanzbegriff' in js: warn('reader.js still names Substanzbegriff')
open(os.path.join(OUT, 'reader.js'), 'w', encoding='utf-8', newline='\n').write(js)

if missing:
    runs, start = [], missing[0]
    for a, b in zip(missing, missing[1:] + [None]):
        if b is None or page_names().index(b) != page_names().index(a) + 1:
            runs.append(start if start == a else start + '–' + a); start = b
    print('missing pages:', len(missing), ' '.join(runs))
print('warnings:', len(warnings))
for w in warnings: print('  ', w)
