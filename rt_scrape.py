import rottentomatoes as rt
import os
import urllib.request
import numpy as np
import re

Movies_file="Movies.txt"
url_file="MovieURLs.txt"

with open("index.html", "r") as f:
    contents = f.readlines()


# TODO: first try to open movie_year url, then just movie

movies = open(Movies_file,'r')
for i,mov in enumerate(movies):
	# mov = mov[:-1]
	print(rt.tomatometer(mov))
	movie = rt.Movie(mov[:-1])
	genres = movie.genres
	score = movie.tomatometer
	audiencescore = movie.audience_score
	synopsis   = movie.synopsis
	image = movie.image
	stream = movie.streaming
	movie_url = movie.url

	synopsis = re.sub(r'[^,]\([^()]*\)', '', synopsis)

	if 'Fandango at Home' in stream:
		stream.remove('Fandango at Home')
	if 'In Theaters' in stream:
		stream.remove('In Theaters')

	img_fname = 'img/movies/'+mov[:-1].replace(' ','')+'.jpg'
	if not os.path.isfile(img_fname):
		# TODO: fix image link returned by rt scraper
		urllib.request.urlretrieve(urllib.parse.quote(image), img_fname)

	img_width  = 175
	img_height = 260
	print( score, stream)

	movie_html  = "   <li data-Filters=\""+', '.join(genres)+", "+', '.join(stream)+"\">"
	movie_html += "<strong>"+mov[:-1]+"</strong></strong>\n"
	movie_html += " <button class=\"myBtn_multi\">"
	movie_html += "<img src=\""+img_fname+"\" width="+str(img_width)+" height="+str(img_height)+"></button></li>\n"
	movie_html += " <div class=\"modal modal_multi\"><div class=\"modal-content\">\n"
	movie_html += "       <span class=\"close close_multi\">&times;</span>"
	movie_html += "<div class=\"left\"><img src=\""+img_fname+"\" width="+str(img_width)+" height="+str(img_height)+"></div>\n"
	movie_html += "        <div class=\"left\"><h2>"+mov[:-1]+"</h2>\n"
	movie_html += "        <a href=\""+movie_url+"\" target=\"_blank\">   <div class=\"flex-container\">"
	movie_html += " <img id='tomato' src=\"img/logos/rt_tomato.png\"> "+str(score)+"% <img id='tomato' src=\"img/logos/rt_popcorn.png\"> "+str(audiencescore)+"%"
	movie_html += "</div></a>\n<p>"+synopsis+"\n\n <div class=\"flex-container\" id=\"streamers\">"

	for streamer in stream:
		movie_html += "<img id=\"streamers\" src=\"img/logos/"+streamer.replace(" ","")+".png\"> "

	movie_html += "</div></p></div>\n</div></div>\n\n"

	print(movie_html)
	contents.insert(111, movie_html)

with open("index.html", "w") as f:
    contents = "".join(contents)
    f.write(contents)
