'''
Offline tests for the MovieRex build. Run with: python test_scraper.py

These deliberately don't touch the network -- they cover the parts that break
silently (url slugs, sorting keys, escaping, idempotent rendering). For a live
check against Rotten Tomatoes, run: python test_scraper.py --live
'''

import sys

import rt_scraper
import update_html


def check(label, got, want):
	if got != want:
		print("FAIL " + label + "\n  got:  " + repr(got) + "\n  want: " + repr(want))
		return 1
	print("ok   " + label)
	return 0


def test_slugify():
	fails = 0
	fails += check("slugify: plain", rt_scraper.slugify("Zodiac"), "zodiac")
	fails += check("slugify: comma", rt_scraper.slugify("Three Billboards Outside Ebbing, Missouri"),
		"three_billboards_outside_ebbing_missouri")
	fails += check("slugify: slash", rt_scraper.slugify("Birth/Rebirth"), "birth_rebirth")
	fails += check("slugify: accents", rt_scraper.slugify("Amélie"), "amelie")
	fails += check("slugify: ampersand", rt_scraper.slugify("Dungeons & Dragons"), "dungeons_and_dragons")
	fails += check("slugify: apostrophe", rt_scraper.slugify("The Devil's Bath"), "the_devils_bath")
	return fails


def test_slug_candidates():
	got = list(rt_scraper.slug_candidates("The Prestige", "2006"))
	want = [
		rt_scraper.RT_BASE + "/m/the_prestige_2006",
		rt_scraper.RT_BASE + "/m/prestige_2006",
		rt_scraper.RT_BASE + "/m/the_prestige",
		rt_scraper.RT_BASE + "/m/prestige",
	]
	# The real RT url for this one is /m/prestige, so the article-stripped
	# variant has to be in the list or we'd fall through to search every time.
	return check("slug_candidates: article variants", got, want)


def test_sort_key():
	fails = 0
	fails += check("sort_key: strips 'The'", update_html.sort_key("The Usual Suspects"), "usual suspects")
	fails += check("sort_key: strips 'A'", update_html.sort_key("A Quiet Place"), "quiet place")
	fails += check("sort_key: keeps other words", update_html.sort_key("Theater Camp"), "theater camp")
	return fails


def test_percent():
	fails = 0
	fails += check("percent: strips sign", update_html.percent("91%"), "91")
	fails += check("percent: empty", update_html.percent(""), "")
	fails += check("percent: none", update_html.percent(None), "")
	return fails


def test_escaping():
	movie = {
		"title": 'The "Quoted" <Movie>',
		"year": "2020",
		"critics": "91%",
		"audience": "80%",
		"genres": ["Drama"],
		"streamers": [],
		"poster": "img/movies/x.jpg",
		"url": "https://example.com",
		"synopsis": 'He said "hi" & left <script>alert(1)</script>',
	}
	card = update_html.render_card(movie, 0)
	fails = 0
	fails += check("escaping: no raw script tag", "<script>" in card, False)
	fails += check("escaping: quotes encoded", '"Quoted"' in card, False)
	fails += check("escaping: ampersand encoded", "&amp;" in card, True)
	return fails


def test_replace_region_idempotent():
	'''
	The build must be re-runnable -- this is what broke the original script,
	which appended a fresh copy of every movie on each run.
	'''
	template = "<div>\n<!-- CARDS -->\n<!-- /CARDS -->\n</div>"
	once = update_html.replace_region(template, "CARDS", "AAA\n")
	twice = update_html.replace_region(once, "CARDS", "AAA\n")
	fails = 0
	fails += check("replace_region: inserts", "AAA" in once, True)
	fails += check("replace_region: idempotent", twice, once)
	# Content containing a closing tag must not confuse the region boundaries.
	tricky = update_html.replace_region(template, "CARDS", "<span>x</span>\n")
	again = update_html.replace_region(tricky, "CARDS", "<span>x</span>\n")
	fails += check("replace_region: idempotent with tags", again, tricky)
	return fails


def test_live():
	'''
	Hits Rotten Tomatoes. Slow and network-dependent, so it's opt-in.
	'''
	fails = 0
	for title, year in [("The Prestige", "2006"), ("Zodiac", "2007")]:
		try:
			data = rt_scraper.scrape(title, year)
		except Exception as e:
			print("FAIL live: " + title + " raised " + repr(e))
			fails += 1
			continue
		fails += check("live: " + title + " has a score", bool(data["critics"]), True)
		fails += check("live: " + title + " has a synopsis", len(data["synopsis"]) > 20, True)

	try:
		rt_scraper.scrape("Definitely Not A Real Film Zzz", "1999")
	except rt_scraper.MovieNotFound:
		print("ok   live: unknown title raises MovieNotFound")
	except Exception as e:
		print("FAIL live: unknown title raised " + repr(e) + ", expected MovieNotFound")
		fails += 1
	else:
		print("FAIL live: unknown title did not raise")
		fails += 1
	return fails


def main():
	fails = 0
	fails += test_slugify()
	fails += test_slug_candidates()
	fails += test_sort_key()
	fails += test_percent()
	fails += test_escaping()
	fails += test_replace_region_idempotent()

	if "--live" in sys.argv:
		fails += test_live()

	print("\n" + ("FAILED: " + str(fails) + " check(s)" if fails else "all checks passed"))
	sys.exit(1 if fails else 0)


if __name__ == "__main__":
	main()
