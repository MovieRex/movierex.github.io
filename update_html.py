'''
Rebuilds index.html from Movies.txt. Written by Brooke Polak.

Idempotent: the movie grid and the filter chips are regenerated from scratch on
every run, so running it twice never duplicates anything.

Scraped data is cached in movies.json, so only titles newly added to Movies.txt
hit Rotten Tomatoes. Because the cache holds data rather than markup, changing
the template below costs nothing -- no re-scraping needed. Delete a key (or the
whole file) to force a refresh of a movie.
'''

import html
import json
import os
import re
import sys

import rt_scraper

MOVIES_FILE = "Movies.txt"
DATA_FILE = "movies.json"
INDEX_FILE = "index.html"

LOGO_DIR = "img/logos"


def read_movies():
	'''
	Returns [(title, year)] in Movies.txt order, skipping blank lines.
	'''
	movies = []
	with open(MOVIES_FILE) as f:
		for line in f:
			line = line.strip()
			if not line:
				continue
			title, _, year = line.rpartition(" ")
			if not title or not year.isdigit():
				print("Warning: can't parse line, skipping: " + line)
				continue
			# Catches typos like "Prisoners 2913", which otherwise scrape fine
			# via the no-year fallback and then sort to the wrong end.
			if not 1900 <= int(year) <= 2100:
				print("Warning: implausible year, check this line: " + line)
			movies.append((title, year))
	return movies


def load_data():
	if not os.path.isfile(DATA_FILE):
		return {}
	with open(DATA_FILE) as f:
		return json.load(f)


def save_data(data):
	with open(DATA_FILE, "w") as f:
		json.dump(data, f, indent=1, sort_keys=True, ensure_ascii=False)
		f.write("\n")


def esc(value):
	return html.escape(str(value or ""), quote=True)


def sort_key(title):
	'''
	Title stripped of a leading article, for A-Z sorting.
	'''
	return re.sub(r"^(the|a|an)\s+", "", title.lower())


def percent(value):
	'''
	Returns the bare number from a score like "91%", for numeric sorting.
	'''
	match = re.search(r"\d+", value or "")
	return match.group(0) if match else ""


def render_card(movie, index):
	'''
	Returns the markup for one poster card.

	Everything the modal needs rides along in data attributes, so there's a
	single source of truth in the DOM and no parallel JSON blob to keep in sync.
	'''
	title = movie["title"]

	attrs = [
		('class', 'card'),
		('type', 'button'),
		('data-index', index),
		('data-title', title),
		('data-year', movie.get("year", "")),
		('data-sort-title', sort_key(title)),
		('data-critics', percent(movie.get("critics"))),
		('data-audience', percent(movie.get("audience"))),
		('data-genres', "|".join(movie.get("genres", []))),
		('data-streamers', "|".join(movie.get("streamers", []))),
		('data-poster', movie.get("poster", "")),
		('data-url', movie.get("url", "")),
		('data-synopsis', movie.get("synopsis", "")),
	]
	opening = "<button " + " ".join(k + '="' + esc(v) + '"' for k, v in attrs) + ">"

	score = ""
	if movie.get("critics"):
		score = (
			'\n\t\t\t\t<span class="score"><img src="' + LOGO_DIR + '/rt_tomato.png" alt="Tomatometer">'
			+ esc(movie["critics"]) + "</span>"
		)

	return (
		"\t\t\t" + opening + "\n"
		'\t\t\t\t<div class="poster">\n'
		'\t\t\t\t\t<img src="' + esc(movie.get("poster", "")) + '" alt="' + esc(title)
		+ ' poster" loading="lazy" decoding="async" width="400" height="600">'
		+ score + "\n"
		"\t\t\t\t</div>\n"
		'\t\t\t\t<div class="meta">\n'
		'\t\t\t\t\t<div class="title">' + esc(title) + "</div>\n"
		'\t\t\t\t\t<div class="year">' + esc(movie.get("year", "")) + "</div>\n"
		"\t\t\t\t</div>\n"
		"\t\t\t</button>\n"
	)


def render_chip(kind, value, n, logo=None):
	'''
	Returns the markup for one filter chip.
	'''
	icon = ""
	if logo:
		icon = '<img src="' + esc(logo) + '" alt="" loading="lazy">'
	return (
		'\t\t\t\t<button class="chip" type="button" aria-pressed="false" data-kind="'
		+ kind + '" data-value="' + esc(value) + '">'
		+ icon + esc(value) + '<span class="n">' + str(n) + "</span></button>\n"
	)


def render_chips(kind, movies, field, with_logos=False):
	'''
	Builds the chip row for a facet, most common first.
	'''
	counts = {}
	for movie in movies:
		for value in movie.get(field, []):
			counts[value] = counts.get(value, 0) + 1

	ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

	out = ""
	for value, n in ordered:
		logo = None
		if with_logos:
			candidate = LOGO_DIR + "/" + value.replace(" ", "") + ".png"
			# Newly-added services won't have a logo file; those render as text.
			logo = candidate if os.path.isfile(candidate) else None
		out += render_chip(kind, value, n, logo)
	return out


def replace_region(contents, marker, body):
	'''
	Replaces everything between a pair of marker comments.

	Both markers are kept so the region can be rebuilt on the next run -- which
	is what makes repeated runs idempotent rather than cumulative.
	'''
	open_token = "<!-- " + marker + " -->"
	close_token = "<!-- /" + marker + " -->"

	start = contents.index(open_token) + len(open_token)
	end = contents.index(close_token, start)
	return contents[:start] + "\n" + body + contents[end:]


def main():
	wanted = read_movies()
	data = load_data()
	failed = []

	for title, year in wanted:
		key = title + "|" + year
		if key in data:
			continue
		print("scraping: " + title + " " + year)
		try:
			data[key] = rt_scraper.scrape(title, year)
		except rt_scraper.MovieNotFound:
			print("  not found on Rotten Tomatoes")
			failed.append(title + " " + year)
		except Exception as e:
			print("  failed: " + repr(e))
			failed.append(title + " " + year)

	save_data(data)

	# Newest additions to Movies.txt show up first on the page.
	movies = [data[t + "|" + y] for t, y in wanted if t + "|" + y in data]
	movies.reverse()

	cards = "".join(render_card(m, i) for i, m in enumerate(movies))
	genres = render_chips("genre", movies, "genres")
	streamers = render_chips("streamer", movies, "streamers", with_logos=True)

	with open(INDEX_FILE) as f:
		contents = f.read()

	contents = replace_region(contents, "MOVIE_CARDS", cards)
	contents = replace_region(contents, "GENRE_CHIPS", genres)
	contents = replace_region(contents, "STREAMER_CHIPS", streamers)

	with open(INDEX_FILE, "w") as f:
		f.write(contents)

	print("wrote " + str(len(movies)) + " movies to " + INDEX_FILE)
	if failed:
		print("Could not scrape: " + ", ".join(failed))
		sys.exit(1)


if __name__ == "__main__":
	main()
