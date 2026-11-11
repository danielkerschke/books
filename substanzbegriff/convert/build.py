"""Stage 2: assemble paragraphs and notes, repair OCR, write HTML chapters."""
import pickle, re, sys, html, collections, json

S = sys.argv[1]
OUT = sys.argv[2]
d = pickle.load(open(S + '/stage1.pkl', 'rb'))
chapters = d['chapters']
orig = d['orig']

def int_to_roman(n):
    out = ''
    for v, r in ((10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v: out += r; n -= v
    return out

log = []
def warn(*a): log.append(' '.join(str(x) for x in a))

# Private-use markers inside working strings
ECW_O, ECW_C = '', ''      # ECW page start  LABEL
BAR = ''                          # small bar-like segment
NUM_O, NUM_C = '', ''      # small number segment
REF_O, REF_C = '', ''      # resolved footnote ref
ORIG_O, ORIG_C = '', ''    # resolved 1910 page break
SP_O, SP_C = '', ''        # letter-spaced emphasis
MARK = re.compile('[-]')

def tok_str(toks):
    out = []
    for t in toks:
        if t[0] == 't': out.append(t[1])
        elif t[0] == 'num': out.append(NUM_O + str(t[1]) + NUM_C + (' ' if t[2].endswith(' ') else ''))
        elif t[0] == 'bar': out.append(BAR)
    return ''.join(out)

CONJ = {'und', 'oder', 'bzw', 'wie', 'als', 'sowie', 'noch', 'bis'}

def join_lines(parts):
    """Join line strings, undoing hyphenation. Markers that land inside a word are moved to its end."""
    text = ''
    for s in parts:
        s = s.replace('\n', ' ')
        if not text:
            text = s.lstrip(); continue
        t = text.rstrip(' ')
        nxt = s.lstrip()
        # strip leading markers of the next line to inspect its first word
        lead = ''
        while nxt and MARK.match(nxt[0]):
            m = re.match('(' + ECW_O + '[^' + ECW_C + ']*' + ECW_C + '|' + NUM_O + r'\d+' + NUM_C + '|' + BAR + r')\s*', nxt)
            if not m: break
            lead += m.group(1); nxt = nxt[m.end():]
        first_word = re.match(r'[^\s]*', nxt).group(0)
        if t.endswith('\xad'):
            t = t[:-1]
            if lead:
                # move markers after the joined word
                w = re.match(r'[^\s]*', nxt).group(0)
                text = t + w + lead + nxt[len(w):]
            else:
                text = t + nxt
        elif t.endswith('-') and len(t) > 1 and t[-2].isalpha() and first_word[:1].islower() and first_word.strip('.,;:') not in CONJ:
            t = t[:-1]
            w = first_word
            text = t + w + lead + nxt[len(w):]
        else:
            text = t + ' ' + lead + nxt
    return text

AMBIG = {'s': '58', 'S': '58', 'o': '0', 'O': '0', '°': '0', 'l': '1', 'I': '1', 't': '1', 'i': '1', 'B': '8', 'g': '9'}
def fuzzy_numbers(tok):
    outs = ['']
    for c in tok:
        opts = c if c.isdigit() else AMBIG.get(c, '')
        if not opts: return []
        outs = [o + d for o in outs for d in opts]
    return [int(o) for o in outs]

# ---------------------------------------------------------------- assemble
parts_by_ch = []
note_ctr = 0
for ch in chapters:
    if ch['slug'] == 'kapitel-5':
        note_ctr = 0  # Part Two restarts note numbering
    paras = []            # list of dict(kind, lines)
    notes = collections.OrderedDict()   # n -> list of line strings
    note_page = {}
    cur_note = None
    page = None
    for it in ch['items']:
        k = it[0]
        if k == 'ecw':
            page = it[1]
            marker = ECW_O + str(page) + ECW_C
            if paras and paras[-1]['kind'] == 'p':
                paras[-1]['lines'].append(marker)
            else:
                paras.append({'kind': 'p', 'lines': [marker], 'cont': True})
        elif k == 'h':
            paras.append({'kind': 'h', 'text': it[2]})
        elif k == 'centered':
            paras.append({'kind': 'c', 'lines': [tok_str(it[1])]})
        elif k == 'line':
            s = tok_str(it[2])
            if it[1]:
                # new paragraph; if the previous paragraph holds only a page marker, merge into it
                if paras and paras[-1]['kind'] == 'p' and all(re.fullmatch(ECW_O + '[^' + ECW_C + ']*' + ECW_C, l) for l in paras[-1]['lines']):
                    paras[-1]['lines'].append(s)
                else:
                    paras.append({'kind': 'p', 'lines': [s]})
            else:
                if not paras or paras[-1]['kind'] != 'p':
                    paras.append({'kind': 'p', 'lines': []})
                paras[-1]['lines'].append(s)
        elif k == 'noteline':
            s = tok_str(it[1])
            cands = []
            for m in re.finditer(NUM_O + r'(\d+)' + NUM_C + r'\s*', s):
                before = s[:m.start()]
                if before.strip() == '' or re.search(r'(?:[\.\]\)\:]|ff\.)\s*$', before):
                    cands.append((m.start(), m.end(), int(m.group(1)), 'small'))
            m = re.match(r'^(\s*)([0-9soOlIStiBg°]{1,3})\s+(?=[A-ZÄÖÜa-z\[\(»„"])', s)
            if m and not any(c[0] <= len(m.group(1)) for c in cands):
                readings = fuzzy_numbers(m.group(2))
                pick = [r for r in readings if r in (note_ctr + 1, note_ctr + 2)]
                if pick:
                    if not m.group(2).isdigit(): warn('fuzzy note number', repr(m.group(2)), '->', pick[0])
                    cands.append((m.start(2), m.end(), pick[0], 'start'))
            for m in re.finditer(r'(?:(?<=[\.\]\)\:] )|(?<=ff\. ))(\d{1,3})\s+(?=[A-ZÄÖÜ\[\(»„])', s):
                cands.append((m.start(1), m.end(), int(m.group(1)), 'mid'))
            cands.sort()
            pos = 0
            for st, en, v, kind in cands:
                if st < pos: continue
                exp = note_ctr + 1
                if kind == 'small':
                    n = v if v in (exp, exp + 1) else exp
                    if v != n: warn('small note number misread', ch['slug'], page, v, '->', n)
                elif v in (exp, exp + 1):
                    n = v
                else:
                    continue
                if n != exp: warn('note number skipped', ch['slug'], 'expected', exp, 'got', n, 'page', page)
                if s[pos:st].strip():
                    if cur_note is None: warn('orphan note text', ch['slug'], page, s[pos:st][:60])
                    else: notes[cur_note].append(s[pos:st])
                note_ctr = cur_note = n
                notes[n] = []
                note_page[n] = page
                pos = en
            if s[pos:].strip():
                if cur_note is None: warn('orphan note text', ch['slug'], page, s[pos:][:60])
                else: notes[cur_note].append(s[pos:])
    for p in paras:
        if p['kind'] in ('p', 'c'):
            p['text'] = join_lines(p['lines'])
    notes_text = collections.OrderedDict((n, join_lines(v)) for n, v in notes.items())
    parts_by_ch.append({'ch': ch, 'paras': paras, 'notes': notes_text, 'note_page': note_page})

# ---------------------------------------------------------------- footnote refs
for C in parts_by_ch:
    paras = [p for p in C['paras'] if p['kind'] in ('p', 'c')]
    # concatenate body with paragraph separators to search page-wise
    SEP = ''
    body = SEP.join(p['text'] for p in paras)
    def page_span(label):
        a = body.find(ECW_O + str(label) + ECW_C)
        if a < 0: return None
        b = body.find(ECW_O, a + 1)
        return a, (b if b >= 0 else len(body))
    cursor = 0
    for n, page in C['note_page'].items():
        span = page_span(page)
        if not span:
            warn('no page span', C['ch']['slug'], n, page); continue
        lo = max(span[0], cursor)
        hi = span[1]
        # the reference may sit a little before the page break on the previous page if a line straddles
        cands = []
        # OCR variants of the number, e.g. "1s4" for 154
        alts = {str(n)}
        for m in re.finditer(r'(?<![\w])[0-9soOlIStiBg°]{%d}(?![\w])' % len(str(n)), body[lo:hi]):
            tokf = m.group(0)
            if not tokf.isdigit() and re.search(r'\d', tokf) and n in fuzzy_numbers(tokf):
                alts.add(re.escape(tokf))
        num = '(?:' + '|'.join(sorted(alts)) + ')'
        for pat, prio in ((NUM_O + str(n) + NUM_C, 0),
                          (r'(?<=[A-Za-zäöüßÄÖÜ\.\,\;\:\!\?»«\)\]\-–])' + num + r'(?=[\s\.\,\;\:\)-' + SEP + r']|$)', 1),
                          (r'(?<=\s)' + num + r'(?=[\s\)-' + SEP + r']|$)', 2)):
            for m in re.finditer(pat, body[lo:hi]):
                cands.append((m.start() + lo, prio, m.end() + lo))
        if not cands:
            warn('ref not found', C['ch']['slug'], 'note', n, 'page', page)
            continue
        cands.sort(key=lambda c: (c[0], c[1]))
        # prefer an exact small-number marker if present
        small = [c for c in cands if c[1] == 0]
        st, prio, en = small[0] if small else cands[0]
        rep = REF_O + str(n) + REF_C
        # remove a single space before a standalone number
        if prio == 2 and st > 0 and body[st - 1] == ' ':
            st -= 1
        if prio == 0 and en < len(body) and body[en] == ' ' and st > 0 and body[st - 1] == ' ':
            en += 1
        body = body[:st] + rep + body[en:]
        cursor = st + len(rep)
    texts = body.split(SEP)
    for p, t in zip(paras, texts): p['text'] = t

# ---------------------------------------------------------------- letter-spaced repair
FUNC = set('''der die das des dem den ein eine einer eines einem einen und oder aber als wie so ob es er sie wir ihr ich du man
in im an am auf aus bei mit nach von vom zu zum zur um für durch über unter vor hinter neben zwischen gegen ohne
ist sind war sein hat haben wird werden kann muß soll will nicht nur auch noch schon doch sich selbst hier da
wo was wer wenn dann denn daß weil nun je all alle jede jeder jedes kein keine dies diese dieser dieses jene jener
ja nein mehr sehr bloß rein bis zu ab ihm ihn ihr ihre sei seit sowohl weder', '''.replace("'", ' ').replace(',', ' ').split())
vocab = collections.Counter()
def add_vocab(t):
    for w in re.findall(r'[A-Za-zÄÖÜäöüß]+', MARK.sub(' ', t)):
        if len(w) >= 3: vocab[w.lower()] += 1
for C in parts_by_ch:
    for p in C['paras']:
        if 'text' in p: add_vocab(p['text'])
    for t in C['notes'].values(): add_vocab(t)
def known(w):
    if re.search(r'.[A-ZÄÖÜ]', w) and not w.isupper():
        return False          # "beI" must not match "bei"
    w = w.lower()
    if len(w) <= 2: return w in FUNC
    return w in FUNC or vocab[w] >= 2

def segment(s):
    """Split s into known words (min length 2). Returns list or None; prefers fewest words."""
    n = len(s)
    best = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None: continue
        for j in range(i + 2, min(n, i + 30) + 1):
            w = s[i:j]
            if known(w):
                cand = best[i] + [w]
                if best[j] is None or len(cand) < len(best[j]):
                    best[j] = cand
    return best[n]

def variants(s):
    out = [s]
    v = s.replace('1', 'l').replace('0', 'o')
    v = v[:1] + v[1:].replace('I', 'l')
    out.append(v)
    if 'rn' in v: out.append(v.replace('rn', 'm'))
    if 'ii' in v: out.append(v.replace('ii', 'ü'))
    if 'cl' in v: out.append(v.replace('cl', 'd'))
    return out

FRAG = re.compile(r'^[A-Za-zÄÖÜäöüß0-9]{1,6}$')
spaced_log = []

def repair_spaced(text):
    # work on plain word tokens; markers and punctuation break runs
    toks = re.split(r'(\s+)', text)
    words = [i for i in range(0, len(toks), 2)]
    out_tokens = list(toks)
    i = 0
    W = len(words)
    used = set()
    while i < W:
        # build maximal run of fragment-like tokens starting at i
        best = None
        for j in range(i + 1, min(W, i + 25)):
            ws = [toks[words[k]] for k in range(i, j + 1)]
            # leading/trailing punctuation allowed on edges
            core = list(ws)
            lead = re.match(r'^[»„(\[]*', core[0]).group(0); core[0] = core[0][len(lead):]
            trail = re.search(r'[\.,;:!?«“)\]]*$', core[-1]).group(0)
            if trail: core[-1] = core[-1][:-len(trail)]
            if not all(FRAG.match(c) for c in core): break
            if known(core[0]) and len(core[0]) > 1 and not (len(core[0]) <= 3 and len(core) > 1 and len(core[1]) == 1):
                break   # a run must start with a fragment, not a real word
            singles = sum(1 for c in core if len(c) == 1 or re.search(r'\d', c))
            unknown = sum(1 for c in core if not known(c))
            if singles < 2 and not (unknown >= 1 and len(core) <= 3):
                continue
            joined = ''.join(core)
            if re.fullmatch(r'\d+', joined): break
            for v in variants(joined):
                seg = segment(v)
                if seg is None: continue
                if singles < 2 and len(seg) != 1: continue
                if len(seg) >= len(core): continue
                score = len(core) - 2 * len(seg)
                if best is None or score > best[0]:
                    best = (score, j, lead, trail, seg, v)
                break
        if best:
            score, j, lead, trail, seg, v = best
            orig_txt = ''.join(toks[words[i]:words[j] + 1])
            if len(seg) > 1 and seg[0].lower() in FUNC and toks[words[i]].strip('»„([') == seg[0]:
                rep = lead + seg[0] + ' ' + SP_O + ' '.join(seg[1:]) + SP_C + trail
            else:
                rep = lead + SP_O + ' '.join(seg) + SP_C + trail
            out_tokens[words[i]] = rep
            for k in range(words[i] + 1, words[j] + 1):
                out_tokens[k] = ''
            spaced_log.append(orig_txt + '  =>  ' + ' '.join(seg))
            i = j + 1
        else:
            i += 1
    return ''.join(out_tokens)

LETTERISH = re.compile(r'^[A-Za-zÄÖÜäöüß1]{1,2}$')
def repair_unknown_runs(text):
    """Fallback for names the vocabulary lacks: capitalised fragment + >=3 one/two-letter tokens."""
    def f(m):
        first, mid, last = m.group(1), m.group(2), m.group(3) or ''
        tail = ''
        if first == 'I': return m.group(0)
        if last and last.strip().lower() in ('und', 'der', 'die', 'das', 'bis', 'zu', 'in', 'im', 'ist', 'als', 'wie', 'von', 'vom', 'den', 'dem', 'des'):
            tail, last = last, ''
        toks = [first] + mid.split() + ([last.strip()] if last else [])
        if sum(1 for t in toks if len(t) == 1) < 3: return m.group(0)
        word = toks[0] + ''.join(toks[1:]).replace('1', 'l')
        if len(word) < 5: return m.group(0)
        spaced_log.append(m.group(0) + '  =>  ' + word + '  [fallback]')
        return SP_O + word + SP_C + tail
    return re.sub(r'(?<![\w\ue030])([A-ZÄÖÜ][a-zäöüß1]?)((?: [a-zäöüß1]{1,2}){3,})( [a-zäöüß]{1,4})?(?![\w])', f, text)

def repair_all(text):
    # apply to marker-free chunks
    pieces = re.split('([-][^-]*?[-]|[])', text)
    return ''.join(repair_unknown_runs(repair_spaced(p)) if not MARK.search(p) else p for p in pieces)

# Spaced runs may straddle a ref/page marker rarely; ignore.
for C in parts_by_ch:
    for p in C['paras']:
        if 'text' in p: p['text'] = repair_all(p['text'])
    for n in C['notes']: C['notes'][n] = repair_all(C['notes'][n])

# merge "Begriffs<SP>funktion..." when prefix+first word is a known compound
def merge_compounds(t):
    def f(m):
        pre, first = m.group(1), m.group(2)
        if vocab[(pre + first).lower()] >= 1:
            return pre + SP_O + first
        return m.group(0)
    return re.sub(r'([A-Za-zÄÖÜäöüß]{3,}) ' + SP_O + r'([a-zäöüß]+)', f, t)
for C in parts_by_ch:
    for p in C['paras']:
        if 'text' in p: p['text'] = merge_compounds(p['text'])

# ---------------------------------------------------------------- 1910 page breaks
BAR_EXCL_BEFORE = re.compile(r'(?:Bd\.|Band|Teil|Nr\.|S\.|Kap\.|Abt\.|Heft|Vol\.|Bde\.|Buch|Abschn\.|Art\.|§|=|\+|\-|<|>|\(|,)\s*$')
for C in parts_by_ch:
    paras = [p for p in C['paras'] if p['kind'] in ('p', 'c')]
    SEP = ''
    body = SEP.join(p['text'] for p in paras)
    # walk pages
    out = []
    pos = 0
    for m in re.finditer(ECW_O + '([^' + ECW_C + ']*)' + ECW_C, body):
        pass
    marks = list(re.finditer(ECW_O + '([^' + ECW_C + ']*)' + ECW_C, body))
    new_body = body[:marks[0].start()] if marks else body
    for idx, m in enumerate(marks):
        label = m.group(1)
        key = int(label) if label.isdigit() else label
        o_s, o_e, bracket, roman = orig[key]
        seg_end = marks[idx + 1].start() if idx + 1 < len(marks) else len(body)
        seg = body[m.start():seg_end]
        # candidates: small bar markers, small "1" numbers, standalone I/1/l/| tokens
        cand = []
        def mathy(st, en):
            prev = re.search(r'(\S*)\s*$', MARK.sub('', seg[max(0, st - 12):st])).group(1)
            nxt = re.match(r'\s*(\S*)', MARK.sub('', seg[en:en + 12])).group(1)
            def m_(t):
                t = t.strip('.,;:()')
                return len(t) <= 1 or bool(re.search(r'\d', t)) or t in ('••', '•••', '...', '=', '+')
            return m_(prev) or m_(nxt) or not seg[st - 1:st].isspace()
        for mm in re.finditer(BAR + '|' + NUM_O + r'1' + NUM_C, seg):
            if mm.group(0) != BAR and mathy(mm.start(), mm.end()):
                continue
            cand.append((mm.start(), mm.end(), 0))
        for mm in re.finditer(r'(?:(?<=\s)|(?<=-)|(?<=—))[I1l|](?=\s|-|' + SEP + r'|$)', seg):
            before = seg[:mm.start()]
            after = seg[mm.end():mm.end() + 3]
            if BAR_EXCL_BEFORE.search(before[-8:]) and not before.endswith('- ') and not before.endswith('-'):
                continue
            if re.match(r'\s*[=+\-<>\d)]', after) and not after.startswith('- ') and not after.startswith('-'):
                if not re.match(r'-\s', after):
                    continue
            if re.match(r'\.', after):
                continue
            if mathy(mm.start(), mm.end()) and seg[mm.start():mm.end()] != '|':
                continue
            cand.append((mm.start(), mm.end(), 1))
        cand.sort()
        expected = None if bracket else (o_e - o_s)
        if expected is not None and len(cand) != expected:
            warn('bars', C['ch']['slug'], 'ECW', label, 'expected', expected, 'found', len(cand), ':',
                 ' | '.join(MARK.sub('', seg[max(0, c[0] - 25):c[1] + 25]).replace(SEP, ' / ') for c in cand))
            if len(cand) > expected:
                # keep the most marker-like ones: small segments first, then 'I'/'|'
                def rank(c):
                    ch_ = seg[c[0]:c[1]]
                    return (c[2], 0 if ch_ in ('I', '|', BAR) else 1)
                keep = sorted(cand, key=rank)[:expected]
                cand = sorted(keep)
        pg = o_s
        res = []
        last = 0
        for st, en, _ in cand:
            pg += 1
            lab = (str(pg) if not roman else int_to_roman(pg)) if True else ''
            res.append(seg[last:st])
            # tidy surrounding spaces: "a I b" -> "a ‹p› b"; "x -I y" -> "x - ‹p› y"
            res.append(ORIG_O + lab + ORIG_C)
            last = en
            if seg[last:last + 1] == ' ' and res[-2].endswith(' '):
                last += 1
        res.append(seg[last:])
        new_body += ''.join(res)
    texts = new_body.split(SEP)
    for p, t in zip(paras, texts): p['text'] = t
    for n in C['notes']:
        # bars inside notes: drop silently
        t = C['notes'][n].replace(BAR, '')
        t = re.sub(r'(?<=\s)[I|](?=\s)', '', t)
        C['notes'][n] = re.sub(r'\s{2,}', ' ', t)


pickle.dump(parts_by_ch, open(S + '/stage2.pkl', 'wb'))
open(S + '/stage2.log', 'w', encoding='utf-8').write('\n'.join(log))
open(S + '/spaced.log', 'w', encoding='utf-8').write('\n'.join(spaced_log))
print('warnings', len(log), 'spaced repairs', len(spaced_log))
