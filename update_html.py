from rt_scraper import Movie

Movies_file="Movies.txt"

with open("index.html", "r") as f:
    contents = f.readlines()

movies = open(Movies_file,'r')
for i,mov in enumerate(movies):
	
	mov = mov.split(' ')
	title = ' '.join(mov[:-1])
	year = mov[-1]
	print("processing: ",title,year)
	movie = Movie(title, year)
	movie_html = movie.generate_html()

	print(movie.synopsis)
	if movie_html:
		contents.insert(111, movie_html)

with open("index.html", "w") as f:
    contents = "".join(contents)
    f.write(contents)
