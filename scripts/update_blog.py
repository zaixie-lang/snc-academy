"""Refresh one pinned and two recent Naver RSS posts with bounded local image cache."""
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'data/blog-config.json').read_text(encoding='utf-8'))
OUT = ROOT / 'data/blog-posts.json'
IMAGE_DIR = ROOT / 'images/blog'
OWNER = 'hannak74'
FALLBACK = 'images/blog-fallback.png'


def clean_url(url):
    p = urlsplit(html.unescape(url).strip())
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip('/'), '', ''))


def valid_image_url(url):
    p = urlsplit(html.unescape(url).strip())
    host = (p.hostname or '').lower()
    return p.scheme == 'https' and (host == 'pstatic.net' or host.endswith('.pstatic.net') or host == 'naver.net' or host.endswith('.naver.net'))


def image_from_description(desc):
    for match in re.finditer(r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)', html.unescape(desc), re.I):
        url = html.unescape(match.group(1)).strip()
        if valid_image_url(url):
            return url
    return ''


def download_image(url, stem):
    """Return a local image path, or empty string. Never publish partial downloads."""
    if not valid_image_url(url):
        return ''
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    # Images are intentionally stored with a fixed .img extension; browser decodes by bytes.
    target = IMAGE_DIR / (stem + '.img')
    tmp = IMAGE_DIR / (stem + '.tmp')
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; SCAcademyBlogUpdater/1.0)',
            'Referer': 'https://blog.naver.com/',
            'Accept': 'image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8',
        })
        with urllib.request.urlopen(req, timeout=20) as response:
            mime = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
            if not mime.startswith('image/'):
                raise ValueError('Non-image response: ' + mime)
            data = response.read(5 * 1024 * 1024 + 1)
        if not data or len(data) > 5 * 1024 * 1024:
            raise ValueError('Empty or oversized image')
        tmp.write_bytes(data)
        tmp.replace(target)
        return 'images/blog/' + target.name
    except Exception as exc:
        print(f'Image unavailable ({stem}): {exc}')
        tmp.unlink(missing_ok=True)
        # Preserve a previously cached image for the same article, if any.
        if target.is_file() and target.stat().st_size:
            return 'images/blog/' + target.name
        return ''


def main():
    request = urllib.request.Request('https://rss.blog.naver.com/hannak74.xml', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=25) as response:
        root = ET.fromstring(response.read())
    pinned = clean_url(CFG['pinned_url'])
    candidates, seen = [], set()
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        link = re.sub(r'\?fromRss=true.*$', '', (item.findtext('link') or '').strip())
        normalized = clean_url(link)
        if not title or normalized == pinned or normalized in seen:
            continue
        if not re.fullmatch(r'https://(?:m\.)?blog\.naver\.com/hannak74/\d+', normalized, re.I):
            continue
        try:
            date = parsedate_to_datetime(item.findtext('pubDate') or '').astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
        seen.add(normalized)
        candidates.append((date, title, link, item.findtext('description') or ''))
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) < 2:
        raise RuntimeError('RSS returned fewer than 2 usable posts; existing blog data retained')

    posts = [{
        'title': CFG['pinned_title'], 'url': CFG['pinned_url'],
        'image': CFG.get('pinned_image_source', FALLBACK),
        'tag': 'PICK',
    }]
    for index, (date, title, link, desc) in enumerate(candidates[:2]):
        article_id = clean_url(link).rstrip('/').split('/')[-1]
        image = download_image(image_from_description(desc), 'latest-' + article_id)
        posts.append({
            'title': title, 'url': link, 'image': image or FALLBACK,
            'date': date.date().isoformat(), 'tag': 'LATEST' if index == 0 else 'RECENT',
        })

    result = {'updated_at': datetime.now(timezone.utc).isoformat(), 'posts': posts}
    temp = OUT.with_suffix('.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(OUT)

    # Delete only files created by this script. Leave manually maintained files alone.
    active = {Path(p['image']).name for p in posts if p['image'].startswith('images/blog/')}
    for pattern in ('latest-*.img', 'pinned-*.img'):
        for old in IMAGE_DIR.glob(pattern):
            if old.name not in active:
                old.unlink()
    print(f'Saved {len(posts)} posts; locally cached {len(active)} images')


if __name__ == '__main__':
    main()
