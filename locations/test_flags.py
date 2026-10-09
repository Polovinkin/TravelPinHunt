from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings

from .admin import CountryAdminForm, country_flag_data, country_flag_display
from .flags import flag_filename, flag_image_url, safe_flag_image_url
from .models import Country


@override_settings(DEBUG=False)
class CustomFlagTests(SimpleTestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.storage = ManifestStaticFilesStorage(location=self.directory.name, base_url="/static/")
        self.storage_patch = patch("locations.flags.staticfiles_storage", self.storage)
        self.storage_patch.start()
        self.addCleanup(self.storage_patch.stop)

    def add_collected_flag(self):
        self.storage.hashed_files["flags/kosovo.png"] = "flags/kosovo.abc123.png"
        target = Path(self.directory.name) / "flags/kosovo.abc123.png"
        target.parent.mkdir()
        target.write_bytes(b"flag")
        return target

    def test_filename_and_existing_paths_resolve_to_collected_flag(self):
        self.add_collected_flag()
        for value in ("kosovo.png", "flags/kosovo.png", " kosovo.png "):
            with self.subTest(value=value):
                self.assertEqual(flag_filename(value), "kosovo.png")
                self.assertEqual(flag_image_url(value), "/static/flags/kosovo.abc123.png")

    def test_source_file_without_manifest_entry_is_rejected_on_production(self):
        target = Path(self.directory.name) / "flags/kosovo.png"
        target.parent.mkdir()
        target.write_bytes(b"flag")
        with self.assertRaisesMessage(ValueError, "Missing staticfiles manifest entry"):
            flag_image_url("kosovo.png")

    def test_deleted_collected_file_is_rejected(self):
        self.add_collected_flag().unlink()
        with self.assertRaisesMessage(ValueError, "Flag image not found"):
            flag_image_url("kosovo.png")

    @override_settings(DEBUG=True)
    def test_local_validation_uses_static_finders(self):
        with patch("locations.flags.finders.find", return_value="/source/static/flags/kosovo.png") as find:
            self.assertEqual(flag_image_url("kosovo.png"), "/static/flags/kosovo.png")
            find.assert_called_once_with("flags/kosovo.png")
        with patch("locations.flags.finders.find", return_value=None):
            with self.assertRaisesMessage(ValueError, "Flag image not found"):
                flag_image_url("kosovo.png")

    def test_missing_flag_falls_back_in_admin_and_public_template(self):
        country = Country(name="Kosovo", code="XK", custom_flag="kosovo.png")
        with self.assertLogs("locations.flags", level="WARNING"):
            self.assertEqual(safe_flag_image_url(country.custom_flag), "")
            self.assertEqual(country_flag_display(country), country.flag)
            self.assertEqual(country_flag_data(country)["image_url"], "")
            html = render_to_string("locations/_country_flag.html", {"country": country})
        self.assertNotIn("<img", html)
        self.assertIn(country.flag, html)
        country.code = None
        with self.assertLogs("locations.flags", level="WARNING"):
            self.assertEqual(country_flag_display(country), "")

    def test_available_flag_renders_in_admin_and_public_template(self):
        self.add_collected_flag()
        country = Country(name="Kosovo", custom_flag="flags/kosovo.png")
        self.assertIn('/static/flags/kosovo.abc123.png', country_flag_display(country))
        html = render_to_string("locations/_country_flag.html", {"country": country})
        self.assertIn('src="/static/flags/kosovo.abc123.png"', html)

    def test_model_validation_reports_field_error_and_normalizes_filename(self):
        country = Country(name="Kosovo", custom_flag="flags/kosovo.png")
        # Проверка slug изолирована от БД; проверка статики остаётся настоящей.
        with patch.object(Country.objects, "filter") as query:
            query.return_value.exclude.return_value.exists.return_value = False
            with self.assertRaises(ValidationError) as caught:
                country.clean()
            self.assertIn("custom_flag", caught.exception.message_dict)
            self.assertIn("collectstatic", caught.exception.message_dict["custom_flag"][0])
            self.add_collected_flag()
            country.clean()
        self.assertEqual(country.custom_flag, "kosovo.png")

    def test_form_shows_existing_path_as_filename_without_changing_instance(self):
        country = Country(name="Kosovo", custom_flag="flags/kosovo.png")
        form = CountryAdminForm(instance=country)
        self.assertEqual(form.initial["custom_flag"], "kosovo.png")
        self.assertEqual(country.custom_flag, "flags/kosovo.png")

    def test_paths_outside_flags_and_url_fragments_are_rejected(self):
        for value in ("../kosovo.png", "flags/../kosovo.png", "static/flags/kosovo.png", "kosovo.png?x", "kosovo.png#x", "..", "a\\b.png"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                flag_filename(value)
