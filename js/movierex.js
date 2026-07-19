/* MovieRex — filtering, sorting and the detail modal. No dependencies. */

(function () {
	'use strict';

	var grid = document.getElementById('grid');
	var cards = Array.prototype.slice.call(grid.querySelectorAll('.card'));
	var sort = document.getElementById('sort');
	var count = document.getElementById('count');
	var reset = document.getElementById('reset');
	var empty = document.getElementById('empty');
	var chips = Array.prototype.slice.call(document.querySelectorAll('.chip'));

	var modal = document.getElementById('modal');
	var lastFocused = null;

	/* ---------- filtering ---------- */

	function selected(kind) {
		return chips
			.filter(function (c) {
				return c.dataset.kind === kind && c.getAttribute('aria-pressed') === 'true';
			})
			.map(function (c) {
				return c.dataset.value;
			});
	}

	function listOf(card, attr) {
		var raw = card.dataset[attr];
		return raw ? raw.split('|') : [];
	}

	function apply() {
		var genres = selected('genre');
		var streamers = selected('streamer');
		var shown = 0;

		cards.forEach(function (card) {
			var cardGenres = listOf(card, 'genres');
			var cardStreamers = listOf(card, 'streamers');

			// Genres are AND (narrow down), streamers are OR (any of these services).
			var okGenre = genres.every(function (g) {
				return cardGenres.indexOf(g) !== -1;
			});
			var okStreamer =
				streamers.length === 0 ||
				streamers.some(function (s) {
					return cardStreamers.indexOf(s) !== -1;
				});
			var visible = okGenre && okStreamer;
			card.hidden = !visible;
			if (visible) {
				shown++;
			}
		});

		count.textContent = shown === cards.length
			? cards.length + ' movies'
			: shown + ' of ' + cards.length;
		empty.hidden = shown !== 0;

		reset.hidden = genres.length === 0 && streamers.length === 0;
	}

	/* ---------- sorting ---------- */

	function score(card, attr) {
		var value = parseInt(card.dataset[attr], 10);
		return isNaN(value) ? -1 : value;
	}

	function applySort() {
		var mode = sort.value;
		var ordered = cards.slice();

		ordered.sort(function (a, b) {
			if (mode === 'title') {
				return a.dataset.sortTitle.localeCompare(b.dataset.sortTitle);
			}
			if (mode === 'year') {
				return b.dataset.year - a.dataset.year;
			}
			if (mode === 'critics') {
				return score(b, 'critics') - score(a, 'critics');
			}
			if (mode === 'audience') {
				return score(b, 'audience') - score(a, 'audience');
			}
			// 'added' — the order they appear in Movies.txt, newest first.
			return a.dataset.index - b.dataset.index;
		});

		var frag = document.createDocumentFragment();
		ordered.forEach(function (card) {
			frag.appendChild(card);
		});
		grid.appendChild(frag);
	}

	/* ---------- modal ---------- */

	function pct(value) {
		return value ? value + '%' : '--';
	}

	function logoFor(name) {
		// Logo filenames drop spaces: "Prime Video" -> "PrimeVideo.png".
		return 'img/logos/' + name.replace(/\s+/g, '') + '.png';
	}

	function open(card) {
		lastFocused = card;

		modal.querySelector('.poster-lg').src = card.dataset.poster;
		modal.querySelector('.poster-lg').alt = card.dataset.title + ' poster';
		modal.querySelector('h2').textContent = card.dataset.title;
		modal.querySelector('.modal-year').textContent = card.dataset.year;
		modal.querySelector('.synopsis').textContent =
			card.dataset.synopsis || 'No synopsis available.';

		var link = modal.querySelector('.scores a');
		link.href = card.dataset.url;
		// The data attributes hold bare numbers so sorting can compare them.
		modal.querySelector('.critics-score').textContent = pct(card.dataset.critics);
		modal.querySelector('.audience-score').textContent = pct(card.dataset.audience);

		var genreRow = modal.querySelector('.genre-row');
		genreRow.innerHTML = '';
		listOf(card, 'genres').forEach(function (g) {
			var el = document.createElement('span');
			el.className = 'tag';
			el.textContent = g;
			genreRow.appendChild(el);
		});

		var streamerRow = modal.querySelector('.streamer-row');
		streamerRow.innerHTML = '';
		var streamers = listOf(card, 'streamers');
		if (streamers.length === 0) {
			var none = document.createElement('span');
			none.className = 'none';
			none.textContent = 'Not currently streaming';
			streamerRow.appendChild(none);
		}
		streamers.forEach(function (name) {
			var img = document.createElement('img');
			img.src = logoFor(name);
			img.alt = name;
			img.loading = 'lazy';
			// Services without a logo file fall back to a plain text chip.
			img.onerror = function () {
				var el = document.createElement('span');
				el.className = 'tag';
				el.textContent = name;
				streamerRow.replaceChild(el, img);
			};
			streamerRow.appendChild(img);
		});

		modal.showModal();
	}

	/* ---------- wiring ---------- */

	chips.forEach(function (chip) {
		chip.addEventListener('click', function () {
			var on = chip.getAttribute('aria-pressed') === 'true';
			chip.setAttribute('aria-pressed', on ? 'false' : 'true');
			apply();
		});
	});

	sort.addEventListener('change', applySort);

	reset.addEventListener('click', function () {
		chips.forEach(function (c) {
			c.setAttribute('aria-pressed', 'false');
		});
		apply();
	});

	grid.addEventListener('click', function (e) {
		var card = e.target.closest('.card');
		if (card) {
			open(card);
		}
	});

	modal.querySelector('.modal-close').addEventListener('click', function () {
		modal.close();
	});

	// Click outside the content closes it.
	modal.addEventListener('click', function (e) {
		if (e.target === modal) {
			modal.close();
		}
	});

	modal.addEventListener('close', function () {
		if (lastFocused) {
			lastFocused.focus();
		}
	});

	apply();
	applySort();
})();
