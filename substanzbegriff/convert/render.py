"""Stage 3: write the reader HTML from stage2.pkl."""
import pickle, re, sys, html, collections, os

S, OUT = sys.argv[1], sys.argv[2]
P = pickle.load(open(S + '/stage2.pkl', 'rb'))
os.makedirs(OUT, exist_ok=True)

ECW_O, ECW_C = '', ''
BAR = ''
NUM_O, NUM_C = '', ''
REF_O, REF_C = '', ''
ORIG_O, ORIG_C = '', ''
SP_O, SP_C = '', ''

BOOK = 'Substanzbegriff und Funktionsbegriff'
SUB = 'Untersuchungen über die Grundfragen der Erkenntniskritik'
PARTS = {1: 'Erster Teil · Dingbegriffe und Relationsbegriffe',
         2: 'Zweiter Teil · Das System der Relationsbegriffe und das Problem der Wirklichkeit'}

# ---------------------------------------------------------------- word-level OCR fixes
vocab = collections.Counter()
def plain(t): return re.sub('[-]', ' ', t)
for C in P:
    for p in C['paras']:
        if 'text' in p:
            for w in re.findall(r'[A-Za-zÄÖÜäöüß]+', plain(p['text'])): vocab[w.lower()] += 1
    for t in C['notes'].values():
        for w in re.findall(r'[A-Za-zÄÖÜäöüß]+', plain(t)): vocab[w.lower()] += 1

fixes = collections.Counter()
def fix_token(m):
    w = m.group(0)
    if not re.search(r'[A-Za-zäöüß]', w) or not re.search(r'[01]', w): return w
    if re.fullmatch(r'[A-Za-z]\d+', w): return w          # E1, x2, t1 ...
    v = w.replace('1', 'l').replace('0', 'o')
    if vocab[v.lower()] >= 2:
        fixes[w + ' -> ' + v] += 1
        return v
    return w
def fix_words(t):
    t = re.sub(r'[A-Za-zÄÖÜäöüß01]{3,}', fix_token, t)
    # "Mi 11" style splits of a known name
    def two(m):
        j = (m.group(1) + m.group(2)).replace('1', 'l')
        if vocab[j.lower()] >= 3 and vocab[m.group(1).lower()] < 2:
            fixes[m.group(0) + ' -> ' + j] += 1
            return j
        return m.group(0)
    t = re.sub(r'\b([A-Z][a-zäöü]{1,5}) ([1l]{1,2}[a-z]*)\b', two, t)
    return t

# ---------------------------------------------------------------- to HTML
def to_html(t, chapter_refs, in_note=False):
    t = fix_words(t)
    t = t.replace('\xad', '')
    t = html.escape(t, quote=False)
    t = re.sub(r'(?<=\s)-(?=\s)', '–', t)                       # Gedankenstrich
    t = re.sub(r'(?<=\s)-(?=[-])', '–', t)
    # dash glued to the preceding word by OCR ("wird- die"), or a hyphenation the line join missed
    def glued(m):
        a, b = m.group(1), m.group(2)
        if b in ('und', 'oder', 'bzw', 'wie', 'als', 'sowie'): return m.group(0)
        if vocab[(a + b).lower()] >= 1 or (vocab[b.lower()] < 2 and vocab[a.lower()] < 2):
            return a + b
        return a + ' – ' + b
    t = re.sub(r'([A-Za-zÄÖÜäöüß]{2,})- ([a-zäöüß]{2,})', glued, t)
    t = re.sub(r'(?<![\w])!(?=[a-zéè\'’])', 'l', t)                  # French "!es" -> "les"
    def ref(m):
        n = m.group(1)
        chapter_refs.add(int(n))
        return '<sup class="fn"><a href="#n%s" id="r%s">%s</a></sup>' % (n, n, n)
    t = re.sub(REF_O + r'(\d+)' + REF_C, ref, t)
    t = re.sub(ECW_O + r'([^' + ECW_C + r']*)' + ECW_C,
               lambda m: '<span class="pg" id="ecw-%s" data-p="%s" title="ECW 6, S. %s"></span>' % (m.group(1), m.group(1), m.group(1)), t)
    def orig(m):
        p = m.group(1)
        if p in USED_ORIG: return ''      # a misplaced duplicate break: drop it
        USED_ORIG.add(p)
        return '<span class="pb" id="s-%s" data-p="%s" title="1910, S. %s"></span>' % (p, p, p)
    t = re.sub(ORIG_O + r'([^' + ORIG_C + r']*)' + ORIG_C, orig, t)
    t = re.sub(NUM_O + r'(\d+)' + NUM_C, r'\1', t)
    t = t.replace(BAR, '')
    t = t.replace(SP_O, '<span class="sp">').replace(SP_C, '</span>')
    t = re.sub(r'[-]', '', t)
    t = re.sub(r'[ \t]{2,}', ' ', t)
    t = re.sub(r' +([,.;:])(?=\s|$)', r'\1', t) if in_note else t
    return t.strip()

def head(title, js=True):
    return ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<title>%s</title>\n<link rel="stylesheet" href="style.css">\n%s</head>\n<body>\n<div class="page">\n'
            % (html.escape(title), '<script src="reader.js" defer></script>\n' if js else ''))

# ---------------------------------------------------------------- hand corrections (checked against the scan)
import glob as _glob, json as _json
CORR_DIR = os.path.join(os.path.dirname(os.path.normpath(OUT)), 'convert', 'corrections')
CORRECTIONS = []
for _f in sorted(_glob.glob(os.path.join(CORR_DIR, '*.json'))):
    CORRECTIONS += _json.load(open(_f, encoding='utf-8'))
CORR_PROBLEMS = []
def apply_corrections(name, text):
    for c in CORRECTIONS:
        if c['file'] != name: continue
        n = text.count(c['old'])
        if n != 1:
            CORR_PROBLEMS.append('%s: %d matches for %r' % (name, n, c['old'][:80]))
            continue
        text = text.replace(c['old'], c['new'])
    return global_fixes(text)

# ---------------------------------------------------------------- book-wide OCR patterns (after hand corrections)
SZ = collections.Counter()
def sz_fix(m):
    w = m.group(0)
    if vocab[w.lower()] > 2: return w
    rules = [('fü', 'ß'), ('fs', 'ß'), ('fi', 'ß')]
    if not re.search(r'gen?$', w): rules.append(('g', 'ß'))   # "liege" is a real word
    for a, b in rules:
        for i in [k for k in range(len(w)) if w.startswith(a, k)]:
            v = w[:i] + b + w[i + len(a):]
            if vocab[v.lower()] >= 3:
                SZ[w + ' -> ' + v] += 1
                return v
    return w
def text_fixes(t):
    t = re.sub(r'»\s+(?=\S)', '»', t)
    t = re.sub(r'(?<=\S)\s+«', '«', t)
    t = re.sub(r'(?<=[A-Za-zÄÖÜäöüß,;:])»(?=\w)', ' »', t)
    t = re.sub(r'\[\s*\.\s*\.\s*\.\s*\]', '[…]', t)
    for a, b in (('dag', 'daß'), ('Dag', 'Daß'), ('lägt', 'läßt'), ('wißen', 'wissen'), ('CEuvres', 'Œuvres'), ('Rene', 'René'), ('Gewigheit', 'Gewißheit'), ('Thc', 'The')):
        t = re.sub(r'(?<![\w])' + a + r'(?![\w])', b, t)
    t = re.sub(r'(?<![\w])([A-Za-zÄÖÜäöüß]+)fü(?![\w])', lambda m: m.group(1) + 'ßt' if vocab[(m.group(1) + 'ßt').lower()] >= 2 else m.group(0), t)
    t = re.sub(r'\b([Aa])\. a\. 0\.', r'\1. a. O.', t)
    t = re.sub(r'\b([Aa])\.a\.0\.', r'\1.a.O.', t)
    t = re.sub(r'&gt;(\S[^&<]{0,80}?\S|\S)&lt;', r'›\1‹', t)
    t = re.sub(r'[A-Za-zÄÖÜäöüß]*(?:fü|g|h|fs|fi)[A-Za-zÄÖÜäöüß]*', sz_fix, t)
    return t
JOINS = collections.Counter()
def join_across_marker(m):
    a, mk, b = m.group(1), m.group(2), m.group(3)
    if b in ('und', 'oder', 'bzw', 'wie', 'als', 'sowie'):
        return m.group(0)                       # "Raum- und Zeitbegriff"
    cands = [(a, b)]
    for x, y in (('eh', 'ch'), ('sehen', 'schen'), ('dem', 'dern'), ('lieh', 'lich'), ('rn', 'm'), ('m', 'rn')):
        if x in b: cands.append((a, b.replace(x, y, 1)))
    for x, y in (('mem', 'mein'), ('gemem', 'gemein'), ('Sehe', 'Sche')):
        if a.endswith(x): cands.append((a[:-len(x)] + y, b))
    for ca, cb in cands:
        if vocab[(ca + cb).lower()] >= 1:
            JOINS[a + '-|' + b + ' -> ' + ca + cb] += 1
            return ca + mk + cb
    JOINS[a + '-|' + b + ' -> ' + a + b + ' (unknown)'] += 1
    return a + mk + b
def global_fixes(page):
    # only touch text between tags, and leave <head> alone
    head, sep, body = page.partition('<body>')
    body = re.sub(r'([A-Za-zÄÖÜäöüß]+)- *((?:<span class="p[gb]"[^>]*></span>)+) *([a-zäöüß]+)', join_across_marker, body)
    parts = re.split(r'(<[^>]+>)', body)
    parts = [p if p.startswith('<') else text_fixes(p) for p in parts]
    return head + sep + ''.join(parts)

order = [C['ch'] for C in P]
def chapter_link(i):
    ch = order[i]
    return '%s.html' % ch['slug'], (ch['num'] + ' · ' if ch['num'] else '') + ch['title']

stats = []
USED_ORIG = set()
for i, C in enumerate(P):
    ch = C['ch']
    refs = set()
    body = []
    sec_ids = []
    first_page = None
    for p in C['paras']:
        if p['kind'] == 'h':
            sid = 'abschnitt-' + p['text']
            sec_ids.append((sid, p['text']))
            body.append('<h2 class="section" id="%s"><span class="num">%s.</span></h2>' % (sid, p['text']))
        elif p['kind'] == 'c':
            h = to_html(p['text'], refs)
            if h: body.append('<p class="center">%s</p>' % h)
        else:
            h = to_html(p['text'], refs)
            if not re.sub(r'<span class="p[gb]"[^>]*></span>', '', h).strip():
                # paragraph holding only a page marker: attach to next paragraph
                body.append(('MARKERS', h))
                continue
            body.append('<p>%s</p>' % h)
    # merge marker-only paragraphs into the following one
    merged = []
    pending = ''
    for b in body:
        if isinstance(b, tuple):
            pending += b[1]; continue
        if pending and b.startswith('<p'):
            b = re.sub(r'^(<p[^>]*>)', lambda m: m.group(1) + pending, b, count=1); pending = ''
        elif pending and b.startswith('<h2'):
            b = b + '\n<!-- -->'; b = b.replace('<!-- -->', '')
            merged.append(b); continue
        merged.append(b)
    if pending: merged.append('<p>%s</p>' % pending)
    body = merged

    notes_html = []
    for n, t in C['notes'].items():
        back = ' <a class="back" href="#r%d" aria-label="zurück zum Text">↩</a>' % n if n in refs else ''
        notes_html.append('<li id="n%d" value="%d">%s%s</li>' % (n, n, to_html(t, set(), True), back))
    stats.append((ch['slug'], len(C['notes']), len(refs)))

    prev_link = chapter_link(i - 1) if i > 0 else ('index.html', 'Inhalt')
    next_link = chapter_link(i + 1) if i + 1 < len(P) else None
    out = [head('%s — %s' % (ch['title'], BOOK))]
    out.append('<nav class="topnav"><a href="index.html">← %s</a></nav>\n' % BOOK)
    out.append('<header class="chapter-head">')
    if ch['part']: out.append('<p class="part">%s</p>' % PARTS[ch['part']])
    if ch['num']: out.append('<p class="chapter-num">%s</p>' % ch['num'])
    out.append('<h1 class="chapter">\n  <span class="chapter-main">%s</span>\n</h1>\n</header>\n' % ch['title'])
    out.append('<nav class="chapter-contents" aria-label="In diesem Kapitel">\n<p class="label">In diesem Kapitel</p>\n<ol>')
    if not sec_ids:
        out.append('  <li><a href="#text"><span class="num">·</span> Text</a></li>')
    for sid, num in sec_ids:
        out.append('  <li><a href="#%s"><span class="num">%s.</span> Abschnitt %s</a></li>' % (sid, num, num))
    if notes_html:
        out.append('  <li class="aux"><a href="#anmerkungen">Anmerkungen</a></li>')
    out.append('</ol>\n</nav>\n')
    out.append('<div class="chapter-text" id="text">\n')
    out.append('\n\n'.join(body))
    out.append('\n</div>\n')
    if notes_html:
        out.append('<section class="notes" id="anmerkungen">\n<h2 id="notes-h">Anmerkungen</h2>\n<ol>\n%s\n</ol>\n</section>\n' % '\n'.join(notes_html))
    nav = ['<nav class="topnav chapter-nav">']
    nav.append('<a class="prev" href="%s">← %s</a>' % prev_link)
    if next_link: nav.append('<a class="next" href="%s">%s →</a>' % next_link)
    nav.append('</nav>')
    out.append('\n'.join(nav) + '\n')
    out.append('</div>\n</body>\n</html>\n')
    page_html = apply_corrections(ch['slug'] + '.html', '\n'.join(out))
    open(os.path.join(OUT, ch['slug'] + '.html'), 'w', encoding='utf-8', newline='\n').write(page_html)

# ---------------------------------------------------------------- index
ix = [head(BOOK, js=False)]
ix.append('<nav class="topnav"><a href="../bibliothek/">← Bibliothek</a></nav>\n')
ix.append('<h1 class="book-title">%s</h1>' % BOOK)
ix.append('<p class="subtitle">%s</p>' % SUB)
ix.append('<p class="byline">Ernst Cassirer · Berlin 1910</p>\n')
def entry(ch, idx):
    C = P[idx]
    secs = [p['text'] for p in C['paras'] if p['kind'] == 'h']
    li = ['  <li>\n    <div class="entry">']
    li.append('      <a href="%s.html">%s%s</a>' % (ch['slug'], '<span class="ch-num">%s</span>' % ch['num'] if ch['num'] else '', ch['title']))
    if secs:
        li.append('      <ol class="sections">')
        for s in secs:
            li.append('        <li><span class="num">%s.</span><a href="%s.html#abschnitt-%s">Abschnitt %s</a></li>' % (s, ch['slug'], s, s))
        li.append('      </ol>')
    li.append('    </div>')
    # page range (ECW)
    pages = [m for p in C['paras'] if 'text' in p for m in re.findall(ECW_O + r'([^' + ECW_C + r']*)' + ECW_C, p['text'])]
    if pages:
        li.append('    <span class="range">S. %s–%s</span>' % (pages[0], pages[-1]))
    li.append('  </li>')
    return '\n'.join(li)
ix.append('<ol class="toc">\n%s\n</ol>\n' % entry(order[0], 0))
for part in (1, 2):
    ix.append('<h2 class="toc-part">%s</h2>' % PARTS[part])
    ix.append('<ol class="toc">\n%s\n</ol>\n' % '\n'.join(entry(ch, k) for k, ch in enumerate(order) if ch['part'] == part))
ix.append('''</div>
</body>
</html>
''')
open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8', newline='\n').write('\n'.join(ix))

open(S + '/fixes.log', 'w', encoding='utf-8').write('\n'.join('%d %s' % (v, k) for k, v in fixes.most_common()))
for s in stats: print(*s)
print('word fixes', sum(fixes.values()))
print('corrections', len(CORRECTIONS), 'problems', len(CORR_PROBLEMS))
for p in CORR_PROBLEMS: print('  ', p)
print('ß fixes', sum(SZ.values()), 'page-break joins', sum(JOINS.values()))
open(S + '/joins.log', 'w', encoding='utf-8').write('\n'.join(sorted(JOINS)))
open(S + '/szfixes.log', 'w', encoding='utf-8').write('\n'.join('%d %s' % (v, k) for k, v in SZ.most_common()))
