import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class MovieRecommender:
    def __init__(self):
        self.vectorizer = None
        self.similarity_matrix = None
        self.movies_data = None
        self.feature_matrix = None
        self.movies_with_features = None

    def load_data_from_backend(self, movies_data, genres_data, movie_genres_data, franchises_data=None):
        self.movies_data = pd.DataFrame(movies_data)
        genres_df = pd.DataFrame(genres_data)
        movie_genres_df = pd.DataFrame(movie_genres_data)
        franchises_df = pd.DataFrame(franchises_data) if franchises_data else pd.DataFrame()

        if self.movies_data.empty or genres_df.empty or movie_genres_df.empty:
            return False

        self.movies_data["Movie_id"] = pd.to_numeric(self.movies_data["Movie_id"], errors="coerce")
        genres_df["Genre_id"] = pd.to_numeric(genres_df["Genre_id"], errors="coerce")
        movie_genres_df["Movie_id"] = pd.to_numeric(movie_genres_df["Movie_id"], errors="coerce")
        movie_genres_df["Genre_id"] = pd.to_numeric(movie_genres_df["Genre_id"], errors="coerce")

        movie_genre_names = movie_genres_df.merge(genres_df, on="Genre_id", how="inner")

        movie_genre_names = (
            movie_genre_names
            .groupby("Movie_id")["Genre_Name"]
            .apply(lambda x: " ".join(sorted(set(str(genre).strip() for genre in x if pd.notna(genre)))))
            .reset_index()
        )

        movies_with_features = self.movies_data.merge(movie_genre_names, on="Movie_id", how="left")

        # Merge franchise data
        if not franchises_df.empty:
            franchises_df["Movie_id"] = pd.to_numeric(franchises_df["Movie_id"], errors="coerce")
            movies_with_features = movies_with_features.merge(
                franchises_df[["Movie_id", "Media_Franchise", "Sequel_Franchise"]], 
                on="Movie_id", 
                how="left"
            )
        else:
            movies_with_features["Media_Franchise"] = None
            movies_with_features["Sequel_Franchise"] = None

        text_columns = ["Title", "Original_Title", "Overview", "Language", "Country", "Age_Rating", "Genre_Name", "Media_Franchise", "Sequel_Franchise"]
        for col in text_columns:
            if col not in movies_with_features.columns:
                movies_with_features[col] = ""
            movies_with_features[col] = movies_with_features[col].fillna("").astype(str).str.strip()

        numeric_columns = ["Runtime", "Release_Year", "Average_Rating", "Popularity_Score"]
        for col in numeric_columns:
            if col not in movies_with_features.columns:
                movies_with_features[col] = None
            movies_with_features[col] = pd.to_numeric(movies_with_features[col], errors="coerce")

        movies_with_features["runtime_bucket"] = pd.cut(
            movies_with_features["Runtime"],
            bins=[0, 80, 100, 120, 150, 999],
            labels=["very_short", "short", "medium", "long", "epic"],
            include_lowest=True
        ).astype("object").fillna("unknown")

        movies_with_features["year_bucket"] = pd.cut(
            movies_with_features["Release_Year"],
            bins=[1880, 1990, 2000, 2010, 2018, 2023, 2030],
            labels=["classic", "90s", "2000s", "2010s", "late_2010s", "recent"],
            include_lowest=True
        ).astype("object").fillna("unknown")

        movies_with_features["rating_bucket"] = pd.cut(
            movies_with_features["Average_Rating"],
            bins=[0, 2.5, 3.5, 4.2, 5],
            labels=["low", "mid", "high", "elite"],
            include_lowest=True
        ).astype("object").fillna("unknown")

        movies_with_features["popularity_bucket"] = pd.cut(
            movies_with_features["Popularity_Score"],
            bins=[0, 10, 40, 80, 999999],
            labels=["niche", "known", "popular", "blockbuster"],
            include_lowest=True
        ).astype("object").fillna("unknown")

        movies_with_features["weighted_title"] = movies_with_features["Title"].apply(
            lambda x: f"{x} {x} {x}" if x else ""
        )

        movies_with_features["weighted_original_title"] = movies_with_features["Original_Title"].apply(
            lambda x: x if x else ""
        )

        movies_with_features["weighted_genres"] = movies_with_features["Genre_Name"].apply(
            lambda x: " ".join(
                f"{genre.strip()} " * 12
                for genre in str(x).split()
                if genre.strip()
            )
        )

        movies_with_features["weighted_overview"] = movies_with_features["Overview"].fillna("").apply(lambda x: x if x else "")

        movies_with_features["weighted_age_rating"] = movies_with_features["Age_Rating"].apply(
            lambda x: f"{x} " * 8 if x and x.strip() else ""
        )

        movies_with_features["weighted_runtime"] = movies_with_features["runtime_bucket"].astype(str).apply(
            lambda x: f"{x} " * 6 if x and x != "unknown" else ""
        )

        # Franchise weighting - HIGHEST priority for media franchise (25x), then sequel franchise (20x)
        movies_with_features["weighted_media_franchise"] = movies_with_features["Media_Franchise"].apply(
            lambda x: f"{x.replace(' ', '_')} " * 25 if x and str(x).strip() and str(x).lower() != 'none' else ""
        )
        movies_with_features["weighted_sequel_franchise"] = movies_with_features["Sequel_Franchise"].apply(
            lambda x: f"{x.replace(' ', '_')} " * 20 if x and str(x).strip() and str(x).lower() != 'none' else ""
        )

        movies_with_features["light_metadata"] = (
            movies_with_features["Language"] + " " +
            movies_with_features["Language"]  
        ).fillna("").astype(str).str.strip()

        movies_with_features["combined_features"] = (
            movies_with_features["weighted_media_franchise"] + " " +
            movies_with_features["weighted_sequel_franchise"] + " " +
            movies_with_features["weighted_title"] + " " +
            movies_with_features["weighted_original_title"] + " " +
            movies_with_features["weighted_genres"] + " " +
            movies_with_features["weighted_age_rating"] + " " +
            movies_with_features["weighted_runtime"] + " " +
            movies_with_features["weighted_overview"] + " " +
            movies_with_features["light_metadata"] + " " +
            movies_with_features["year_bucket"].astype(str) + " " +
            movies_with_features["rating_bucket"].astype(str) + " " +
            movies_with_features["popularity_bucket"].astype(str)
        ).str.strip()

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=7000,
            ngram_range=(1, 2),
            min_df=1
        )

        self.feature_matrix = self.vectorizer.fit_transform(movies_with_features["combined_features"])
        self.similarity_matrix = cosine_similarity(self.feature_matrix)
        self.movies_with_features = movies_with_features

        return True

    def get_recommendations_by_id(self, movie_id, top_n=5, min_score=0.25):
        if self.similarity_matrix is None or self.movies_with_features is None:
            return {"error": "Model not trained. Call load_data_from_backend first."}

        movie_idx = self.movies_with_features[self.movies_with_features["Movie_id"] == movie_id].index

        if len(movie_idx) == 0:
            return {"error": "Movie not found"}

        idx = movie_idx[0]
        selected_title = str(self.movies_with_features.iloc[idx]["Title"]).strip().lower()

        similarity_scores = list(enumerate(self.similarity_matrix[idx]))
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)

        recommendations = []
        for i, score in similarity_scores:
            movie_data = self.movies_with_features.iloc[i]
            current_movie_id = movie_data["Movie_id"]
            current_title = str(movie_data["Title"]).strip().lower()

            if current_movie_id == movie_id:
                continue

            if current_title == selected_title:
                continue

            if score < min_score:
                continue

            recommendations.append({
                "Movie_id": int(current_movie_id),
                "Title": str(movie_data["Title"]),
                "Genre_Name": str(movie_data["Genre_Name"]) if pd.notna(movie_data["Genre_Name"]) else "",
                "Language": str(movie_data["Language"]) if pd.notna(movie_data["Language"]) else "",
                "Country": str(movie_data["Country"]) if pd.notna(movie_data["Country"]) else "",
                "Age_Rating": str(movie_data["Age_Rating"]) if pd.notna(movie_data["Age_Rating"]) else "",
                "Poster_Url": str(movie_data["Poster_Url"]) if pd.notna(movie_data["Poster_Url"]) else "",
                "Release_Year": int(movie_data["Release_Year"]) if pd.notna(movie_data["Release_Year"]) else None,
                "Average_Rating": float(movie_data["Average_Rating"]) if pd.notna(movie_data["Average_Rating"]) else None,
                "Similarity_Score": round(float(score), 4)
            })

            if len(recommendations) == top_n:
                break

        return {"recommendations": recommendations}


recommender = MovieRecommender()