'''
Scrapes movie info from Rotten Tomatoes for MovieRex. Written by Brooke Polak.

The public entry point is scrape(title, year), which returns a plain dict of
movie data (or raises MovieNotFound). Rendering lives in update_html.py, so the
site template can change without re-scraping anything.
'''

import os
import re
import time
import unicodedata
import urllib.parse

import requests
from bs4 import BeautifulSoup
from PIL import Image

RT_BASE = "https://www.rottentomatoes.com"
POSTER_DIR = "img/movies"

# Posters render a few hundred px wide; anything larger is wasted bytes.
POSTER_WIDTH = 400
POSTER_QUALITY = 82

# Rotten Tomatoes serves a stub page to the default requests user-agent.
HEADERS = {
	"User-Agent": (
		"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
		"(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
	),
	"Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 20
RETRIES = 3

# Minimum seconds between any two requests to Rotten Tomatoes, enforced globally
# at the request layer so slug-guessing, search fallbacks, poster downloads and
# the nightly refresh all share one polite cadence. Override with the
# RT_REQUEST_INTERVAL env var (e.g. to slow CI down further, or 0 in tests).
REQUEST_INTERVAL = float(os.environ.get("RT_REQUEST_INTERVAL", "1.5"))

# Streamers we don't care about listing. RT renamed "Fandango at Home" to
# plain "Fandango" at some point; both spellings show up.
IGNORED_STREAMERS = {"Fandango at Home", "Fandango", "In Theaters"}

# Same service, two names depending on when RT last rebranded it.
STREAMER_ALIASES = {"HBO Max": "Max"}

# RT has started returning some genres as combined pairs. Split them so the
# site's filters stay consistent with everything scraped before the change.
GENRE_ALIASES = {
	"Mystery & Thriller": ["Mystery", "Thriller"],
	"Sci-Fi & Fantasy": ["Sci-Fi", "Fantasy"],
	"Music & Musical": ["Music", "Musical"],
	"Biography & History": ["Biography", "History"],
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Wall-clock time of the last request, so _get can space the next one out.
_last_request = 0.0


class MovieNotFound(Exception):
	'''Raised when a title can't be located on Rotten Tomatoes at all.'''


def _get(url, **kwargs):
	'''
	SESSION.get, throttled to at most one request per REQUEST_INTERVAL.

	Centralising the sleep here means every caller is rate-limited the same way
	no matter how many requests a single movie lookup ends up making.
	'''
	global _last_request
	wait = REQUEST_INTERVAL - (time.monotonic() - _last_request)
	if wait > 0:
		time.sleep(wait)
	try:
		return SESSION.get(url, timeout=TIMEOUT, **kwargs)
	finally:
		_last_request = time.monotonic()


def fetch(url):
	'''
	GETs a url and returns soup, or None on 404 / persistent failure.

	Retries with backoff so a single flaky response doesn't fail the build.
	'''
	for attempt in range(RETRIES):
		try:
			response = _get(url)
		except requests.RequestException as e:
			print("    request failed (" + repr(e) + "), retrying")
		else:
			if response.status_code == 404:
				return None
			if response.ok:
				return BeautifulSoup(response.content, "html.parser")
			print("    HTTP " + str(response.status_code) + ", retrying")
		time.sleep(2 ** attempt)
	return None


def slugify(title):
	'''
	Turns a movie title into the Rotten Tomatoes url slug form.
	'''
	# Decompose accents to their ascii base character (é -> e).
	text = unicodedata.normalize("NFKD", title)
	text = "".join(c for c in text if not unicodedata.combining(c))
	text = text.lower()
	text = text.replace("&", " and ")
	# RT drops apostrophes rather than splitting on them: "Molly's Game" is
	# /m/mollys_game, not /m/molly_s_game.
	text = re.sub(r"['’]", "", text)
	text = re.sub(r"[^a-z0-9]+", " ", text)
	return "_".join(text.split())


def slug_candidates(title, year):
	'''
	Yields plausible RT urls, most specific first.

	RT is inconsistent about whether the year is appended and whether a leading
	article is kept, so we try the realistic combinations before searching.
	'''
	slug = slugify(title)
	variants = [slug]

	stripped = re.sub(r"^(the|a|an)_", "", slug)
	if stripped != slug:
		variants.append(stripped)

	for variant in variants:
		yield RT_BASE + "/m/" + variant + "_" + str(year)
	for variant in variants:
		yield RT_BASE + "/m/" + variant


def search(title, year):
	'''
	Falls back to RT's search page, returning the url of a matching result.

	Only accepts a result whose release year is within a year of ours -- RT
	sometimes lists the festival year rather than the release year.
	'''
	url = RT_BASE + "/search?search=" + urllib.parse.quote(title)
	soup = fetch(url)
	if soup is None:
		return None

	for row in soup.find_all("search-page-media-row"):
		link = row.find("a", href=True)
		if not link:
			continue
		found_year = row.get("release-year")
		try:
			if abs(int(found_year) - int(year)) > 1:
				continue
		except (TypeError, ValueError):
			continue
		return link["href"]
	return None


def text_of(soup, tag, **attrs):
	'''
	Returns the stripped text of the first matching node, or None.
	'''
	node = soup.find(tag, attrs) if attrs else soup.find(tag)
	return node.text.strip() if node else None


def find_movie_page(title, year):
	'''
	Locates the RT page for a title, returning (url, soup).

	A page only counts as a match if it actually carries a critics score --
	that rules out RT's "coming soon" and disambiguation stubs.
	'''
	for url in slug_candidates(title, year):
		soup = fetch(url)
		if soup is not None and text_of(soup, "rt-text", slot="critics-score"):
			return url, soup

	url = search(title, year)
	if url:
		if url.startswith("/"):
			url = RT_BASE + url
		soup = fetch(url)
		if soup is not None and text_of(soup, "rt-text", slot="critics-score"):
			return url, soup

	raise MovieNotFound(title + " (" + str(year) + ")")


def poster_path(title):
	'''
	Where a title's poster lives on disk.

	Titles made entirely of punctuation would otherwise collapse to an empty
	name and write a hidden ".jpg", so fall back to the url slug.
	'''
	name = re.sub(r"[^\w]", "", title) or slugify(title) or "untitled"
	return POSTER_DIR + "/" + name + ".jpg"


def optimize_poster(path):
	'''
	Downscales a poster in place. RT hands out originals up to 15MB, which is
	absurd for something displayed a few hundred pixels wide.
	'''
	try:
		with Image.open(path) as img:
			img = img.convert("RGB")
			if img.width > POSTER_WIDTH:
				height = round(img.height * POSTER_WIDTH / img.width)
				img = img.resize((POSTER_WIDTH, height), Image.LANCZOS)
			img.save(path, "JPEG", quality=POSTER_QUALITY, optimize=True, progressive=True)
	except (OSError, ValueError) as e:
		print("    warning: couldn't optimize " + path + " (" + repr(e) + ")")


def download_poster(url, path):
	'''
	Downloads a poster if we don't already have it. Returns True on success.
	'''
	if os.path.isfile(path):
		return True
	if not url:
		return False

	for attempt in range(RETRIES):
		try:
			response = _get(url)
			response.raise_for_status()
		except requests.RequestException as e:
			print("    poster download failed (" + repr(e) + "), retrying")
			time.sleep(2 ** attempt)
			continue
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, "wb") as f:
			f.write(response.content)
		optimize_poster(path)
		return True
	return False


def parse_page(soup):
	'''
	Pulls the fields we care about out of an RT movie page.

	Shared by scrape() and refresh() so both read the page the same way.
	'''
	synopsis = text_of(soup, "rt-text", slot="content") or ""
	# Get rid of stupid actor names in synopsis!
	synopsis = re.sub(r"[^,]\([^()]*\)", "", synopsis)
	synopsis = " ".join(synopsis.split())

	genres = []
	for node in soup.find_all("rt-text", {"slot": "metadata-genre"}):
		for genre in GENRE_ALIASES.get(node.text.strip(), [node.text.strip()]):
			if genre and genre not in genres:
				genres.append(genre)

	streamers = []
	for node in soup.find_all("where-to-watch-meta"):
		name = node.text.strip()
		name = STREAMER_ALIASES.get(name, name)
		# No one cares about theaters anymore!
		if name and name not in IGNORED_STREAMERS and name not in streamers:
			streamers.append(name)

	return {
		"critics": text_of(soup, "rt-text", slot="critics-score"),
		"audience": text_of(soup, "rt-text", slot="audience-score"),
		"synopsis": synopsis,
		"genres": genres,
		"streamers": streamers,
	}


def scrape(title, year):
	'''
	Returns a dict of movie data, or raises MovieNotFound.

	Every field except the score is optional -- a missing synopsis or genre
	list shouldn't sink an otherwise good entry.
	'''
	url, soup = find_movie_page(title, year)
	movie = parse_page(soup)

	poster_node = soup.find("rt-img", {"slot": "poster-image"})
	poster_url = poster_node.get("src") if poster_node else None
	path = poster_path(title)
	if not download_poster(poster_url, path):
		print("    warning: no poster for " + title)
		path = None

	movie.update({"title": title, "year": str(year), "url": url, "poster": path})
	return movie


def refresh(movie):
	'''
	Re-reads an already-scraped movie's RT page for changed scores/streamers.

	Goes straight to the stored url -- no slug guessing -- and falls back to a
	full lookup only if that url has since moved. Returns the fields that
	changed, or raises MovieNotFound.
	'''
	title, year = movie["title"], movie.get("year", "")
	soup = None
	url = movie.get("url")

	if url:
		soup = fetch(url)
		if soup is not None and not text_of(soup, "rt-text", slot="critics-score"):
			soup = None

	if soup is None:
		# The page moved or went away; re-locate it the slow way.
		url, soup = find_movie_page(title, year)

	fresh = parse_page(soup)
	fresh["url"] = url
	return fresh
