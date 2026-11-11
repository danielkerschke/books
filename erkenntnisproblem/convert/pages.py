"""Stage 1: group the OCR words of every PDF page into lines and save them as JSON.

    python pages.py <pdf> <out.json>

Output: list of pages {pdf: n, lines: [{y, x, size, tz, text}]}, top to bottom.
"""
import json, sys
from pypdf import PdfReader
from words import page_words

def lines_of(words):
    lines = []
    for x, y, size, tz, text in words:
        if lines and abs(lines[-1]['y'] - y) < 2.5 and x >= lines[-1]['xmax'] - 1:
            l = lines[-1]
        else:
            l = {'y': y, 'x': x, 'xmax': x, 'sizes': [], 'tzs': [], 'words': []}
            lines.append(l)
        l['words'].append(text); l['sizes'].append(size); l['tzs'].append(tz); l['xmax'] = x
    out = []
    for l in sorted(lines, key=lambda l: -l['y']):
        s = sorted(l['sizes'])
        out.append({'y': l['y'], 'x': l['x'], 'size': s[len(s) // 2], 'tz': l['tzs'],
                    'text': ''.join(l['words']).rstrip()})
    return out

if __name__ == '__main__':
    r = PdfReader(sys.argv[1])
    pages = [{'pdf': i + 1, 'lines': lines_of(page_words(p))} for i, p in enumerate(r.pages)]
    json.dump(pages, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
    print(len(pages), 'pages')
