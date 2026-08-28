# Структура базы данных. Тут находятся классы которые становятся таблицами в PostgreSQL. Это сердце приложения.
from django.db import models
from django.db.models import Q
from django.utils.text import slugify


class Country(models.Model):
    name = models.CharField(max_length=30, help_text="Country name in English")
    code = models.CharField(max_length=2, unique=True, help_text="ISO country code, for flags")  # ISO код: RU, FR, JP, TH
    slug = models.SlugField(unique=True, blank=True, help_text="Generated automatically from the name")
    has_states = models.BooleanField(
        default=False,
        help_text=(
            "Show a state/region layer for this country (e.g. USA): "
            "Country → State → City instead of Country → City"
        ),
    )

    def save(self, *args, **kwargs):
        # генерируем slug из названия страны один раз при создании
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Countries"

    @property
    def flag(self):
        # конвертируем ISO код в эмодзи флага через Unicode regional indicators
        # 'A' = 0x1F1E6, 'B' = 0x1F1E7, и т.д. — браузер склеивает два символа в один флаг
        return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in self.code.upper())

    @property
    def url(self):
        # для единообразия с State.url и City.url — упрощает сборку ссылок в шаблонах
        return f"/{self.slug}/"


class State(models.Model):
    """Штат/провинция/регион внутри страны. Универсальная модель — не только для США,
    подойдёт для любой страны с делением на штаты/провинции. Используется только когда
    у страны стоит Country.has_states=True."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="states")
    name = models.CharField(max_length=50, help_text="State/region name in English")
    slug = models.SlugField(blank=True, help_text="Generated automatically from the name")
    code = models.CharField(max_length=10, blank=True, help_text="Optional abbreviation, e.g. CA, NY")

    def save(self, *args, **kwargs):
        # генерируем slug из названия штата один раз при создании
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.country.name}"

    class Meta:
        unique_together = ["country", "slug"]  # slug уникален в рамках страны, не глобально
        ordering = ["name"]

    @property
    def url(self):
        return f"/{self.country.slug}/{self.slug}/"


class City(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="cities")
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="cities", null=True, blank=True,
        help_text="Only for countries with Country.has_states=True (e.g. USA). Leave blank otherwise.",
    )
    name = models.CharField(max_length=50, db_index=True, help_text="City name in English")
    slug = models.SlugField(blank=True, help_text="Generated automatically from the name")
    is_capital = models.BooleanField(default=False, help_text="Is this the capital city?")
    location_type = models.CharField(
        max_length=50, blank=True, help_text="Optional special location type, e.g. Island, National Park"
    )
    youtube_walk_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Optional Vagabondity walking tour for this city or place",
    )
    note = models.TextField(
        blank=True,
        help_text="Optional public note shown above this city's locations",
    )

    def save(self, *args, **kwargs):
        # генерируем slug из названия города один раз при создании
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.state_id:
            return f"{self.name}, {self.state.name}, {self.country.name}"
        return f"{self.name}, {self.country.name}"

    class Meta:
        verbose_name_plural = "Cities"
        ordering = ["name"]
        constraints = [
            # страны без штатов: slug уникален в рамках страны — поведение как раньше
            models.UniqueConstraint(
                fields=["country", "slug"], condition=Q(state__isnull=True),
                name="unique_city_slug_per_country_without_state",
            ),
            # страны со штатами: slug уникален в рамках штата, а не всей страны — это
            # позволяет, например, Springfield в Illinois и Springfield в Ohio сосуществовать
            models.UniqueConstraint(
                fields=["state", "slug"], condition=Q(state__isnull=False),
                name="unique_city_slug_per_state",
            ),
        ]

    @property
    def url(self):
        if self.state_id:
            return f"/{self.country.slug}/{self.state.slug}/{self.slug}/"
        return f"/{self.country.slug}/{self.slug}/"


class PinType(models.Model):
    """Тип пина: city (городской), country (страновой), place (достопримечательность)"""

    CITY = "city"
    PLACE = "place"
    COUNTRY = "country"

    PIN_TYPE_CHOICES = [
        (CITY, "City pin"),
        (PLACE, "Place pin"),
        (COUNTRY, "Country pin"),
    ]

    name = models.CharField(max_length=50, choices=PIN_TYPE_CHOICES, unique=True)

    def __str__(self):
        # возвращает человекочитаемое название, например "City pin" вместо "city"
        return self.get_name_display()


class Location(models.Model):
    """Место где продают пины: магазин, сувенирная лавка, музей и т.д."""

    SOURCE_OWNER = "owner"
    SOURCE_COMMUNITY = "community"

    SOURCE_CHOICES = [
        (SOURCE_OWNER, "Site owner"),
        (SOURCE_COMMUNITY, "Community"),
    ]

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    lat = models.DecimalField(max_digits=8, decimal_places=5, null=True, blank=True)   # широта
    lng = models.DecimalField(max_digits=9, decimal_places=5, null=True, blank=True)   # долгота
    google_maps_url = models.URLField(blank=True)
    yandex_maps_url = models.URLField(
        blank=True, help_text="Used instead of Google Maps for locations in Russia, where Google Maps works poorly"
    )
    pin_types = models.ManyToManyField(PinType, blank=True)  # у одного места может быть несколько типов пинов
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default=SOURCE_OWNER,
        help_text="Site owner: no badge shown on the site. Community: shows a contribution badge on the location card.",
    )
    contributor_nickname = models.CharField(
        max_length=50, blank=True,
        help_text="Shown in the community badge on the site, e.g. 'Added by Anna'. Leave blank to show an unnamed 'Community-added' badge.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at (UTC)")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at (UTC)")

    def __str__(self):
        return f"{self.name} — {self.city.name}"


class LocationSubmission(models.Model):
    """Заявка от пользователя на добавление нового места. Проходит модерацию перед попаданием в базу."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

    STATUS_CHOICES = [
        (PENDING, "🟡 Pending"),
        (APPROVED, "✅ Approved"),
        (REJECTED, "❌ Rejected"),
    ]

    # Информация о месте
    country_name = models.CharField(max_length=30, help_text="Country name in English")
    city_name = models.CharField(max_length=100, help_text="City name in English")
    location_name = models.CharField(max_length=100, help_text="Name of the shop or place")
    google_maps_url = models.URLField(max_length=500, help_text="Link to Google Maps")
    description = models.TextField(help_text="Description of the place and what pins are available")
    photo_url = models.URLField(max_length=500, blank=True, help_text="Link to a photo of the pins (optional)")

    # Какие типы пинов продаются (булевы флаги, не FK — заявка не привязана к PinType напрямую)
    has_city_pins = models.BooleanField(default=False)
    has_country_pins = models.BooleanField(default=False)
    has_place_pins = models.BooleanField(default=False)

    # Контакт сабмиттера (опционально)
    submitter_email = models.EmailField(max_length=100, blank=True, help_text="Your email (optional)")
    contributor_nickname = models.CharField(
        max_length=50, blank=True,
        help_text="Nickname to credit you in the Contributors list on the site (optional)",
    )

    # Статус модерации и служебные поля
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at (UTC)")
    notes = models.TextField(blank=True, help_text="Internal notes for review")  # заметки для модератора

    def __str__(self):
        return f"{self.location_name} — {self.city_name}, {self.country_name}"

    class Meta:
        ordering = ["-created_at"]  # новые заявки сверху
