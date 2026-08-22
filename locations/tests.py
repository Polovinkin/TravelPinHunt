from django.test import TestCase, RequestFactory
from django.urls import reverse
from locations.models import Country, State, City, Location, LocationSubmission
from locations.views import home, contributors


class ViewsPerformanceAndCorrectnessTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.country_us = Country.objects.create(name="United States", code="US")
        self.country_jp = Country.objects.create(name="Japan", code="JP")
        self.city_tokyo = City.objects.create(country=self.country_jp, name="Tokyo")
        self.location = Location.objects.create(city=self.city_tokyo, name="Tokyo Souvenir Shop")

        self.submission1 = LocationSubmission.objects.create(
            country_name="USA, California",
            city_name="Los Angeles",
            location_name="Pin Shop",
            google_maps_url="https://maps.google.com",
            description="Nice pins",
            contributor_nickname="Alice",
            status=LocationSubmission.APPROVED,
        )
        self.submission2 = LocationSubmission.objects.create(
            country_name="Japan",
            city_name="Tokyo",
            location_name="Tokyo Pin Shop",
            google_maps_url="https://maps.google.com",
            description="More pins",
            contributor_nickname="Alice",
            status=LocationSubmission.APPROVED,
        )

    def test_home_view(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("countries", response.context)
        self.assertEqual(response.context["country_count"], 1)
        self.assertEqual(response.context["location_count"], 1)
        self.assertEqual(response.context["latest_location"], self.location)

    def test_contributors_view(self):
        response = self.client.get("/contributors/")
        self.assertEqual(response.status_code, 200)
        contributors_list = response.context["contributors_list"]
        self.assertEqual(len(contributors_list), 1)
        alice = contributors_list[0]
        self.assertEqual(alice["contributor_nickname"], "Alice")
        self.assertEqual(alice["submission_count"], 2)
        # Check flags resolved correctly: US flag and JP flag
        self.assertIn(self.country_us.flag, alice["flags"])
        self.assertIn(self.country_jp.flag, alice["flags"])
