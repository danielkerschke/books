"""Stage 0: read the invisible OCR text layer of the archive.org PDF as positioned words.

Each word: (x, y, size, tz, text). tz is the horizontal scaling the OCR layer applies to fit
the word to its box on the scan; letter-spaced (gesperrt) words show up as large tz.
"""
import re, sys
from pypdf import PdfReader

TOK = re.compile(rb'([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) Tm|([-\d.]+) ([-\d.]+) Td|/\S+ ([\d.]+) Tf|([\d.]+) Tz|\[ <([0-9A-Fa-f]*)> \] TJ')

def page_words(page):
    data = page.get_contents().get_data()
    x = y = lx = ly = size = tz = 0.0
    out = []
    for m in TOK.finditer(data):
        if m.group(1):
            x = lx = float(m.group(5)); y = ly = float(m.group(6))
        elif m.group(7):
            lx += float(m.group(7)); ly += float(m.group(8)); x, y = lx, ly
        elif m.group(9):
            size = float(m.group(9))
        elif m.group(10):
            tz = float(m.group(10))
        elif m.group(11) is not None:
            text = bytes.fromhex(m.group(11).decode()).decode('utf-16-be')
            out.append((round(x, 1), round(y, 1), round(size, 2), round(tz, 1), text))
    return out

if __name__ == '__main__':
    r = PdfReader(sys.argv[1])
    for i in map(int, sys.argv[2:]):
        for w in page_words(r.pages[i - 1]):
            print(w)
