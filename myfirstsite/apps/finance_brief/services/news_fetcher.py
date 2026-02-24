import requests
import xml.etree.ElementTree as ET

RSS_SOURCES = [
    {'url': 'https://feeds.reuters.com/reuters/businessNews', 'source': 'Reuters'},
    {'url': 'https://news.google.com/rss/search?q=finance+stock+market&hl=zh-TW&gl=TW&ceid=TW:zh-Hant', 'source': 'Google News'},
    {'url': 'https://www.cnyes.com/rss/news/cnnews.xml', 'source': '鉅亨網'},
]

TIMEOUT = 10  # seconds per RSS fetch


def _extract_link(elem):
    """Try multiple strategies to extract item URL."""
    # 1. Standard RSS 2.0 text content
    link = (elem.findtext('link') or '').strip()
    if link and link.startswith('http'):
        return link

    # 2. Atom-style href attribute
    link_elem = elem.find('link')
    if link_elem is not None:
        href = link_elem.get('href', '').strip()
        if href and href.startswith('http'):
            return href

    # 3. guid as permalink fallback
    guid_elem = elem.find('guid')
    if guid_elem is not None:
        is_link = guid_elem.get('isPermaLink', 'true').lower() != 'false'
        guid_text = (guid_elem.text or '').strip()
        if is_link and guid_text.startswith('http'):
            return guid_text

    return ''


def _parse_rss(url, source, max_items):
    """Parse a single RSS feed and return a list of headline dicts."""
    try:
        resp = requests.get(url, timeout=TIMEOUT, headers={'User-Agent': 'Mozilla/5.0'})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"[news_fetcher] Failed to fetch {source}: {e}")
        return []

    items = []
    # Support both <rss><channel><item> and <feed><entry> formats
    channel = root.find('channel')
    if channel is not None:
        elements = channel.findall('item')
    else:
        # Atom feed fallback
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        elements = root.findall('atom:entry', ns)

    for elem in elements[:max_items]:
        title = elem.findtext('title', '').strip()
        link = _extract_link(elem)
        pub = elem.findtext('pubDate', '') or elem.findtext('published', '')
        pub = pub.strip() if pub else ''

        if title and link:
            items.append({
                'title': title,
                'url': link,
                'source': source,
                'published': pub,
            })

    return items


def fetch_news(max_per_source=6):
    """Fetch and combine news from all RSS sources.

    Returns:
        list of dicts: [{title, url, source, published}]
    """
    all_news = []
    for src in RSS_SOURCES:
        headlines = _parse_rss(src['url'], src['source'], max_per_source)
        all_news.extend(headlines)
    return all_news
