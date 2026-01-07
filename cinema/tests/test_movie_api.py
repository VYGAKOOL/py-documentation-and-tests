from django.test import TestCase
from django.urls import reverse

from cinema.models import MovieSession, CinemaHall

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())

import os
import tempfile
from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from cinema.models import Movie, Genre, Actor
from cinema.serializers import (
    MovieListSerializer,
    MovieDetailSerializer,
)


MOVIE_LIST_URL = reverse("cinema:movie-list")


def movie_detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


def movie_image_upload_url(movie_id):
    return reverse("cinema:movie-upload-image", args=[movie_id])


def sample_genre(name="Action"):
    return Genre.objects.create(name=name)


def sample_actor(first_name="Tom", last_name="Hardy"):
    return Actor.objects.create(
        first_name=first_name,
        last_name=last_name,
    )


def sample_movie(**params):
    defaults = {
        "title": "Test movie",
        "description": "Test description",
        "duration": 120,
    }
    defaults.update(params)
    movie = Movie.objects.create(
        title=defaults["title"],
        description=defaults["description"],
        duration=defaults["duration"],
    )
    return movie


class MovieApiTests(TestCase):
    """Tests for MovieViewSet"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.com",
            password="password123",
        )
        self.admin = get_user_model().objects.create_superuser(
            email="admin@test.com",
            password="admin123",
        )

    # ---------- LIST ----------

    def test_movie_list_authenticated(self):
        """Authenticated user can list movies"""
        self.client.force_authenticate(self.user)

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        res = self.client.get(MOVIE_LIST_URL)

        movies = Movie.objects.all()
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    # ---------- RETRIEVE ----------

    def test_movie_retrieve_authenticated(self):
        """Authenticated user can retrieve movie"""
        self.client.force_authenticate(self.user)

        movie = sample_movie()

        url = movie_detail_url(movie.id)
        res = self.client.get(url)

        serializer = MovieDetailSerializer(movie)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    # ---------- CREATE ----------

    def test_movie_create_admin_success(self):
        """Admin can create movie"""
        self.client.force_authenticate(self.admin)

        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "Admin movie",
            "description": "Admin desc",
            "duration": 90,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Movie.objects.filter(title="Admin movie").exists())

    def test_movie_create_user_forbidden(self):
        """Non-admin user cannot create movie"""
        self.client.force_authenticate(self.user)

        genre = sample_genre()
        actor = sample_actor()

        payload = {
            "title": "Movie",
            "description": "Desc",
            "duration": 100,
            "genres": [genre.id],
            "actors": [actor.id],
        }

        res = self.client.post(MOVIE_LIST_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    # ---------- FILTERS ----------

    def test_filter_movies_by_title(self):
        """Filter movies by title"""
        self.client.force_authenticate(self.user)

        sample_movie(title="Batman")
        sample_movie(title="Superman")

        res = self.client.get(MOVIE_LIST_URL, {"title": "bat"})

        movies = Movie.objects.filter(title__icontains="bat")
        serializer = MovieListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_genres(self):
        """Filter movies by genres"""
        self.client.force_authenticate(self.user)

        genre1 = sample_genre("Action")
        genre2 = sample_genre("Drama")

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.genres.add(genre1)
        movie2.genres.add(genre2)

        res = self.client.get(
            MOVIE_LIST_URL,
            {"genres": str(genre1.id)},
        )

        serializer = MovieListSerializer([movie1], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_movies_by_actors(self):
        """Filter movies by actors"""
        self.client.force_authenticate(self.user)

        actor1 = sample_actor("Tom", "Hardy")
        actor2 = sample_actor("Leonardo", "DiCaprio")

        movie1 = sample_movie(title="Movie 1")
        movie2 = sample_movie(title="Movie 2")

        movie1.actors.add(actor1)
        movie2.actors.add(actor2)

        res = self.client.get(
            MOVIE_LIST_URL,
            {"actors": str(actor1.id)},
        )

        serializer = MovieListSerializer([movie1], many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    # ---------- UPLOAD IMAGE ----------

    def test_upload_image_admin_success(self):
        """Admin can upload image to movie"""
        self.client.force_authenticate(self.admin)

        movie = sample_movie()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image:
            img = Image.new("RGB", (10, 10))
            img.save(image, format="JPEG")
            image.seek(0)

            res = self.client.post(
                movie_image_upload_url(movie.id),
                {"image": image},
                format="multipart",
            )

        movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(movie.image)
        self.assertTrue(os.path.exists(movie.image.path))

    def test_upload_image_user_forbidden(self):
        """Non-admin cannot upload image"""
        self.client.force_authenticate(self.user)

        movie = sample_movie()

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image:
            img = Image.new("RGB", (10, 10))
            img.save(image, format="JPEG")
            image.seek(0)

            res = self.client.post(
                movie_image_upload_url(movie.id),
                {"image": image},
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
