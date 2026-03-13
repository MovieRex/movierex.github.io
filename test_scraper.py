
import requests
from bs4 import BeautifulSoup
import re
from rt_scraper import Movie
import os
import urllib.request
import numpy as np


title = "The Prestige"
year = "2006"


print("processing: ",title,year)
movie = Movie(title, year)
movie_html = movie.generate_html()

print(movie.synopsis)



# URL = "https://www.rottentomatoes.com/m/blink_twice_2019"
# page = requests.get(URL)

# soup = BeautifulSoup(page.content, "html.parser")

# critics_score = soup.find('rt-text', {'slot':'critics-score'}).text 
# audience_score = soup.find('rt-text', {'slot':'audience-score'}).text
# synopsis = soup.find('rt-text', {'slot':'content'}).text
# poster_url = soup.find('rt-img', {'slot':'poster-image'})["src"]
# genres = [s.text for s in soup.find_all('rt-text', {'slot':'metadata-genre'})]
# streamers = [s.text.strip('\n') for s in soup.find_all('where-to-watch-meta')]
# # Get rid of stupid actor names in synopsis!
# synopsis = re.sub(r'[^,]\([^()]*\)', '', synopsis)

# print(critics_score)
# print(audience_score)
# print(synopsis)
# print(poster_url)
# print(genres)
# print(streamers)
