"""RSS -> verified, locally cached blog images. No invented articles or thumbnails."""
import html
import json
import mimetypes
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
IMG = ROOT / 'images/blog'
IMG.mkdir(parents=True, exist_ok=True)
OWNER = 'hannak74'

def clean_url(url):
    p = urlsplit(html.unescape(url).strip())
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip('/'), '', ''))

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0', 'Referer':'https://blog.naver.com/'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read(), r.headers.get('Content-Type', '')

def image_from_description(desc):
    for match in re.finditer(r'<img\b[^>]*\bsrc\s*=\s*["\']([^"\']+)', html.unescape(desc), re.I):
        url = html.unescape(match.group(1))
        if url.startswith('https://') and any(x in urlsplit(url).netloc for x in ('pstatic.net','naver.net')):
            return url
    return ''

def cache_image(url, name):
    if not url: return ''
    try:
        data, ct = fetch(url)
        if not ct.lower().startswith('image/') or len(data) < 300: raise ValueError('not image')
        ext = '.png' if 'png' in ct else '.webp' if 'webp' in ct else '.jpg' if ('jpeg' in ct or 'jpg' in ct) else ''
        if not ext: raise ValueError('unsupported image')
        path = IMG / (name + ext)
        path.write_bytes(data)
        return 'images/blog/' + path.name
    except Exception as exc:
        print('Image unavailable:', name, str(exc))
        return ''

def is_shared(item, link, desc):
    """Conservative filter: exclude only clearly indicated reposts; manual exclude list for ambiguity."""
    if clean_url(link) in {clean_url(u) for u in CFG.get('exclude_urls', [])}: return True
    if not re.search(r'/(?:'+OWNER+r')/\d+', clean_url(link), re.I): return True
    author = (item.findtext('author') or item.findtext('{http://purl.org/dc/elements/1.1/}creator') or '').strip()
    if author and OWNER not in author and '강한나' not in author: return True
    plain = re.sub(r'<[^>]+>', ' ', html.unescape(desc))[:450]
    if re.search(r'(?:다른\s*블로그에서\s*공유|원문\s*출처\s*[:：]|공유한\s*글)', plain): return True
    return False

def main():
    content, _ = fetch('https://rss.blog.naver.com/hannak74.xml')
    root = ET.fromstring(content)
    candidates = []
    for item in root.findall('.//item'):
        title = (item.findtext('title') or '').strip()
        link = re.sub(r'\?fromRss=true.*$', '', (item.findtext('link') or '').strip())
        desc = item.findtext('description') or ''
        if not title or not link or is_shared(item, link, desc): continue
        try: dt = parsedate_to_datetime(item.findtext('pubDate') or '').astimezone(timezone.utc)
        except Exception: continue
        candidates.append((dt, title, link, desc))
    candidates.sort(reverse=True)
    pinned = clean_url(CFG['pinned_url'])
    latest = []
    for dt, title, link, desc in candidates:
        if clean_url(link) == pinned: continue
        article_id = re.search(r'/([0-9]{9,})$', clean_url(link))
        if not article_id: continue
        image = cache_image(image_from_description(desc), 'latest-' + article_id.group(1))
        # Never substitute a different article's image.
        latest.append({'title':title, 'url':link, 'image':image, 'date':dt.date().isoformat()})
        if len(latest) == 2: break
    pinned_img = cache_image(CFG.get('pinned_image_source',''), 'pinned')
    result = {'updated_at':datetime.now(timezone.utc).isoformat(),
              'posts':[{'title':CFG['pinned_title'], 'url':CFG['pinned_url'], 'image':pinned_img, 'tag':'PICK'}] +
                      [{**p,'tag':'LATEST' if i==0 else 'RECENT'} for i,p in enumerate(latest)]}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print('Saved',len(result['posts']),'posts; cached images',sum(bool(p['image']) for p in result['posts']))

if __name__ == '__main__': main()
