"""Refresh rolling Naver blog posts with high-resolution image cache."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import json
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlsplit, urlunsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CFG_FILE = ROOT / 'data/blog-config.json'
OUT = ROOT / 'data/blog-posts.json'
IMAGE_DIR = ROOT / 'images/blog'
FALLBACK = 'images/blog-fallback.png'
OWNER = 'hannak74'
RSS_URL = f'https://rss.blog.naver.com/{OWNER}.xml'

USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/120.0.0.0 Safari/537.36'
)


def clean_url(url):
    p = urlsplit(html.unescape(url).strip())
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip('/'), '', ''))


def extract_log_no(url):
    cleaned = clean_url(url)
    m = re.search(r'/(?:hannak74/)?(\d+)', cleaned)
    return m.group(1) if m else ''


def is_valid_image_url(url):
    p = urlsplit(html.unescape(url).strip())
    host = (p.hostname or '').lower()
    return p.scheme == 'https' and (
        host == 'pstatic.net' or host.endswith('.pstatic.net')
        or host == 'naver.net' or host.endswith('.naver.net')
    )


def fetch_url(url, timeout=15, referer=None):
    headers = {'User-Agent': USER_AGENT}
    if referer:
        headers['Referer'] = referer
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_post_details(log_no):
    """Fetch title and representative high-resolution image URL from Naver Blog post."""
    post_url = f'https://blog.naver.com/PostView.naver?blogId={OWNER}&logNo={log_no}'
    try:
        raw_html = fetch_url(post_url, timeout=15).decode('utf-8', errors='ignore')
    except Exception as exc:
        print(f'Failed to fetch post HTML ({log_no}): {exc}')
        return '', ''

    # 1. Title extraction
    title = ''
    se_m = re.search(r'<div[^>]*class=["\'][^"\']*se-title-text[^"\']*["\'][^>]*>(.*?)</div>', raw_html, re.S)
    if se_m:
        title = html.unescape(re.sub(r'<[^>]+>', '', se_m.group(1))).strip()
    if not title:
        og_m = re.search(r'<meta\s+property=["\']og:title["\']\s+content=["\']([^"\']+)["\']', raw_html, re.I)
        if og_m:
            title = html.unescape(og_m.group(1)).strip()

    # 2. Representative image extraction (high-res cover image)
    best_image_url = ''
    # Look for first Smart Editor image in post body
    img_matches = re.findall(r'<img\b[^>]*\bclass=["\'][^"\']*se-image-resource[^"\']*["\'][^>]*>', raw_html)
    if not img_matches:
        img_matches = re.findall(r'<img\b[^>]*\bdata-lazy-src=["\'][^"\']+["\'][^>]*>', raw_html)

    for tag in img_matches:
        lazy_m = re.search(r'data-lazy-src=["\']([^"\']+)["\']', tag, re.I)
        src_m = re.search(r'src=["\']([^"\']+)["\']', tag, re.I)
        candidate = (lazy_m or src_m).group(1) if (lazy_m or src_m) else ''
        candidate = html.unescape(candidate).strip()
        if not is_valid_image_url(candidate):
            continue
        if any(ignore in candidate for ignore in ('img_ani_', 'profile', 'dthumb-phinf', 'static.naver.net')):
            continue
        best_image_url = candidate
        break

    # Fallback to og:image if no body image found
    if not best_image_url:
        og_img_m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', raw_html, re.I)
        if og_img_m:
            best_image_url = html.unescape(og_img_m.group(1)).strip()

    return title, best_image_url


def fetch_rss_recent_posts(exclude_urls, limit=2):
    """Fetch recent posts from Naver Blog RSS feed, excluding specified URLs."""
    try:
        raw_xml = fetch_url(RSS_URL, timeout=15)
        root = ET.fromstring(raw_xml)
    except Exception as exc:
        print(f'Failed to fetch RSS feed: {exc}')
        return []

    exclude_set = {clean_url(u) for u in exclude_urls}
    candidates = []
    seen = set()

    for item in root.findall('.//item'):
        raw_link = (item.findtext('link') or '').strip()
        link = re.sub(r'\?fromRss=true.*$', '', raw_link).strip()
        normalized = clean_url(link)
        title = html.unescape((item.findtext('title') or '').strip())

        if not normalized or normalized in exclude_set or normalized in seen:
            continue
        if not re.fullmatch(rf'https://(?:m\.)?blog\.naver\.com/{OWNER}/\d+', normalized, re.I):
            continue

        pub_date_str = item.findtext('pubDate') or ''
        dt = None
        if pub_date_str:
            try:
                dt = parsedate_to_datetime(pub_date_str).astimezone(timezone.utc)
            except Exception:
                dt = None

        seen.add(normalized)
        candidates.append({
            'url': normalized,
            'title': title,
            'pubDate': dt,
        })

    candidates.sort(key=lambda x: x['pubDate'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return candidates[:limit]


def determine_extension(data, content_type=''):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if data.startswith(b'\xff\xd8'):
        return '.jpg'
    if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
        return '.webp'
    if 'png' in content_type:
        return '.png'
    if 'jpeg' in content_type or 'jpg' in content_type:
        return '.jpg'
    if 'webp' in content_type:
        return '.webp'
    return '.png'


def download_post_image(image_url, article_id):
    """Download near-original image to images/blog/post-{article_id}.{ext}.

    If download fails, preserve any previously cached image for this article.
    Never publish partial downloads. Avoid creating duplicate extensions (.img / .png).
    """
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    # Check if a previously cached image already exists for fallback
    existing_file = None
    for pattern in (f'post-{article_id}.*', f'latest-{article_id}.*'):
        for f in IMAGE_DIR.glob(pattern):
            if f.is_file() and f.stat().st_size > 0:
                existing_file = f
                break
        if existing_file:
            break

    if not image_url or not is_valid_image_url(image_url):
        if existing_file:
            return 'images/blog/' + existing_file.name
        return ''

    # Build high-resolution URLs to try in order
    candidates = []
    base_url = image_url.split('?')[0]

    # 1. Postfiles with high-res type=w966
    postfiles_base = base_url.replace('blogthumb.pstatic.net', 'postfiles.pstatic.net')
    candidates.append(f'{postfiles_base}?type=w966')
    candidates.append(f'{postfiles_base}?type=w773')
    candidates.append(postfiles_base)

    # 2. Blogthumb high-res (w1) or original thumbnail if postfiles fails
    if 'blogthumb.pstatic.net' in image_url:
        candidates.append(f'{base_url}?type=w1')
        candidates.append(image_url)

    data = None
    content_type = ''
    for test_url in candidates:
        try:
            req = urllib.request.Request(test_url, headers={
                'User-Agent': USER_AGENT,
                'Referer': 'https://blog.naver.com/',
                'Accept': 'image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8',
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                mime = resp.headers.get('Content-Type', '').split(';')[0].strip().lower()
                if not mime.startswith('image/'):
                    continue
                content = resp.read(10 * 1024 * 1024 + 1)
                if content and len(content) <= 10 * 1024 * 1024:
                    data = content
                    content_type = mime
                    break
        except Exception:
            continue

    if not data:
        print(f'Image download failed for article {article_id}')
        if existing_file:
            print(f'Preserving existing cached image: {existing_file.name}')
            return 'images/blog/' + existing_file.name
        return ''

    ext = determine_extension(data, content_type)
    target = IMAGE_DIR / f'post-{article_id}{ext}'
    tmp = IMAGE_DIR / f'post-{article_id}.tmp'

    try:
        tmp.write_bytes(data)
        tmp.replace(target)

        # Remove any obsolete duplicate file for this article with a different extension
        for old in IMAGE_DIR.glob(f'post-{article_id}.*'):
            if old != target and old.is_file():
                old.unlink()
        for old in IMAGE_DIR.glob(f'latest-{article_id}.*'):
            if old.is_file():
                old.unlink()

        return 'images/blog/' + target.name
    except Exception as exc:
        print(f'Error saving image ({article_id}): {exc}')
        tmp.unlink(missing_ok=True)
        if existing_file:
            return 'images/blog/' + existing_file.name
        return ''


def is_file_referenced(filename, active_images):
    """Check if filename is actively referenced in active posts, config, HTML, CSS, or JS."""
    if filename in active_images:
        return True

    # Check data/blog-config.json
    try:
        cfg_text = CFG_FILE.read_text(encoding='utf-8')
        if filename in cfg_text:
            return True
    except Exception:
        pass

    # Check index.html, CSS, and JS files
    search_paths = [
        ROOT / 'index.html',
        ROOT / 'js/main.js',
        ROOT / 'css/style.css',
    ]
    for sp in search_paths:
        if sp.is_file():
            try:
                if filename in sp.read_text(encoding='utf-8', errors='ignore'):
                    return True
            except Exception:
                pass

    return False


def cleanup_unused_cache_images(active_images):
    """Delete ONLY unreferenced auto-cache images (post-*, latest-*).

    Never delete manual images (pinned-*), brand logos, or fallback images.
    Before deleting, verify that the file is not referenced anywhere.
    """
    for pattern in ('latest-*.img', 'latest-*.png', 'latest-*.jpg',
                    'post-*.img', 'post-*.png', 'post-*.jpg', 'post-*.webp'):
        for old in IMAGE_DIR.glob(pattern):
            if not old.is_file():
                continue
            if not is_file_referenced(old.name, active_images):
                print(f'Removing unreferenced auto-cached image: {old.name}')
                old.unlink(missing_ok=True)


def main():
    cfg = json.loads(CFG_FILE.read_text(encoding='utf-8'))
    cfg_posts = cfg.get('posts') or cfg.get('rolling_posts') or []

    # Fallback to legacy pinned + RSS if 'posts' is not defined in config
    if not cfg_posts and 'pinned_url' in cfg:
        cfg_posts = [
            {'url': cfg['pinned_url'], 'title': cfg.get('pinned_title', ''), 'tag': 'PICK',
             'image': cfg.get('pinned_image_source', '')}
        ]

    posts = []
    default_tags = ['노피곰 설명회', '철산중 영어시험 분석', '강담수학']

    # 1. Process pinned posts (3 items)
    for index, post_cfg in enumerate(cfg_posts):
        url = clean_url(post_cfg.get('url', ''))
        log_no = extract_log_no(url)
        tag = post_cfg.get('tag') or (default_tags[index] if index < len(default_tags) else 'S&C BLOG')

        # Use title/image from config if explicitly set; otherwise fetch from Naver blog
        title = post_cfg.get('title', '').strip()
        custom_image = post_cfg.get('image', '').strip()

        auto_title, auto_image_url = '', ''
        if not title or not custom_image:
            auto_title, auto_image_url = fetch_post_details(log_no)

        final_title = title or auto_title or 'S&C ACADEMY 공식 블로그'

        # Determine image
        if custom_image and (ROOT / custom_image).is_file():
            final_image = custom_image
        else:
            downloaded = download_post_image(auto_image_url, log_no)
            final_image = downloaded or FALLBACK

        post_entry = {
            'title': final_title,
            'url': url,
            'image': final_image,
            'tag': tag,
        }
        posts.append(post_entry)

    # 2. Fetch 2 recent posts from RSS feed excluding pinned URLs
    pinned_urls = [p['url'] for p in posts]
    recent_candidates = fetch_rss_recent_posts(exclude_urls=pinned_urls, limit=2)

    recent_tags = ['LATEST', 'RECENT']
    for idx, candidate in enumerate(recent_candidates):
        url = candidate['url']
        log_no = extract_log_no(url)
        auto_title, auto_image_url = fetch_post_details(log_no)
        final_title = auto_title or candidate.get('title') or 'S&C ACADEMY 공식 블로그'
        downloaded = download_post_image(auto_image_url, log_no)
        final_image = downloaded or FALLBACK
        tag = recent_tags[idx] if idx < len(recent_tags) else 'LATEST'

        posts.append({
            'title': final_title,
            'url': url,
            'image': final_image,
            'tag': tag,
        })

    # Fallback to existing posts if RSS fetch failed and we have fewer than 5 posts
    if len(posts) < 5 and OUT.is_file():
        try:
            prev_data = json.loads(OUT.read_text(encoding='utf-8'))
            prev_posts = prev_data.get('posts', [])
            existing_urls = {clean_url(p['url']) for p in posts}
            for p in prev_posts:
                if len(posts) >= 5:
                    break
                p_url = clean_url(p.get('url', ''))
                if p_url and p_url not in existing_urls:
                    posts.append(p)
                    existing_urls.add(p_url)
        except Exception as exc:
            print(f'Warning: Failed to load previous posts for fallback: {exc}')

    # Save data/blog-posts.json atomically
    result = {
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'posts': posts,
    }
    temp = OUT.with_suffix('.tmp')
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(OUT)

    # Clean up only unreferenced auto-cache images
    active_images = {Path(p['image']).name for p in posts if p['image'].startswith('images/blog/')}
    cleanup_unused_cache_images(active_images)

    print(f'Successfully updated {len(posts)} rolling posts.')
    for idx, p in enumerate(posts):
        print(f"  [{idx + 1}] {p['tag']} | {p['title'][:40]}... | {p['image']}")


if __name__ == '__main__':
    main()
