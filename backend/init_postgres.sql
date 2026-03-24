-- PostgreSQL Schema for MovieGoer Database
-- Converted from SQL Server schema to PostgreSQL for Railway deployment
-- Run this script to initialize your Railway PostgreSQL database

-- Users table (equivalent to UserSchema.UserTable)
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    passwords_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Movies table (equivalent to MoviesSchema.MoviesTable)
CREATE TABLE IF NOT EXISTS movies (
    movie_id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    original_title VARCHAR(200),
    overview TEXT,
    runtime INTEGER CHECK (runtime > 0),
    language VARCHAR(50),
    country VARCHAR(50),
    age_rating VARCHAR(20),
    average_rating DECIMAL(4,2) CHECK (average_rating BETWEEN 0 AND 10),
    popularity_score DECIMAL(10,2) CHECK (popularity_score >= 0),
    poster_url VARCHAR(500),
    release_year INTEGER NOT NULL CHECK (release_year BETWEEN 1888 AND 2100)
);

-- Genres table (equivalent to GenreSchema.GenreTable)
CREATE TABLE IF NOT EXISTS genres (
    genre_id SERIAL PRIMARY KEY,
    genre_name VARCHAR(50) NOT NULL UNIQUE
);

-- Movie-Genres junction table (equivalent to GenreSchema.MovieGenresTable)
CREATE TABLE IF NOT EXISTS movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    genre_id INTEGER NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- Franchises table (equivalent to FranchiseSchema.FranchiseTable)
CREATE TABLE IF NOT EXISTS franchises (
    franchise_id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    media_franchise VARCHAR(50),
    sequel_franchise VARCHAR(50)
);

-- Ratings table (equivalent to RatingsSchema.RatingsTable)
CREATE TABLE IF NOT EXISTS ratings (
    rating_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
    rated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, movie_id)
);

-- Watch History table (equivalent to WatchHistorySchema.WatchHistoryTable)
CREATE TABLE IF NOT EXISTS watch_history (
    watchhistory_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    watched_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- User Preferences table (equivalent to PreferenceSchema.UserPreferenceTable)
CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    preferred_genre_id INTEGER REFERENCES genres(genre_id),
    preferred_language VARCHAR(50),
    preferred_country VARCHAR(50),
    min_runtime INTEGER CHECK (min_runtime >= 0),
    max_runtime INTEGER CHECK (max_runtime >= 0),
    preferred_age_rating VARCHAR(20),
    preference_weight DECIMAL(4,2) CHECK (preference_weight BETWEEN 0 AND 1),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Streaming Services table (equivalent to StreamingSchema.StreamingServicesTable)
CREATE TABLE IF NOT EXISTS streaming_services (
    streaming_service_id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL UNIQUE,
    logo_url VARCHAR(500),
    base_url VARCHAR(500)
);

-- Movie Streaming junction table (equivalent to StreamingSchema.MovieStreamingTable)
CREATE TABLE IF NOT EXISTS movie_streaming (
    moviestreaming_id SERIAL PRIMARY KEY,
    movie_id INTEGER NOT NULL REFERENCES movies(movie_id) ON DELETE CASCADE,
    streaming_service_id INTEGER NOT NULL REFERENCES streaming_services(streaming_service_id) ON DELETE CASCADE,
    streaming_url VARCHAR(500) NOT NULL,
    available_from TIMESTAMP,
    available_until TIMESTAMP,
    UNIQUE(movie_id, streaming_service_id)
);

-- ============================================
-- DATA INSERTS
-- ============================================

-- Insert Genres
INSERT INTO genres (genre_id, genre_name) VALUES
(1, 'Action'),
(2, 'Adventure'),
(3, 'Animation'),
(4, 'Crime'),
(5, 'Drama'),
(6, 'Fantasy'),
(7, 'Mystery'),
(8, 'Romance'),
(9, 'Sci-Fi'),
(10, 'Thriller'),
(11, 'Comedy'),
(12, 'Family'),
(13, 'Horror'),
(14, 'War'),
(15, 'Music');

-- Reset sequence for genres
SELECT setval('genres_genre_id_seq', (SELECT MAX(genre_id) FROM genres));

-- Insert Streaming Services
INSERT INTO streaming_services (streaming_service_id, service_name, logo_url, base_url) VALUES
(1, 'Netflix', 'https://images.justwatch.com/icon/207360008/s100/netflix.webp', 'https://www.netflix.com'),
(2, 'Hulu', 'https://images.justwatch.com/icon/116305230/s100/hulu.webp', 'https://www.hulu.com'),
(3, 'Disney+', 'https://images.justwatch.com/icon/147638351/s100/disneyplus.webp', 'https://www.disneyplus.com'),
(4, 'Prime Video', 'https://images.justwatch.com/icon/52449861/s100/amazonprimevideo.webp', 'https://www.primevideo.com'),
(5, 'Apple TV+', 'https://images.justwatch.com/icon/190848813/s100/appletvplus.webp', 'https://tv.apple.com'),
(6, 'Max', 'https://images.justwatch.com/icon/305458112/s100/max.webp', 'https://www.max.com'),
(7, 'Paramount+', 'https://images.justwatch.com/icon/232697473/s100/paramountplus.webp', 'https://www.paramountplus.com'),
(8, 'Peacock', 'https://images.justwatch.com/icon/194559929/s100/peacocktv.webp', 'https://www.peacocktv.com'),
(11, 'Fandango at Home', 'https://images.justwatch.com/icon/316322378/s100/fandangoathome.webp', 'https://athome.fandango.com'),
(12, 'Crunchyroll', 'https://tse3.mm.bing.net/th/id/OIP.oJdWMYML3f95_5bG1hJz0QHaEK?rs=1&pid=ImgDetMain&o=7&rm=3', 'https://www.crunchyroll.com');

SELECT setval('streaming_services_streaming_service_id_seq', (SELECT MAX(streaming_service_id) FROM streaming_services));

-- Insert Movies
INSERT INTO movies (movie_id, title, original_title, overview, runtime, language, country, age_rating, average_rating, popularity_score, poster_url, release_year) VALUES
(3, 'Inception', 'Inception', 'A thief who steals corporate secrets through dream-sharing technology is given the inverse task of planting an idea into the mind of a CEO.', 148, 'English', 'USA', 'PG-13', 4.80, 95.20, 'https://m.media-amazon.com/images/M/MV5BMjAxMzY3NjcxNF5BMl5BanBnXkFtZTcwNTI5OTM0Mw@@._V1_SX300.jpg', 2010),
(4, 'The Dark Knight', 'The Dark Knight', 'Batman faces the Joker, a criminal mastermind who plunges Gotham into chaos.', 152, 'English', 'USA', 'PG-13', 4.90, 98.40, 'https://m.media-amazon.com/images/S/pv-target-images/e9a43e647b2ca70e75a3c0af046c4dfdcd712380889779cbdc2c57d94ab63902.jpg', 2008),
(5, 'Interstellar', 'Interstellar', 'A team of explorers travels through a wormhole in space in an attempt to ensure humanity survival.', 169, 'English', 'USA', 'PG-13', 4.70, 96.10, 'https://m.media-amazon.com/images/M/MV5BZjdkOTU3MDktN2IxOS00OGEyLWFmMjktY2FiMmZkNWIyODZiXkEyXkFqcGdeQXVyMTMxODk2OTU@._V1_SX300.jpg', 2014),
(6, 'Parasite', 'Gisaengchung', 'A poor family schemes to become employed by a wealthy household.', 132, 'Korean', 'South Korea', 'R', 4.60, 90.70, 'https://m.media-amazon.com/images/M/MV5BYWZjMjk3ZTItODQ2ZC00NTY5LWE0ZDYtZTI3MjcwN2Q5NTVkXkEyXkFqcGdeQXVyODk4OTc3MTY@._V1_SX300.jpg', 2019),
(7, 'Spirited Away', 'Sen to Chihiro no kamikakushi', 'A young girl enters the world of spirits and must save her parents.', 125, 'Japanese', 'Japan', 'PG', 4.80, 88.90, 'https://www.themoviedb.org/t/p/original/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg', 2001),
(8, 'The Matrix', 'The Matrix', 'A computer hacker learns that reality is a simulation and joins a rebellion.', 136, 'English', 'USA', 'R', 4.70, 94.30, 'https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg', 1999),
(9, 'La La Land', 'La La Land', 'A musician and an aspiring actress fall in love while pursuing their dreams.', 128, 'English', 'USA', 'PG-13', 4.20, 82.50, 'https://www.themoviedb.org/t/p/original/6ibTJwSpzFT43rqtoy51PF54A9r.jpg', 2016),
(10, 'Whiplash', 'Whiplash', 'A promising young drummer enrolls at a cut-throat music conservatory.', 107, 'English', 'USA', 'R', 4.50, 84.70, 'https://m.media-amazon.com/images/M/MV5BOTA5NDZlZGUtMjAxOS00YTRkLTkwYmMtYWQ0NWEwZDZiNjEzXkEyXkFqcGdeQXVyMTMxODk2OTU@._V1_SX300.jpg', 2014),
(11, 'The Godfather', 'The Godfather', 'The patriarch of an organized crime dynasty transfers control to his son.', 175, 'English', 'USA', 'R', 4.90, 91.80, 'https://m.media-amazon.com/images/M/MV5BM2MyNjYxNmUtYTAwNi00MTYxLWJmNWYtYzZlODY3ZTk3OTFlXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX300.jpg', 1972),
(12, 'Pulp Fiction', 'Pulp Fiction', 'The lives of two mob hitmen and others intertwine in tales of violence and redemption.', 154, 'English', 'USA', 'R', 4.70, 89.40, 'https://m.media-amazon.com/images/M/MV5BNGNhMDIzZTUtNTBlZi00MTRlLWFjM2ItYzViMjE3YzI5MjljXkEyXkFqcGdeQXVyNzkwMjQ5NzM@._V1_SX300.jpg', 1994),
(13, 'Titanic', 'Titanic', 'A seventeen-year-old aristocrat falls in love with a kind but poor artist aboard the Titanic.', 194, 'English', 'USA', 'PG-13', 4.50, 93.10, 'https://m.media-amazon.com/images/M/MV5BMDdmZGU3NDQtY2E5My00ZTliLWIzOTUtMTY4ZGI1YjdiNjk3XkEyXkFqcGdeQXVyNTA4NzY1MzY@._V1_SX300.jpg', 1997),
(14, 'The Shawshank Redemption', 'The Shawshank Redemption', 'Two imprisoned men bond over a number of years.', 142, 'English', 'USA', 'R', 4.90, 92.60, 'https://image.tmdb.org/t/p/w500/q6y0Go1tsGEsmtFryDOJo3dEmqu.jpg', 1994),
(15, 'Avengers Endgame', 'Avengers Endgame', 'After the devastating events of Infinity War, the Avengers assemble once more.', 181, 'English', 'USA', 'PG-13', 4.40, 97.20, 'https://m.media-amazon.com/images/M/MV5BMTc5MDE2ODcwNV5BMl5BanBnXkFtZTgwMzI2NzQ2NzM@._V1_SX300.jpg', 2019),
(16, 'Toy Story', 'Toy Story', 'A cowboy doll is profoundly threatened by a new spaceman figure.', 81, 'English', 'USA', 'G', 4.40, 85.90, 'https://image.tmdb.org/t/p/original/wNRat1bU3abQtpInLJW8YxlPsER.jpg', 1995),
(17, 'Get Out', 'Get Out', 'A young man uncovers a disturbing secret when he visits his girlfriends family estate.', 104, 'English', 'USA', 'R', 4.30, 87.80, 'https://th.bing.com/th/id/OIP.UqB7SvY89HsRVL0QvtpEDgHaK9?w=115&h=180&c=7&r=0&o=7&dpr=1.3&pid=1.7&rm=3', 2017),
(18, 'The Lord of the Rings The Fellowship of the Ring', 'The Lord of the Rings The Fellowship of the Ring', 'A meek Hobbit and eight companions set out on a journey to destroy a powerful ring.', 178, 'English', 'New Zealand', 'PG-13', 4.80, 94.00, 'https://tse3.mm.bing.net/th/id/OIP.yjd-NpYfWTAaoIP4ZP01lgHaLC?rs=1&pid=ImgDetMain&o=7&rm=3', 2001),
(19, 'The Lord of the Rings The Two Towers', 'The Lord of the Rings The Two Towers', 'The Fellowship is broken but continues the quest against Sauron.', 179, 'English', 'New Zealand', 'PG-13', 4.70, 93.50, 'https://tse3.mm.bing.net/th/id/OIP.7QM-e0m3iWvSd7aY3O2shQHaLH?rs=1&pid=ImgDetMain&o=7&rm=3', 2002),
(20, 'The Lord of the Rings The Return of the King', 'The Lord of the Rings The Return of the King', 'Gandalf and Aragorn lead the World of Men against Sauron army.', 201, 'English', 'New Zealand', 'PG-13', 4.90, 97.00, 'https://image.tmdb.org/t/p/original/uexxR7Kw1qYbZk0RYaF9Rx5ykbj.jpg', 2003),
(21, 'Forrest Gump', 'Forrest Gump', 'The presidencies of Kennedy and Johnson and more unfold through the perspective of Forrest Gump.', 142, 'English', 'USA', 'PG-13', 4.60, 90.20, 'https://m.media-amazon.com/images/M/MV5BNWIwODRlZTUtY2U3ZS00Yzg1LWJhNzYtMmZiYmEyNmU1NjMzXkEyXkFqcGdeQXVyMTQxNzMzNDI@._V1_SX300.jpg', 1994),
(22, 'Fight Club', 'Fight Club', 'An insomniac office worker forms an underground fight club with a soap maker.', 139, 'English', 'USA', 'R', 4.60, 91.10, 'https://m.media-amazon.com/images/M/MV5BNDIzNDU0YzEtYzE5Ni00ZjlkLTk5ZjgtNjM3NWE4YzA3Nzk3XkEyXkFqcGdeQXVyMjUzOTY1NTc@._V1_SX300.jpg', 1999),
(23, 'The Silence of the Lambs', 'The Silence of the Lambs', 'A young FBI cadet seeks the help of Dr. Hannibal Lecter.', 118, 'English', 'USA', 'R', 4.50, 86.80, 'https://m.media-amazon.com/images/M/MV5BNjNhZTk0ZmEtNjJhMi00YzFlLWE1MmEtYzM1M2ZmMGMwMTU4XkEyXkFqcGdeQXVyNjU0OTQ0OTY@._V1_SX300.jpg', 1991),
(24, 'Se7en', 'Se7en', 'Two detectives hunt a serial killer who uses the seven deadly sins as motives.', 127, 'English', 'USA', 'R', 4.60, 88.40, 'https://image.tmdb.org/t/p/w500/6yoghtyTpznpBik8EngEmJskVUO.jpg', 1995),
(25, 'The Social Network', 'The Social Network', 'The story of the founding of Facebook and the resulting lawsuits.', 120, 'English', 'USA', 'PG-13', 4.20, 80.40, 'https://www.themoviedb.org/t/p/original/n0ybibhJtQ5icDqTp8eRytcIHJx.jpg', 2010),
(26, 'Coco', 'Coco', 'Aspiring musician Miguel enters the Land of the Dead to find his ancestor.', 105, 'English', 'USA', 'PG', 4.60, 86.50, 'https://lumiere-a.akamaihd.net/v1/images/au_pixar_coco_movie_poster_9bf4bb18.jpeg', 2017),
(27, 'Up', 'Up', 'An old man ties thousands of balloons to his house and flies away.', 96, 'English', 'USA', 'PG', 4.50, 84.60, 'https://image.tmdb.org/t/p/w500/vpbaStTMt8qqXaEgnOR2EE4DNJk.jpg', 2009),
(28, 'Inside Out', 'Inside Out', 'After moving to a new city, a young girls emotions guide her through life.', 95, 'English', 'USA', 'PG', 4.50, 85.20, 'https://image.tmdb.org/t/p/original/u5Ut5uygWnTRWGRoPVzlLsetiIp.jpg', 2015),
(29, 'The Lion King', 'The Lion King', 'Lion prince Simba and his father are targeted by his bitter uncle.', 88, 'English', 'USA', 'G', 4.70, 89.70, 'https://tse1.explicit.bing.net/th/id/OIP.9yxvUHiTWP-sEgbvczFKYQHaLH?rs=1&pid=ImgDetMain&o=7&rm=3', 1994),
(30, 'Gladiator', 'Gladiator', 'A former Roman general sets out to exact vengeance against the corrupt emperor.', 155, 'English', 'USA', 'R', 4.50, 87.10, 'https://www.themoviedb.org/t/p/original/ty8TGRuvJLPUmAR1H1nRIsgwvim.jpg', 2000),
(31, 'The Prestige', 'The Prestige', 'Two rival magicians engage in a battle to create the ultimate illusion.', 130, 'English', 'USA', 'PG-13', 4.50, 83.80, 'https://m.media-amazon.com/images/M/MV5BMjA4NDI0MTIxNF5BMl5BanBnXkFtZTYwNTM0MzY2._V1_SX300.jpg', 2006),
(32, 'Memento', 'Memento', 'A man with short-term memory loss attempts to track down his wifes murderer.', 113, 'English', 'USA', 'R', 4.40, 81.60, 'https://image.tmdb.org/t/p/w500/fKTPH2WvH8nHTXeBYBVhawtRqtR.jpg', 2000),
(33, 'Joker', 'Joker', 'A mentally troubled comedian embarks on a downward spiral of social revolution.', 122, 'English', 'USA', 'R', 4.30, 94.60, 'https://image.tmdb.org/t/p/w500/udDclJoHjfjb8Ekgsd4FDteOkCU.jpg', 2019),
(34, 'Black Panther', 'Black Panther', 'TChalla returns home to Wakanda to take his rightful place as king.', 134, 'English', 'USA', 'PG-13', 4.30, 92.30, 'https://image.tmdb.org/t/p/w500/uxzzxijgPIY7slzFvMotPv8wjKA.jpg', 2018),
(35, 'Doctor Strange', 'Doctor Strange', 'A brilliant neurosurgeon discovers the world of the mystic arts.', 115, 'English', 'USA', 'PG-13', 4.10, 88.10, 'https://tse2.mm.bing.net/th/id/OIP.YrBFYZEsHDbuKcDF-U6r6wHaLH?rs=1&pid=ImgDetMain&o=7&rm=3', 2016),
(36, 'Iron Man', 'Iron Man', 'After being held captive, Tony Stark builds a powered suit of armor.', 126, 'English', 'USA', 'PG-13', 4.30, 90.00, 'https://tse3.mm.bing.net/th/id/OIP._qC_BfO_ydtG3rV-gZGC_gHaLH?rs=1&pid=ImgDetMain&o=7&rm=3', 2008),
(37, 'Captain America The Winter Soldier', 'Captain America The Winter Soldier', 'Steve Rogers teams up with Black Widow to uncover a conspiracy.', 136, 'English', 'USA', 'PG-13', 4.40, 87.20, 'https://tse2.mm.bing.net/th/id/OIP.lAK54b4P1jYQ0kPAvsA_fAHaLH?rs=1&pid=ImgDetMain&o=7&rm=3', 2014),
(38, 'Spider-Man Into the Spider-Verse', 'Spider-Man Into the Spider-Verse', 'Teen Miles Morales becomes Spider-Man and meets alternate Spider-People.', 117, 'English', 'USA', 'PG', 4.70, 91.50, 'https://image.tmdb.org/t/p/original/73vmdVnXfgGzLsmXJqzB3vmOnaA.jpg', 2018),
(39, 'Dune', 'Dune', 'Paul Atreides leads nomadic tribes in a battle to control the desert planet Arrakis.', 155, 'English', 'USA', 'PG-13', 4.30, 93.20, 'https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg', 2021),
(40, 'Blade Runner 2049', 'Blade Runner 2049', 'A young blade runner discovers a secret that could plunge society into chaos.', 164, 'English', 'USA', 'R', 4.40, 84.40, 'https://th.bing.com/th/id/R.c203a8b403a072511b0c445717c71d49?rik=Ba01%2b5CT19EHbQ&pid=ImgRaw&r=0', 2017),
(41, 'Mad Max Fury Road', 'Mad Max Fury Road', 'In a post-apocalyptic wasteland, Max helps a rebel warrior flee a tyrant.', 120, 'English', 'Australia', 'R', 4.50, 90.80, 'https://th.bing.com/th/id/R.3c4f7da830a6a6c9dc14e311da28e854?rik=uU%2b4fIiYTzo1iw&pid=ImgRaw&r=0', 2015),
(42, 'Alien', 'Alien', 'The crew of a commercial spacecraft encounters a deadly lifeform.', 117, 'English', 'USA', 'R', 4.50, 85.30, 'https://image.tmdb.org/t/p/w500/vfrQk5IPloGg1v9Rzbh2Eg3VGyM.jpg', 1979),
(43, 'Aliens', 'Aliens', 'Ellen Ripley returns to battle the alien threat with a team of marines.', 137, 'English', 'USA', 'R', 4.50, 84.90, 'https://image.tmdb.org/t/p/w500/r1x5JGpyqZU8PYhbs4UcrO1Xb6x.jpg', 1986),
(44, 'Shrek', 'Shrek', 'An ogre sets out to rescue a princess with a talkative donkey.', 90, 'English', 'USA', 'PG', 4.20, 83.00, 'https://image.tmdb.org/t/p/original/wD5kcfBM21Dcn1hpGon7qa0vwS5.jpg', 2001),
(45, 'Finding Nemo', 'Finding Nemo', 'After his son is captured, a timid clownfish sets out on a journey to bring him home.', 100, 'English', 'USA', 'G', 4.40, 84.80, 'https://m.media-amazon.com/images/S/pv-target-images/30a5a5f314204c9097adce2ad26b35566f40d8a760c2e879480c0420348fc7b5.jpg', 2003),
(46, 'WALL-E', 'WALL-E', 'A small waste-collecting robot embarks on a space journey that changes humanity.', 98, 'English', 'USA', 'G', 4.60, 86.20, 'https://image.tmdb.org/t/p/w500/hbhFnRzzg6ZDmm8YAmxBnQpQIPh.jpg', 2008),
(47, 'Jurassic Park', 'Jurassic Park', 'A pragmatic paleontologist visits a theme park where dinosaurs are cloned.', 127, 'English', 'USA', 'PG-13', 4.50, 88.70, 'https://filmartgallery.com/cdn/shop/products/Jurassic-Park-Vintage-Movie-Poster-Original.jpg?v=1738906074', 1993),
(48, 'The Truman Show', 'The Truman Show', 'An insurance salesman discovers his whole life is a reality television show.', 103, 'English', 'USA', 'PG', 4.40, 82.10, 'https://image.tmdb.org/t/p/original/67KjyFo3PFoYCqyhnagRINg9ALK.jpg', 1998),
(49, 'Arrival', 'Arrival', 'A linguist works with the military to communicate with alien lifeforms.', 116, 'English', 'USA', 'PG-13', 4.30, 83.40, 'https://www.themoviedb.org/t/p/original/ngJ3f5ohpq1dMFtEZj2tRJx0Llx.jpg', 2016),
(50, 'Her', 'Her', 'A lonely writer develops an unlikely relationship with an operating system.', 126, 'English', 'USA', 'R', 4.20, 79.60, 'https://www.themoviedb.org/t/p/original/jpWcLPddK2gZEl09HBY17zeZtdC.jpg', 2013),
(51, 'The Grand Budapest Hotel', 'The Grand Budapest Hotel', 'A concierge teams up with a lobby boy after a priceless painting is stolen.', 99, 'English', 'USA', 'R', 4.20, 78.90, 'https://m.media-amazon.com/images/M/MV5BMzM5NjUxOTEyMl5BMl5BanBnXkFtZTgwNjEyMDM0MDE@._V1_SX300.jpg', 2014),
(52, 'No Country for Old Men', 'No Country for Old Men', 'Violence and fate collide after a hunter discovers a drug deal gone wrong.', 122, 'English', 'USA', 'R', 4.40, 82.70, 'https://m.media-amazon.com/images/M/MV5BMjA5Njk3MjM4OV5BMl5BanBnXkFtZTcwMTc5MTE1MQ@@._V1_SX300.jpg', 2007);

SELECT setval('movies_movie_id_seq', (SELECT MAX(movie_id) FROM movies));

-- Insert Movie Genres
INSERT INTO movie_genres (movie_id, genre_id) VALUES
(3, 9), (3, 10), (4, 1), (4, 4), (4, 5), (4, 10), (5, 2), (5, 5), (5, 9),
(6, 5), (6, 10), (7, 3), (7, 6), (7, 12), (8, 1), (8, 9), (9, 5), (9, 8), (9, 15),
(10, 5), (10, 15), (11, 4), (11, 5), (12, 4), (12, 5), (12, 11), (13, 5), (13, 8),
(14, 5), (15, 1), (15, 2), (15, 9), (16, 3), (16, 11), (16, 12), (17, 10), (17, 13),
(18, 2), (18, 6), (19, 2), (19, 6), (20, 2), (20, 6), (21, 5), (21, 8), (21, 11),
(22, 5), (23, 10), (23, 13), (24, 4), (24, 10), (25, 5), (26, 3), (26, 12),
(27, 2), (27, 3), (27, 12), (28, 3), (28, 12), (29, 3), (29, 5), (29, 12),
(30, 1), (30, 5), (31, 5), (31, 7), (31, 10), (32, 7), (32, 10), (33, 4), (33, 5), (33, 10),
(34, 1), (34, 2), (34, 9), (35, 1), (35, 2), (35, 6), (36, 1), (36, 2), (36, 9),
(37, 1), (37, 2), (37, 9), (38, 1), (38, 2), (38, 3), (39, 2), (39, 5), (39, 9),
(40, 5), (40, 9), (40, 10), (41, 1), (41, 2), (41, 9), (42, 9), (42, 13),
(43, 1), (43, 9), (43, 13), (44, 3), (44, 11), (44, 12), (45, 2), (45, 3), (45, 12),
(46, 3), (46, 9), (46, 12), (47, 1), (47, 2), (47, 9), (48, 5), (48, 11),
(49, 5), (49, 9), (50, 5), (50, 8), (50, 9), (51, 5), (51, 11), (52, 4), (52, 5), (52, 10);

-- Insert Users (cleaned - only unique test users)
INSERT INTO users (user_id, username, email, passwords_hash, created_at) VALUES
(41, 'TestUser', 'you@gmail.com', '872e4e50ce9990d8b041330c47c9ddd11bec6b503ae9386a99da8584e9bb12c4', '2026-03-20 14:30:22'),
(42, 'testuser99', 'test99@test.com', '0e3246dc869aa660163b186fbf002393d2405f322660341d2c666fd0c8362143', '2026-03-20 15:54:48'),
(43, 'TestUser2', 'testuser2@gmail.com', '6d58a6f9ec97185d3cd2420d204eed114b559a3beac6a29f1bb9a15b5f991085', '2026-03-20 15:55:28'),
(44, 'TestUser3', 'testuser3@gmail.com', '6d58a6f9ec97185d3cd2420d204eed114b559a3beac6a29f1bb9a15b5f991085', '2026-03-20 16:01:15'),
(45, 'TestUser5', 'TestUser5@gmail.com', '6d58a6f9ec97185d3cd2420d204eed114b559a3beac6a29f1bb9a15b5f991085', '2026-03-20 17:19:44');

SELECT setval('users_user_id_seq', (SELECT MAX(user_id) FROM users));

-- Insert User Preferences
INSERT INTO user_preferences (preference_id, user_id, preferred_genre_id, preferred_language, preferred_country, min_runtime, max_runtime, preferred_age_rating, preference_weight, created_at) VALUES
(41, 41, 1, 'English', 'USA', 90, 120, 'PG-13', 1.00, '2026-03-20 14:31:04'),
(42, 41, 9, 'English', 'USA', 90, 120, 'PG-13', 0.80, '2026-03-20 14:31:04'),
(43, 41, 10, 'English', 'USA', 90, 120, 'PG-13', 0.60, '2026-03-20 14:31:04'),
(44, 43, 15, 'English', 'USA', NULL, NULL, NULL, 1.00, '2026-03-20 16:00:09'),
(45, 43, 7, 'English', 'USA', NULL, NULL, NULL, 0.80, '2026-03-20 16:00:09'),
(46, 43, 11, 'English', 'USA', NULL, NULL, NULL, 0.60, '2026-03-20 16:00:09'),
(47, 44, 8, NULL, NULL, NULL, NULL, 'PG', 1.00, '2026-03-20 16:01:48'),
(48, 44, 5, NULL, NULL, NULL, NULL, 'PG', 0.80, '2026-03-20 16:01:48'),
(49, 44, 6, NULL, NULL, NULL, NULL, 'PG', 0.60, '2026-03-20 16:01:48'),
(58, 45, 2, 'English', 'USA', NULL, NULL, 'PG', 1.00, '2026-03-20 17:44:27'),
(59, 45, 3, 'English', 'USA', NULL, NULL, 'PG', 0.80, '2026-03-20 17:44:27'),
(60, 45, 11, 'English', 'USA', NULL, NULL, 'PG', 0.60, '2026-03-20 17:44:27');

SELECT setval('user_preferences_preference_id_seq', (SELECT MAX(preference_id) FROM user_preferences));

-- Insert Ratings (sample - user 45's ratings)
INSERT INTO ratings (rating_id, user_id, movie_id, score, rated_at) VALUES
(1117, 45, 27, 4, CURRENT_TIMESTAMP),
(1118, 45, 7, 5, CURRENT_TIMESTAMP),
(1119, 45, 29, 4, CURRENT_TIMESTAMP),
(1120, 45, 44, 5, CURRENT_TIMESTAMP),
(1121, 45, 20, 5, CURRENT_TIMESTAMP),
(1122, 45, 35, 5, CURRENT_TIMESTAMP);

SELECT setval('ratings_rating_id_seq', (SELECT MAX(rating_id) FROM ratings));

-- Insert Watch History (sample - user 45's history)
INSERT INTO watch_history (watchhistory_id, user_id, movie_id, watched_date) VALUES
(121, 45, 28, '2026-03-20 19:19:40'),
(122, 45, 27, CURRENT_TIMESTAMP),
(123, 45, 7, CURRENT_TIMESTAMP),
(124, 45, 44, CURRENT_TIMESTAMP),
(125, 45, 20, CURRENT_TIMESTAMP),
(126, 45, 35, CURRENT_TIMESTAMP);

SELECT setval('watch_history_watchhistory_id_seq', (SELECT MAX(watchhistory_id) FROM watch_history));

-- Insert Movie Streaming
INSERT INTO movie_streaming (moviestreaming_id, movie_id, streaming_service_id, streaming_url) VALUES
(4, 4, 1, 'https://www.netflix.com'),
(5, 4, 4, 'https://www.primevideo.com'),
(6, 5, 1, 'https://www.netflix.com'),
(7, 5, 4, 'https://www.primevideo.com'),
(9, 7, 3, 'https://www.disneyplus.com'),
(10, 8, 1, 'https://www.netflix.com'),
(11, 8, 4, 'https://www.primevideo.com'),
(12, 9, 5, 'https://tv.apple.com'),
(13, 10, 1, 'https://www.netflix.com'),
(14, 11, 4, 'https://www.primevideo.com'),
(15, 12, 1, 'https://www.netflix.com'),
(16, 12, 4, 'https://www.primevideo.com'),
(17, 13, 5, 'https://tv.apple.com'),
(18, 14, 1, 'https://www.netflix.com'),
(19, 15, 5, 'https://tv.apple.com'),
(20, 16, 3, 'https://www.disneyplus.com'),
(21, 17, 6, 'https://www.max.com'),
(22, 18, 5, 'https://tv.apple.com'),
(23, 19, 5, 'https://tv.apple.com'),
(24, 20, 5, 'https://tv.apple.com'),
(25, 21, 1, 'https://www.netflix.com'),
(26, 22, 1, 'https://www.netflix.com'),
(27, 23, 6, 'https://www.max.com'),
(28, 24, 1, 'https://www.netflix.com'),
(29, 25, 1, 'https://www.netflix.com'),
(30, 26, 3, 'https://www.disneyplus.com'),
(31, 27, 3, 'https://www.disneyplus.com'),
(32, 28, 3, 'https://www.disneyplus.com'),
(33, 29, 3, 'https://www.disneyplus.com'),
(34, 30, 4, 'https://www.primevideo.com'),
(36, 32, 1, 'https://www.netflix.com'),
(37, 33, 1, 'https://www.netflix.com'),
(38, 34, 5, 'https://tv.apple.com'),
(39, 35, 5, 'https://tv.apple.com'),
(40, 36, 5, 'https://tv.apple.com'),
(41, 37, 5, 'https://tv.apple.com'),
(42, 38, 5, 'https://tv.apple.com'),
(43, 39, 5, 'https://tv.apple.com'),
(44, 40, 1, 'https://www.netflix.com'),
(45, 41, 1, 'https://www.netflix.com'),
(46, 42, 6, 'https://www.max.com'),
(47, 43, 6, 'https://www.max.com'),
(48, 44, 5, 'https://tv.apple.com'),
(50, 46, 3, 'https://www.disneyplus.com'),
(51, 47, 5, 'https://tv.apple.com'),
(52, 48, 1, 'https://www.netflix.com'),
(53, 49, 5, 'https://tv.apple.com'),
(54, 50, 5, 'https://tv.apple.com'),
(55, 51, 1, 'https://www.netflix.com'),
(97, 3, 6, 'https://www.max.com'),
(98, 45, 3, 'https://www.disneyplus.com'),
(99, 45, 2, 'https://www.hulu.com'),
(100, 52, 7, 'https://www.paramountplus.com'),
(101, 6, 2, 'https://www.hulu.com'),
(102, 7, 12, 'https://www.crunchyroll.com'),
(103, 31, 1, 'https://www.netflix.com');

SELECT setval('movie_streaming_moviestreaming_id_seq', (SELECT MAX(moviestreaming_id) FROM movie_streaming));