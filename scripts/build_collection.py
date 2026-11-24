# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow==12.0.0"]
# ///
"""Build the collection from its canonical pixel grids, or check the exports."""
import argparse
import io
import json
import re
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SIZE = 34


def terminal(im, ascii_only=False):
    rows = []
    for y in range(0, SIZE, 2):
        row = ''
        for x in range(SIZE):
            pair = bool(im.getpixel((x, y))), bool(im.getpixel((x, y+1)))
            row += ('#' if any(pair) else ' ') if ascii_only else {
                (False, False): ' ', (True, False): '▀',
                (False, True): '▄', (True, True): '█',
            }[pair]
        rows.append(row.rstrip())
    return '\n'.join(rows) + '\n'


def read_grid(item):
    data = json.loads((ROOT/'logos'/item['slug']/'design.json').read_text())
    rows = data['rows']
    assert data['student'] == item['slug']
    assert len(rows) == SIZE and all(len(row) == SIZE and set(row) <= {'.', '#'} for row in rows)
    assert any('#' in row for row in rows)
    assert set(rows[0]+rows[-1]) == {'.'} and all(row[0] == row[-1] == '.' for row in rows)
    im = Image.new('1', (SIZE, SIZE))
    im.putdata([255 if pixel == '#' else 0 for row in rows for pixel in row])
    return im


def exports(item, im):
    rgba = Image.new('RGBA', im.size, item['color'])
    rgba.putalpha(im.convert('L'))
    png = io.BytesIO()
    rgba.resize((680, 680), Image.Resampling.NEAREST).save(png, format='PNG')
    rects = ''.join(f'<rect x="{x}" y="{y}" width="1" height="1"/>'
                    for y in range(SIZE) for x in range(SIZE) if im.getpixel((x, y)))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 34" width="680" height="680" '
           f'shape-rendering="crispEdges"><title>{escape(item["name"])} halo logo</title>'
           f'<g fill="{item["color"]}">{rects}</g></svg>\n')
    return {'logo.png': png.getvalue(), 'logo.svg': svg.encode(),
            'logo.txt': ('$1'+terminal(im)).encode(), 'mono.txt': terminal(im).encode(),
            'ascii.txt': terminal(im, True).encode(), 'color': (item['color']+'\n').encode()}


def check_fastfetch(item, im):
    ansi = re.compile(r'\x1b\[[0-9;]*m')
    for variant, expected in [('logo', terminal(im)), ('mono', terminal(im)), ('ascii', terminal(im, True))]:
        result = subprocess.run(['fastfetch', '--config', 'none', '--logo-type', 'file',
                                 '--logo', str(ROOT/'logos'/item['slug']/f'{variant}.txt'),
                                 '--logo-position', 'top', '--structure', 'separator', '--pipe', 'true'],
                                capture_output=True, text=True, check=True, timeout=30)
        assert not result.stderr, result.stderr
        assert ansi.sub('', result.stdout).splitlines()[:17] == expected.splitlines()
    result = subprocess.run(['fastfetch', '--config', 'none', '--logo-type', 'file',
                             '--logo', str(ROOT/'logos'/item['slug']/'logo.txt'),
                             '--logo-color-1', item['color'], '--logo-position', 'top',
                             '--structure', 'separator', '--pipe', 'false'],
                            capture_output=True, text=True, check=True, timeout=30)
    assert not result.stderr
    rgb = bytes.fromhex(item['color'][1:])
    assert '\x1b[38;2;'+';'.join(map(str, rgb))+'m' in result.stdout


def font(size):
    for name in ('DejaVuSans.ttf', '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def gallery(items):
    items = sorted(items, key=lambda item: (item['school'], item['name']))
    columns = 4
    rows = (len(items) + columns - 1) // columns
    sheet = Image.new('RGB', (1592, 128 + rows * 384), '#171c24')
    draw = ImageDraw.Draw(sheet)
    draw.text((32, 24), 'Fastfetch Blue Archive Logos', fill='#f1f5f9', font=font(32))
    draw.text((32, 68), 'Grouped by school / 34 columns x 17 rows', fill='#a3b2c4', font=font(18))
    for index, item in enumerate(items):
        x, y = 24+(index%columns)*392, 112+(index//columns)*384
        draw.rounded_rectangle((x, y, x+368, y+356), radius=10, fill='#202733')
        draw.text((x+20, y+14), item['name'], font=font(24), fill=item['color'])
        draw.text((x+20, y+46), item['school'], font=font(16), fill='#a3b2c4')
        im = Image.open(ROOT/'logos'/item['slug']/'logo.png').convert('RGBA')
        im = im.resize((272, 272), Image.Resampling.NEAREST)
        sheet.paste(im, (x+48, y+76), im)
    (ROOT/'docs').mkdir(exist_ok=True)
    sheet.save(ROOT/'docs/gallery.png')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check committed exports without modifying files.')
    parser.add_argument('--fastfetch', action='store_true', help='Also exercise the installed Fastfetch binary.')
    args = parser.parse_args()
    catalog = json.loads((ROOT/'catalog.json').read_text())
    items = catalog['logos']
    assert catalog['format'] == 1 and len({item['slug'] for item in items}) == len(items)
    for item in items:
        assert re.fullmatch(r'[a-z0-9-]+', item['slug']) and re.fullmatch(r'#[0-9a-fA-F]{6}', item['color'])
        im = read_grid(item)
        for name, data in exports(item, im).items():
            path = ROOT/'logos'/item['slug']/name
            if args.check:
                if name.endswith('.png'):
                    actual = Image.open(path).convert('RGBA')
                    expected = Image.open(io.BytesIO(data)).convert('RGBA')
                    assert actual.size == expected.size and actual.tobytes() == expected.tobytes(), f'Stale export: {path.relative_to(ROOT)}'
                else:
                    assert path.read_bytes() == data, f'Stale export: {path.relative_to(ROOT)}'
            else:
                path.write_bytes(data)
        if args.fastfetch:
            check_fastfetch(item, im)
        print(('Checked' if args.check else 'Built'), item['slug'])
    if not args.check:
        gallery(items)
    print(f'{len(items)} logos; all exports match their source grids.')


if __name__ == '__main__':
    main()
