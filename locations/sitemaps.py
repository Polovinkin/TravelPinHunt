# Карта сайта для поисковых систем (Google, Bing и т.д.), доступна на /sitemap.xml
# Использует встроенный Django sitemaps framework — обновляется автоматически по мере
# добавления новых стран/штатов/городов в базу, ничего вручную поддерживать не нужно.
from django.contrib.sitemaps import Sitemap
from django.db.models import Q
from django.urls import reverse
from .models import Country, State, City


class StaticViewSitemap(Sitemap):
    """Статические страницы сайта: главная, about, contributors."""

    priority = 0.5
    changefreq = "monthly"

    def items(self):
        return ["locations:home", "locations:about", "locations:contributors"]

    def location(self, item):
        return reverse(item)


class CountrySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        # Не отправляем поисковикам пустые страницы стран: в sitemap должны быть
        # страны, где есть хотя бы одна локация или заметка о городе.
        return Country.objects.filter(
            Q(cities__locations__isnull=False) | Q(cities__note__gt=""),
        ).distinct()

    def location(self, obj):
        return f"/{obj.slug}/"


class StateSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return State.objects.select_related("country").all()

    def location(self, obj):
        return obj.url


class CitySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return City.objects.select_related("country", "state").all()

    def location(self, obj):
        return obj.url
