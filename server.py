import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from urllib.parse import parse_qs, urlparse, unquote
import json
import pandas as pd
from datetime import datetime
import uuid
import os
from typing import Callable, Any
from wsgiref.simple_server import make_server

nltk.download('vader_lexicon', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.download('stopwords', quiet=True)

adj_noun_pairs_count = {}
sia = SentimentIntensityAnalyzer()
stop_words = set(stopwords.words('english'))

reviews = pd.read_csv('data/reviews.csv').to_dict('records')

class ReviewAnalyzerServer:
    def __init__(self) -> None:
        # This method is a placeholder for future initialization logic
        pass

    def analyze_sentiment(self, review_body):
        sentiment_scores = sia.polarity_scores(review_body)
        return sentiment_scores

    def __call__(self, environ: dict[str, Any], start_response: Callable[..., Any]) -> bytes:
        """
        The environ parameter is a dictionary containing some useful
        HTTP request information such as: REQUEST_METHOD, CONTENT_LENGTH, QUERY_STRING,
        PATH_INFO, CONTENT_TYPE, etc.
        """
        locations_allowed = [
            "Albuquerque, New Mexico",
            "Carlsbad, California",
            "Chula Vista, California",
            "Colorado Springs, Colorado",
            "Denver, Colorado",
            "El Cajon, California",
            "El Paso, Texas",
            "Escondido, California",
            "Fresno, California",
            "La Mesa, California",
            "Las Vegas, Nevada",
            "Los Angeles, California",
            "Oceanside, California",
            "Phoenix, Arizona",
            "Sacramento, California",
            "Salt Lake City, Utah",
            "Salt Lake City, Utah",
            "San Diego, California",
            "Tucson, Arizona"
        ]

        if environ["REQUEST_METHOD"] == "GET":

            # Write your code here

            # Getting parameters from the url
            url_params = parse_qs(environ.get("QUERY_STRING"))
            location = url_params.get("location", [None])[0]
            start_date = url_params.get("start_date", [None])[0]
            end_date = url_params.get("end_date", [None])[0]

            # Filter the reviews based on the query string parameters
            filtered_reviews = reviews
            if location and location in locations_allowed:
                filtered_reviews = [review for review in filtered_reviews if review["Location"] == location]
            if start_date:          
                filtered_reviews = [review for review in filtered_reviews if datetime.strptime(review["Timestamp"], "%Y-%m-%d  %H:%M:%S") >= datetime.strptime(start_date, "%Y-%m-%d")]       

            if end_date:      
                filtered_reviews = [review for review in filtered_reviews if datetime.strptime(review["Timestamp"], "%Y-%m-%d  %H:%M:%S") <= datetime.strptime(end_date, "%Y-%m-%d")]

            # Adding sentiment scores to reviews
            for review in filtered_reviews:
                review_body = review["ReviewBody"]
                sentiment_scores = self.analyze_sentiment(review_body)
                review["sentiment"] = sentiment_scores
            
            filtered_reviews.sort(key=lambda x: x["sentiment"]["compound"], reverse=True)

            response_body = json.dumps(filtered_reviews, indent=2).encode("utf-8")


            # Set the appropriate response headers
            start_response("200 OK", [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(response_body)))
             ])
            # print(response_body)
            return [response_body]


        if environ["REQUEST_METHOD"] == "POST":
            # Write your code here
            if environ["CONTENT_TYPE"] == "application/x-www-form-urlencoded":
                content_length = int(environ.get("CONTENT_LENGTH", 0))
                post_body = environ["wsgi.input"].read(content_length).replace(b"+", b" ").decode("utf-8")
                post_data = dict(item.split("=") for item in post_body.split("&"))
                review_id = str(uuid.uuid4())

                # Check if the post data contains Location
                if not post_data.get("Location"):
                    response_body = json.dumps({"error": "Location not provided"}, indent=2).encode("utf-8")

                    # Set the appropriate response headers
                    start_response("400 Bad Request", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_body)))
                    ])
                    return [response_body]

                # Check if the location is valid
                post_data["Location"] = unquote(post_data["Location"])
                if post_data.get("Location") not in locations_allowed:
                    response_body = json.dumps({"error": "invalid location"}, indent=2).encode("utf-8")

                    # Set the appropriate response headers
                    start_response("400 Bad Request", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_body)))
                    ])
                    return [response_body]

                # Check if the post data contains ReviewBody
                if not post_data.get("ReviewBody"):
                    response_body = json.dumps({"error": "ReviewBody not provided"}, indent=2).encode("utf-8")

                    # Set the appropriate response headers
                    start_response("400 Bad Request", [
                    ("Content-Type", "application/json"),
                    ("Content-Length", str(len(response_body)))
                    ])
                    return [response_body]
                
                # Writing the review to the reviews.csv file
                post_data["ReviewBody"] = unquote(post_data["ReviewBody"])
                post_data["ReviewId"] = review_id
                post_data["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Add the post data to the reviews.csv file
                with open('data/reviews.csv', 'a') as file:
                    file.write(f'\n{post_data["ReviewId"]},"{post_data["Location"]}",{post_data["Timestamp"]},{post_data["ReviewBody"]}')
                    file.close()
                    
                response_body = json.dumps(post_data, indent=2).encode("utf-8")

                # Set the appropriate response headers
                start_response("201 Created", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
                ])
                return [response_body]
            else:
                response_body = json.dumps({"error": "Invalid post request"}, indent=2).encode("utf-8")

                # Set the appropriate response headers
                start_response("400 Bad Request", [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(response_body)))
                ])
                return [response_body]

if __name__ == "__main__":
    app = ReviewAnalyzerServer()
    port = os.environ.get('PORT', 8000)
    with make_server("", port, app) as httpd:
        print(f"Listening on port {port}...")
        httpd.serve_forever()