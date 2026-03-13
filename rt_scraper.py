import requests
from bs4 import BeautifulSoup
import re
import os
import urllib.request

class Movie:
    '''
    Class that holds movie information scraped from rotten tomatoes
    for MovieRex. Written by Brooke Polak.
    '''
    def __init__(self, title, year):
        '''
        Sets all the necessary class properties. also, if its a new movie, 
        download a poster for the website.        
        
        :param self: what is self? who am i?
        :param title: movie title
        :param year: movie year -- must break degeneracies!
        '''
        
        rt_url = 'https://www.rottentomatoes.com/m/'
        
        self.title = title
        self.year = year
        
        movie_url_suffix = "_".join(self.title.lower().split(' '))
        # Get rid of any punctuation in movie title
        movie_url_suffix = re.sub(r'&','and',movie_url_suffix)
        movie_url_suffix = re.sub(r'[^\w\s]', '', movie_url_suffix)
        movie_url_suffix = self.replace_accents_with_ascii(movie_url_suffix)
        
        try:
            self.movie_url = rt_url+movie_url_suffix+"_"+str(self.year)
            page = requests.get(self.movie_url)
            soup = BeautifulSoup(page.content, "html.parser")
            # this will be none and throw an error if we cant include year
            self.critics_score = soup.find('rt-text', {'slot':'critics-score'}).text
        except AttributeError:
            try:
                self.movie_url = rt_url+movie_url_suffix
                page = requests.get(self.movie_url)
                soup = BeautifulSoup(page.content, "html.parser")
                self.critics_score = soup.find('rt-text', {'slot':'critics-score'}).text
            except AttributeError:
                # If we STILLL cant find it! use the search function.
                try:
                    rt_search_url = "https://www.rottentomatoes.com/search?search="+re.sub('_','%20',movie_url_suffix)
                    page = requests.get(rt_search_url)
                    search_soup = BeautifulSoup(page.content, "html.parser")
                    search = search_soup.find('search-page-media-row')
                    if int(search['release-year']) == int(self.year):
                        self.movie_url = search.find('a')['href']
                    page = requests.get(self.movie_url)
                    soup = BeautifulSoup(page.content, "html.parser")
                    self.critics_score = soup.find('rt-text', {'slot':'critics-score'}).text
                except AttributeError:
                    print('Warning: Movie not found! skipping')
                    return None

        print(self.movie_url)
        self.audience_score = soup.find('rt-text', {'slot':'audience-score'}).text
        self.synopsis = soup.find('rt-text', {'slot':'content'}).text
        self.poster_url = soup.find('rt-img', {'slot':'poster-image'})["src"]
        self.genres = [s.text for s in soup.find_all('rt-text', {'slot':'metadata-genre'})]
        self.streamers = [s.text.strip('\n') for s in soup.find_all('where-to-watch-meta')]
        # Get rid of stupid actor names in synopsis!
        self.synopsis = re.sub(r'[^,]\([^()]*\)', '', self.synopsis)
        
        # No one cares about theaters anymore! 
        if 'Fandango at Home' in self.streamers:
            self.streamers.remove('Fandango at Home')
        if 'In Theaters' in self.streamers:
            self.streamers.remove('In Theaters')
                

        # check to see if we need to download a movie poster
        self.img_fname = 'img/movies/'+self.title.replace(' ','')+'.jpg'
        if not os.path.isfile(self.img_fname):
            # TODO: fix image link returned by rt scraper
            urllib.request.urlretrieve(self.poster_url, self.img_fname)
        
        
    def generate_html(self):
        
        '''
        Returns the html for the movie container. 
        
        :param self: Description
        '''
        
        img_width  = 175
        img_height = 260
        
        movie_html  = "   <li data-Filters=\""+', '.join(self.genres)+", "+', '.join(self.streamers)+"\">"
        movie_html += "<strong>"+self.title+"</strong></strong>\n"
        movie_html += " <button class=\"myBtn_multi\">"
        movie_html += "<img src=\""+self.img_fname+"\" width="+str(img_width)+" height="+str(img_height)+"></button></li>\n"
        movie_html += " <div class=\"modal modal_multi\"><div class=\"modal-content\">\n"
        movie_html += "       <span class=\"close close_multi\">&times;</span>"
        movie_html += "<div class=\"left\"><img src=\""+self.img_fname+"\" width="+str(img_width)+" height="+str(img_height)+"></div>\n"
        movie_html += "        <div class=\"left\"><h2>"+self.title+"</h2>\n"
        movie_html += "        <a href=\""+self.movie_url+"\" target=\"_blank\">   <div class=\"flex-container\">"
        movie_html += " <img id='tomato' src=\"img/logos/rt_tomato.png\"> "+str(self.critics_score)
        movie_html += " <img id='tomato' src=\"img/logos/rt_popcorn.png\"> "+str(self.audience_score)
        movie_html += "</div></a>\n<p>"+self.synopsis+"\n\n <div class=\"flex-container\" id=\"streamers\">"

        for streamer in self.streamers:
                movie_html += "<img id=\"streamers\" src=\"img/logos/"+streamer.replace(" ","")+".png\"> "

        movie_html += "</div></p></div>\n</div></div>\n\n"
        
        return movie_html
        
    def replace_accents_with_ascii(self, text):
        '''
        Helper function for turning movie name into url
        
        :param text: Description
        '''
        replacements = {
            r'à|á|â|ã|ä|å': 'a',
            r'è|é|ê|ë': 'e',
            r'ì|í|î|ï': 'i',
            r'ò|ó|ô|õ|ö': 'o',
            r'ù|ú|û|ü': 'u',
            r'ý|ÿ': 'y',
            r'ç': 'c'
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text