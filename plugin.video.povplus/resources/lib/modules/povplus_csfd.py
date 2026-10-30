# Modified for POV+ by kudykam · 2026-10-30 · GPL-3.0-only
"""ČSFD metadata. No CAPTCHA solving, login scraping, or substituted ratings.

Page fields cross-checked against SikySikov metadata.csfd.cz 3.49 (GPL v3):
https://github.com/sikysikov/sikyaddons/blob/master/repo/metadata.csfd.cz/csfdcz.xml
The transport remains independent; the TMDb helper is not a ČSFD API.
"""
import json
import re
import unicodedata
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlsplit
from modules.povplus_policy import number


class Unavailable(Exception):
    pass


def normal(text):
    return re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', str(text or '')).encode('ascii', 'ignore').decode().lower())


def text(value):
    # Kodi labels use bracket markup; service content must remain plain text.
    return re.sub(r'\s+', ' ', str(value or '')).replace('[', '(').replace(']', ')').strip()


class Node:
    def __init__(self, tag='', attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or []), []

    def content(self):
        return ''.join(c.content() if isinstance(c, Node) else c for c in self.children)

    def nodes(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.nodes()

    def has(self, cls):
        return cls in self.attrs.get('class', '').split()

    def first(self, cls=None, tag=None):
        return next((n for n in self.nodes() if (cls is None or n.has(cls)) and (tag is None or n.tag == tag)), None)


class DOM(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root, self.stack = Node('root'), []
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                return

    def handle_data(self, value):
        self.stack[-1].children.append(value)


def validate_page(html):
    if any(marker in html.lower() for marker in ('anubis_challenge', 'making sure you\'re not a bot', 'cf-chl-', 'captcha', 'anubis could not load')):
        raise Unavailable('ČSFD blokuje automatické čtení. Hodnocení se nezobrazuje; ochrana se neobchází.')


def film_id(url):
    parsed = urlsplit(urljoin('https://www.csfd.cz', str(url)))
    if parsed.scheme != 'https' or parsed.hostname not in ('www.csfd.cz', 'csfd.cz'):
        return None
    match = re.match(r'/film/(\d+)(?:[-/]|$)', parsed.path)
    return match.group(1) if match else None


def search_candidates(html):
    validate_page(html)
    root, results, seen = DOM(html).root, [], set()
    for article in root.nodes():
        if article.tag != 'article':
            continue
        link = article.first('film-title-name')
        if not link or not film_id(link.attrs.get('href', '')):
            continue
        info = article.first('film-title-info')
        match = re.search(r'\b(?:19|20)\d{2}\b', info.content() if info else article.content())
        mid = film_id(link.attrs['href'])
        if mid in seen:
            continue
        seen.add(mid)
        alias = article.first('search-name')
        results.append({'id': mid, 'title': text(link.content()), 'aliases': [text(alias.content()).strip('()')] if alias else [], 'year': int(match.group()) if match else None})
    return results


def parse_movie(html, mid):
    validate_page(html)
    root = DOM(html).root
    ld = []
    for node in root.nodes():
        if node.tag == 'script' and node.attrs.get('type') == 'application/ld+json':
            try:
                data = json.loads(node.content())
                ld.extend(data if isinstance(data, list) else data.get('@graph', [data]))
            except (ValueError, TypeError, AttributeError):
                pass
    movie = next((n for n in ld if isinstance(n, dict) and n.get('@type') in ('Movie','TVSeries','TVEpisode')), {})
    heading = root.first('film-header-name') or root
    heading = heading.first(tag='h1')
    title = text(heading.content() if heading else movie.get('name'))
    title = re.sub(r'\s*\(\d{4}\)\s*$', '', title)
    year = str(movie.get('dateCreated') or movie.get('datePublished') or '')[:4]
    if not year.isdigit():
        header = root.first('film-header-name')
        match = re.search(r'\b(?:19|20)\d{2}\b', header.content() if header else '')
        year = match.group() if match else None
    if not year:
        origin = root.first('origin')
        match = re.search(r'\b(?:19|20)\d{2}\b', origin.content() if origin else '')
        year = match.group() if match else None
    rating_node = root.first('film-rating-average') or root.first('rating-average')
    rating = None
    if rating_node:
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*%', rating_node.content())
        rating = number(match.group(1).replace(',', '.')) if match else None
    if rating is None:
        aggregate = movie.get('aggregateRating') or {}
        best = number(aggregate.get('bestRating'))
        value = number(aggregate.get('ratingValue'))
        if best and value is not None:
            rating = 100 * value / best
    if rating is not None and not 0 <= rating <= 100:
        rating = None
    imdbs = set(re.findall(r'imdb\.com/title/(tt\d+)', html))
    reviews = []
    for node in root.nodes():
        if node.tag != 'article':
            continue
        body = node.first('comment') or node.first('review-text') or node.first('user-comment') or node.first('review-content')
        if body is None:
            body = next((n for n in node.nodes() if any(k.endswith('review-content') for k in n.attrs)), None)
        author = node.first('user-title-name') or node.first('user-title')
        # Dates/actions nested inside review content are not part of the review.
        def review_text(n):
            if isinstance(n, str): return n
            if n.has('review-date') or n.tag in ('script', 'style'): return ''
            return ''.join(review_text(c) for c in n.children)
        body_text = text(review_text(body)) if body else ''
        if body_text:
            reviews.append({'author':text(author.content()) if author else 'Uživatel ČSFD', 'text':body_text[:900], 'source':'ČSFD', 'url':'https://www.csfd.cz/film/%s/recenze/' % mid})
        if len(reviews) == 3:
            break
    genres_node = root.first('genres')
    return {'id':str(mid), 'title':title, 'year':int(year) if year and str(year).isdigit() else None,
            'rating':rating, 'imdbIds':sorted(imdbs), 'reviews':reviews,
            'genres':text(genres_node.content()).split(' / ') if genres_node else [],
            'source':'ČSFD', 'mediaType':'movie' if movie.get('@type')=='Movie' else 'tv' if movie.get('@type') in ('TVSeries','TVEpisode') else None, 'url':'https://www.csfd.cz/film/%s/' % mid}


class Client:
    def __init__(self, api='', fetch=None):
        self.api = api.strip().rstrip('/')
        if self.api:
            u = urlsplit(self.api)
            if u.scheme not in ('http','https') or not u.hostname or u.username or u.password or u.query or u.fragment:
                raise Unavailable('Neplatná adresa vlastního ČSFD API.')
        self.fetch = fetch or self._fetch

    @staticmethod
    def _fetch(url, as_json=False):
        import requests
        try:
            response = requests.get(url, timeout=(4, 7), allow_redirects=False,
                                    headers={'User-Agent':'POVPlus/1.0 (+Kodi personal movie metadata)', 'Accept':'application/json' if as_json else 'text/html'})
            if response.status_code != 200 or len(response.content) > 2_000_000:
                raise Unavailable('Zdroj ČSFD neodpověděl nebo odmítl požadavek.')
            return response.json() if as_json else response.text
        except (requests.RequestException, ValueError):
            raise Unavailable('ČSFD je momentálně nedostupné.') from None

    def movie(self, mid):
        if not str(mid).isdigit():
            raise Unavailable('Neplatné ID ČSFD.')
        if not self.api:
            return parse_movie(self.fetch('https://www.csfd.cz/film/%s/' % mid), mid)
        raw = self.fetch(self.api+'/movie/'+str(mid), True)
        if not isinstance(raw, dict) or str(raw.get('id')) != str(mid):
            raise Unavailable('ČSFD API nevrátilo správný film.')
        rating = number(raw.get('rating'))
        return {'id':str(mid), 'title':text(raw.get('title')), 'year':raw.get('year'),
                'rating':rating if rating is not None and 0 <= rating <= 100 else None,
                'genres':raw.get('genres') or [], 'reviews':[], 'imdbIds':[], 'source':'ČSFD',
                'url':'https://www.csfd.cz/film/%s/' % mid}

    def lookup(self, meta):
        titles = {normal(meta.get('title')), normal(meta.get('originaltitle'))} - {''}
        year, imdb = str(meta.get('year') or ''), str(meta.get('imdb_id') or '')
        query = meta.get('originaltitle') or meta.get('title')
        if not query or not year:
            raise Unavailable('Chybí název nebo rok pro bezpečné přiřazení ČSFD.')
        if self.api:
            data = self.fetch(self.api+'/search/'+quote(str(query), safe=''), True)
            candidates = data.get('movies', []) if isinstance(data, dict) else data if isinstance(data, list) else []
        else:
            candidates = search_candidates(self.fetch('https://www.csfd.cz/hledat/?q='+quote(str(query))))
        matches = [c for c in candidates if isinstance(c,dict) and titles.intersection({normal(c.get('title')), *(normal(a) for a in c.get('aliases', []) if isinstance(a, str))}) and str(c.get('year')) == year]
        if len(matches) != 1:
            raise Unavailable('ČSFD film nelze jednoznačně přiřadit. Použij ruční propojení v detailu POV+.')
        result = self.movie(matches[0]['id'])
        if result.get('mediaType') == 'tv':
            raise Unavailable('ČSFD profil patří seriálu, nikoli filmu.')
        if normal(result['title']) not in titles or str(result['year']) != year:
            raise Unavailable('Profil ČSFD neodpovídá názvu a roku filmu.')
        if result['imdbIds'] and imdb and imdb not in result['imdbIds']:
            raise Unavailable('ČSFD profil má jiné IMDb ID.')
        result['matchedBy'] = 'imdb' if imdb in result['imdbIds'] else 'unique_title_year'
        return result
