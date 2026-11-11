"""Stage 1: turn positioned PDF text segments into a token stream per chapter.

Output: stream.pkl = list of chapters, each a list of items:
  ('h', level, text)           heading
  ('p', [tokens])              paragraph
tokens: ('t', text) | ('ref', n) | ('ecw', label) | ('orig', label) | ('bar',)
plus notes: dict n -> [tokens]
and a log of anomalies.
"""
import pickle, re, sys, collections

S = sys.argv[1]
pages = pickle.load(open(S + '/segs.pkl', 'rb'))

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII']
def roman_to_int(s):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
    t = 0
    for i, c in enumerate(s):
        v = vals[c]
        if i + 1 < len(s) and vals[s[i + 1]] > v: t -= v
        else: t += v
    return t
def int_to_roman(n):
    out = ''
    for v, r in ((10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v: out += r; n -= v
    return out

# Chapter structure from the table of contents (ECW page numbers).
CHAPTERS = [
    dict(slug='vorwort', num='', title='Vorwort', part=None, start='VII', sections=[]),
    dict(slug='kapitel-1', num='Erstes Kapitel', title='Zur Theorie der Begriffsbildung', part=1, start=1, sections=[]),
    dict(slug='kapitel-2', num='Zweites Kapitel', title='Die Zahlbegriffe', part=1, start=27, sections=[27, 36, 45, 56]),
    dict(slug='kapitel-3', num='Drittes Kapitel', title='Der Raumbegriff und die Geometrie', part=1, start=71, sections=[71, 80, 97, 107]),
    dict(slug='kapitel-4', num='Viertes Kapitel', title='Die naturwissenschaftliche Begriffsbildung', part=1, start=121, sections=[121, 124, 141, 150, 163, 184, 204, 222, 240]),
    dict(slug='kapitel-5', num='Fünftes Kapitel', title='Zum Problem der Induktion', part=2, start=255, sections=[255, 272, 286]),
    dict(slug='kapitel-6', num='Sechstes Kapitel', title='Der Begriff der Wirklichkeit', part=2, start=292, sections=[292, 309, 316, 327]),
    dict(slug='kapitel-7', num='Siebentes Kapitel', title='Subjektivität und Objektivität der Relationsbegriffe', part=2, start=334, sections=[]),
    dict(slug='kapitel-8', num='Achtes Kapitel', title='Zur Psychologie der Relationen', part=2, start=353, sections=[353, 365]),
]
CHAPTER_STARTS = {c['start'] for c in CHAPTERS}

log = []
def warn(*a):
    log.append(' '.join(str(x) for x in a))

SMALL = 8.0
BARLIKE = re.compile(r'^[1Il|/!]$')

def ecw_label(pdf):
    if pdf <= 10: return int_to_roman(pdf - 1)  # pdf 8 -> VII
    return pdf - 11

def lines_of(pdf):
    segs = sorted(pages[pdf], key=lambda s: (-s[1], s[0]))
    lines = []
    for s in segs:
        if lines and abs(lines[-1]['y'] - s[1]) < 3:
            lines[-1]['segs'].append(s)
        else:
            lines.append({'y': s[1], 'segs': [s]})
    for L in lines:
        L['segs'].sort(key=lambda s: s[0])
        L['x'] = L['segs'][0][0]
        big = [max(s[2], s[3]) if False else s[3] for s in L['segs'] if len(s[4].strip()) > 2]
        L['size'] = max(big) if big else max(s[3] for s in L['segs'])
        L['text'] = ''.join(s[4] for s in L['segs']).replace('\n', ' ')
    return lines

def parse_header(L, ecw):
    """Return the original (1910) page label at the top of this page and whether a range was given."""
    t = L['text'].strip()
    t = re.sub(r'\s+', ' ', t)
    m = re.search(r'\[?([0-9]+|[IVX]+)\]?\s*[-~–]\s*([0-9]+|[IVX]+)', t)
    if m:
        a, b = m.group(1), m.group(2)
        bracket = '[' in t[:m.end()]
        return a, b, bracket
    nums = re.findall(r'\b([0-9]+|[IVX]+)\b', t)
    others = [n for n in nums if n != str(ecw)]
    if others:
        return others[-1], others[-1], False
    warn('header?', ecw, t)
    return None, None, False

def seg_tokens(L, in_notes):
    """Convert a line's segments into raw tokens. Small numeric segments become markers."""
    out = []
    for s in L['segs']:
        txt = s[4].replace('\n', ' ')
        small = s[3] < SMALL and s[2] < SMALL + 1
        st = txt.strip()
        if small and re.fullmatch(r'\d{1,3}', st):
            out.append(('num', int(st), txt))
        elif small and BARLIKE.match(st):
            out.append(('bar',))
            if txt.endswith(' '): out.append(('t', ' '))
        else:
            out.append(('t', txt))
    return out

chapters = []
notes = {}
note_pages = {}
cur = None
next_note = 1
orig_expect = {}

for pdf in list(range(8, 11)) + list(range(12, 386)):
    ecw = ecw_label(pdf)
    lines = lines_of(pdf)
    if not lines: continue
    # header: top line(s) at y >= 615
    head = [L for L in lines if L['y'] >= 615]
    lines = [L for L in lines if L['y'] < 615]
    o_start, o_end, bracket = parse_header({'text': ' '.join(h['text'] for h in head)}, ecw)
    if o_start is None:
        o_s = o_e = prev_end; roman = prev_roman; bracket = False
        warn('no 1910 range on page', ecw, '-> assuming', o_s)
    else:
        roman = not o_start.isdigit()
        o_s = roman_to_int(o_start) if roman else int(o_start)
        o_e = roman_to_int(o_end) if roman else int(o_end)
    prev_end, prev_roman = o_e, roman
    orig_expect[ecw] = (o_s, o_e, bracket, roman)

    is_start = ecw in CHAPTER_STARTS
    if is_start:
        ch = next(c for c in CHAPTERS if c['start'] == ecw)
        cur = dict(ch, items=[])
        chapters.append(cur)
        # drop the heading block: everything before the first long line
        xs = sorted(L['x'] for L in lines if len(L['text'].strip()) >= 45); bm = xs[len(xs)//2]
        k = 0
        while k < len(lines) and (lines[k]['x'] - bm > 15 or len(lines[k]['text'].strip()) < 20):
            k += 1
        dropped = ' / '.join(l['text'].strip() for l in lines[:k])
        warn('chapter head dropped', ecw, ':', dropped)
        lines = lines[k:]
        para_break_first = True
    else:
        para_break_first = False

    # split into body and notes: notes are a trailing run of smaller lines
    # (single OCR lines can carry odd scale factors, so use a majority rule)
    split = len(lines)
    for i, L in enumerate(lines):
        if L['size'] < 9.7:
            rest = lines[i:]
            small = sum(1 for R in rest if R['size'] < 9.7)
            if small / len(rest) >= 0.6:
                split = i
                break
    body_lines = lines[:split]
    note_lines = lines[split:]
    for R in note_lines:
        if R['size'] >= 9.7: warn('large line in notes', ecw, R['text'][:50])
    # sanity: a note region should start with a number or be a continuation
    margin = min((L['x'] for L in body_lines), default=0)
    # section heading lines inside body (roman numeral alone)
    if cur['sections'] and ecw in cur['sections']:
        sec_idx = cur['sections'].index(ecw)
        want = ROMAN[sec_idx]
        found = False
        for i, L in enumerate(body_lines):
            t = L['text'].strip().rstrip('.').strip()
            if re.fullmatch(r'[IVX/l1]+', t) and (L['x'] - margin) > 40:
                body_lines[i] = {'heading': want}
                found = True
                break
        if not found and is_start:
            found = True  # numeral was part of the dropped chapter head
            cur['items'].append(('h', 2, want))
        if not found:
            warn('section numeral not found', ecw, want)

    cur['items'].append(('ecw', ecw, o_s, roman))
    first = True
    for L in body_lines:
        if 'heading' in L:
            cur['items'].append(('h', 2, L['heading']))
            first = True
            para_break_first = True
            continue
        indent = L['x'] - margin
        text_strip = L['text'].strip()
        new_para = (indent > 5 and indent < 60) or (first and para_break_first)
        if indent >= 60 and len(text_strip) < 40:
            # centered short line inside body (signature, formula, heading-like)
            cur['items'].append(('centered', seg_tokens(L, False)))
            continue
        cur['items'].append(('line', new_para, seg_tokens(L, False)))
        first = False
        para_break_first = False

    # notes
    for L in note_lines:
        toks = seg_tokens(L, True)
        cur['items'].append(('noteline', toks, ecw))

pickle.dump({'chapters': chapters, 'orig': orig_expect}, open(S + '/stage1.pkl', 'wb'))
open(S + '/stage1.log', 'w', encoding='utf-8').write('\n'.join(log))
print(len(chapters), 'chapters;', len(log), 'log lines')
