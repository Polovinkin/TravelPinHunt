# Настройка встроенной админки Django. Регистрирую модели, настраиваю как они выглядят и редактируются в /admin.
from .models import Country, State, City, PinType, Location, LocationSubmission
from django.contrib import admin
from django import forms
from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.utils.html import format_html
from urllib.parse import urlencode


# --- COUNTRIES ---

class HasLocationsFilter(admin.SimpleListFilter):
    """Тоггл в сайдбаре: показывать только страны, у которых есть хотя бы одна locations."""

    title = "has locations"
    parameter_name = "has_locations"

    def lookups(self, request, model_admin):
        return [("yes", "With locations"), ("no", "Without locations")]

    def queryset(self, request, queryset):
        # queryset тут уже annotated в CountryAdmin.get_queryset (location_count_annotated)
        if self.value() == "yes":
            return queryset.filter(location_count_annotated__gt=0)
        if self.value() == "no":
            return queryset.filter(location_count_annotated=0)
        return queryset


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["flag_display", "name", "code", "slug", "city_count", "location_count", "has_states"]
    list_display_links = ["name"]  # кликабельным должно быть название, а не флаг
    list_filter = [HasLocationsFilter, "has_states"]
    search_fields = ["name", "code"]
    readonly_fields = ["slug"]  # slug генерируется автоматически из name, руками не редактируется

    def get_queryset(self, request):
        # annotate вместо obj.cities... в цикле — иначе на 100+ странах будет N+1 запросов.
        # distinct=True на обоих Count, потому что JOIN cities+locations размножает строки
        qs = super().get_queryset(request).annotate(
            city_count_annotated=models.Count("cities", distinct=True),
            location_count_annotated=models.Count("cities__locations", distinct=True),
        )

        # Автокомплит для поля State.country (виджет шлёт app_label/model_name/field_name
        # текущего поля в GET) — показываем только страны с has_states=True, чтобы туда
        # нельзя было по ошибке добавить штат стране без этого флага. На обычный список
        # стран в самой Country admin это не влияет — там этих GET-параметров нет.
        if request.GET.get("model_name") == "state" and request.GET.get("field_name") == "country":
            qs = qs.filter(has_states=True)

        return qs

    @admin.display(description="Flag")
    def flag_display(self, obj):
        # эмодзи флага для визуала в списке стран
        return obj.flag

    @admin.display(description="Cities", ordering="city_count_annotated")
    def city_count(self, obj):
        return obj.city_count_annotated

    @admin.display(description="Locations", ordering="location_count_annotated")
    def location_count(self, obj):
        # сколько всего pin locations в городах этой страны
        return obj.location_count_annotated


# --- STATES ---

class StateAdminForm(forms.ModelForm):
    """Кастомная форма штата: запрещает добавить дубликат штата в ту же страну"""

    class Meta:
        model = State
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            # без этого браузер предлагает автозаполнение из ранее введённых значений
            # других полей "code" на сайте (например ISO-кодов стран) — сбивает с толку
            "code": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get("country")
        name = cleaned_data.get("name")
        slug = slugify(name) if name else ""

        # проверяем уникальность по паре country+slug (не глобально)
        if country and slug:
            exists = State.objects.filter(country=country, slug=slug).exclude(pk=self.instance.pk).exists()
            if exists:
                self.add_error("name", f"Oops, {name} was already added to {country.name}!")

        return cleaned_data


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    form = StateAdminForm
    list_display = ["name", "flag_display", "country", "code", "slug", "city_count"]
    search_fields = ["name", "code"]
    list_filter = ["country"]
    readonly_fields = ["slug"]  # slug генерируется автоматически из name
    autocomplete_fields = ["country"]  # поиск страны по названию вместо огромного дропдауна
    fields = [
        "country",
        ("name", "code"),  # кортеж = два поля в одной строке
        "slug",
    ]

    class Media:
        # рисует эмодзи флага справа от поля Country и обновляет его при выборе страны
        js = ["admin_country_flag.js"]

    def get_queryset(self, request):
        # select_related избегает N+1, annotate — чтобы не считать города в цикле
        return super().get_queryset(request).select_related("country").annotate(
            city_count_annotated=models.Count("cities", distinct=True),
        )

    @admin.display(description="Flag")
    def flag_display(self, obj):
        return obj.country.flag

    @admin.display(description="Cities", ordering="city_count_annotated")
    def city_count(self, obj):
        return obj.city_count_annotated

    def _country_flags_context(self):
        # переиспользуем ту же логику и тот же JS, что и в CityAdmin — см. там подробный комментарий
        import json
        return {"country_flags_json": json.dumps({str(c.pk): c.flag for c in Country.objects.all()})}

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), **self._country_flags_context()}
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), **self._country_flags_context()}
        return super().change_view(request, object_id, form_url, extra_context)


# --- CITIES ---

class CityAdminForm(forms.ModelForm):
    """Кастомная форма города: требует штат для "штатных" стран (has_states=True),
    запрещает штат для остальных, и проверяет дубликаты в правильном скоупе —
    по штату (если есть) или по стране (если штатов нет)."""

    class Meta:
        model = City
        fields = "__all__"
        labels = {
            "youtube_walk_url": "YouTube walk URL",
            "note": "City note",
        }
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "youtube_walk_url": forms.URLInput(attrs={"autocomplete": "off"}),
            "note": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get("country")
        state = cleaned_data.get("state")
        name = cleaned_data.get("name")
        slug = slugify(name) if name else ""

        if country and country.has_states:
            if not state:
                self.add_error("state", f"{country.name} requires a state — please select one.")
            elif state.country_id != country.id:
                self.add_error("state", "Selected state does not belong to the selected country.")
        elif state:
            # страна без штатов, но штат почему-то передан (например через devtools) — игнорируем
            cleaned_data["state"] = None
            state = None

        # проверяем уникальность slug в правильном скоупе: по штату, если он есть, иначе по стране
        if slug:
            if state:
                exists = City.objects.filter(state=state, slug=slug).exclude(pk=self.instance.pk).exists()
                scope_name = state.name
            elif country:
                exists = City.objects.filter(country=country, slug=slug, state__isnull=True).exclude(pk=self.instance.pk).exists()
                scope_name = country.name
            else:
                exists = False
                scope_name = ""
            if exists:
                self.add_error("name", f"Oops, {name} was already added to {scope_name}!")

        return cleaned_data

@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    form = CityAdminForm
    list_display = ["name", "flag_display", "country", "state", "slug", "is_capital", "location_count"]
    search_fields = ["name", "country__name"]
    list_filter = ["country"]
    readonly_fields = ["slug"]  # slug генерируется автоматически из name
    autocomplete_fields = ["country"]  # поиск страны по названию вместо огромного дропдауна
    fields = [
        "country",
        "state",  # поле видно только для стран с has_states=True — см. admin_city_state.js
        ("name", "is_capital"),  # кортеж = два поля в одной строке
        "youtube_walk_url",
        "note",
        "location_type",
        "slug",
    ]

    class Media:
        # первый скрипт рисует флаг рядом с Country, второй — показывает/скрывает и
        # заполняет поле State в зависимости от выбранной страны
        js = ["admin_country_flag.js", "admin_city_state.js"]

    def get_queryset(self, request):
        # select_related избегает N+1: достаём города сразу со страной и штатом одним JOIN запросом
        return super().get_queryset(request).select_related("country", "state")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "state":
            # сортируем по стране, чтобы штаты одной страны шли подряд — так проще
            # ориентироваться в исходном (до JS-фильтрации) списке опций
            kwargs["queryset"] = State.objects.select_related("country").order_by("country__name", "name")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Locations")
    def location_count(self, obj):
        # показывает сколько pin locations добавлено в этом городе
        return obj.locations.count()

    @admin.display(description="Flag")
    def flag_display(self, obj):
        # эмодзи флага страны рядом с её названием, как в списке стран
        return obj.country.flag

    def _country_flags_context(self):
        # {country_id: flag_emoji} для JS, который рисует флаг рядом с полем Country.
        # Считаем на каждый рендер формы (запрос дешёвый — всего ~170 стран), а не кэшируем,
        # чтобы не расходиться с реальными данными в БД.
        import json
        return {"country_flags_json": json.dumps({str(c.pk): c.flag for c in Country.objects.all()})}

    def _state_context(self):
        # {country_id: True} для стран с has_states=True, и {country_id: [{id, name}, ...]}
        # штатов этой страны — для JS, который показывает/скрывает и заполняет поле State.
        import json
        has_states_map = {str(pk): True for pk in Country.objects.filter(has_states=True).values_list("pk", flat=True)}
        states_by_country = {}
        for state in State.objects.select_related("country").order_by("name"):
            states_by_country.setdefault(str(state.country_id), []).append({"id": state.pk, "name": state.name})
        return {
            "country_has_states_json": json.dumps(has_states_map),
            "states_by_country_json": json.dumps(states_by_country),
        }

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), **self._country_flags_context(), **self._state_context()}
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), **self._country_flags_context(), **self._state_context()}
        return super().change_view(request, object_id, form_url, extra_context)


# --- LOCATIONS ---

class LocationAdminForm(forms.ModelForm):
    """Кастомная форма локации: поле coordinates парсит lat/lng из формата Google Maps"""

    coordinates = forms.CharField(
        required=False,
        help_text="Paste coordinates, e.g. 47.18706, 9.32250",
        widget=forms.TextInput(attrs={"autocomplete": "off"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # при редактировании существующей локации показываем текущие координаты в поле
        if self.instance and self.instance.lat and self.instance.lng:
            self.fields["coordinates"].initial = f"{self.instance.lat}, {self.instance.lng}"

    class Meta:
        model = Location
        fields = "__all__"
        exclude = ["lat", "lng"]  # скрываем сырые поля, координаты вводятся через поле coordinates выше
        labels = {
            "google_maps_url": "Google Maps URL",
            "yandex_maps_url": "Yandex Maps URL",
            "lat": "Latitude (auto)",
            "lng": "Longitude (auto)",
        }
        widgets = {
            # ширина в 2 раза больше стандартной (vTextField ~20em) — имена локаций часто длинные
            "name": forms.TextInput(attrs={"autocomplete": "off", "style": "width: 50%; max-width: 40em;"}),
            # class="vLargeTextField" — стандартный класс Django admin для текстовых полей,
            # без него виджет теряет обычную ширину (48em)
            "description": forms.Textarea(attrs={"rows": 7, "class": "vLargeTextField"}),
            # одинаковая ширина для обеих ссылок — примерно половина страницы
            "google_maps_url": forms.URLInput(attrs={"autocomplete": "off", "style": "width: 50%; max-width: 45em;"}),
            "yandex_maps_url": forms.URLInput(attrs={"autocomplete": "off", "style": "width: 50%; max-width: 45em;"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        coordinates = cleaned_data.get("coordinates")
        if coordinates:
            try:
                # парсим строку "lat, lng" → два отдельных float
                lat, lng = [c.strip() for c in coordinates.split(",")]
                cleaned_data["lat"] = round(float(lat), 5)  # 5 знаков после запятой достаточно
                cleaned_data["lng"] = round(float(lng), 5)
            except (ValueError, AttributeError):
                self.add_error("coordinates", "Invalid format. Use: 47.18706, 9.32250")
        return cleaned_data

    def save(self, commit=True):
        # записываем распарсенные lat/lng в инстанс вручную (они exclude'd из Meta.fields)
        instance = super().save(commit=False)
        instance.lat = self.cleaned_data.get("lat")
        instance.lng = self.cleaned_data.get("lng")
        if commit:
            instance.save()
        return instance

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    form = LocationAdminForm
    list_display = ["name", "city", "source_column", "created_at"]
    search_fields = ["name", "description", "city__name"]  # city__name — чтобы искать локации по названию города
    list_filter = ["pin_types", "source"]
    readonly_fields = ["lat", "lng", "created_at", "updated_at"]  # координаты редактируются только через поле coordinates
    autocomplete_fields = ["city"]
    fieldsets = [
        (None, {"fields": ["name", "city", "description"]}),
        ("Location", {"fields": ["google_maps_url", ("coordinates", "lat", "lng")]}),
        ("Pin types", {"fields": ["pin_types"]}),
        ("Contributor", {"fields": [("source", "contributor_nickname")]}),
        ("Meta", {"fields": [("created_at", "updated_at")]}),
    ]

    def get_fieldsets(self, request, obj=None):
        # поле yandex_maps_url нужно только для локаций в России, поэтому не показываем
        # его в форме для всех остальных стран, чтобы не захламлять админку
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.city.country.code == "RU":
            fieldsets = [
                (title, {**opts, "fields": (
                    [*opts["fields"], "yandex_maps_url"] if title == "Location" else opts["fields"]
                )})
                for title, opts in fieldsets
            ]
        return fieldsets

    def get_queryset(self, request):
        # select_related избегает N+1: достаём локации сразу с их городами одним JOIN запросом
        return super().get_queryset(request).select_related("city", "city__country")

    @admin.display(description="Source", ordering="source")
    def source_column(self, obj):
        # показывает, кто добавил локацию: сам Дима (Owner) или заявка сообщества (Community),
        # для community дополнительно показываем ник, если он указан в заявке
        if obj.source == Location.SOURCE_COMMUNITY:
            if obj.contributor_nickname:
                return f"👤 {obj.contributor_nickname}"
            return "👥 Community"  # значок нескольких людей — контрибьютор без указанного ника
        return "Owner"

    def _city_flags_context(self):
        # {city_id: flag_emoji} для JS, который рисует флаг рядом с полем City
        # (флаг берётся из страны, к которой привязан город)
        import json
        cities = City.objects.select_related("country")
        return {"city_flags_json": json.dumps({str(c.pk): c.country.flag for c in cities})}

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), **self._city_flags_context()}
        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {**(extra_context or {}), **self._city_flags_context()}
        return super().change_view(request, object_id, form_url, extra_context)

    # эмодзи как на форме /submit/, только для отображения в этой форме — модель не трогаем
    PIN_TYPE_EMOJI = {"city": "🏙️", "place": "🏛️", "country": "🌍"}

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # простые чекбоксы вместо filter_horizontal — типов пинов всего 3, выбор
        # такой же, как на форме /submit/
        if db_field.name == "pin_types":
            kwargs["widget"] = forms.CheckboxSelectMultiple()
        formfield = super().formfield_for_manytomany(db_field, request, **kwargs)
        if db_field.name == "pin_types":
            formfield.label_from_instance = lambda obj: (
                f"{self.PIN_TYPE_EMOJI.get(obj.name, '')} {obj}"
            )
        return formfield

    class Media:
        css = {"all": ["admin_custom.css"]}  # чекбоксы pin_types в одну строку
        js = ["admin_country_flag.js"]  # флаг страны рядом с полем City


# --- PIN TYPES ---

@admin.register(PinType)
class PinTypeAdmin(admin.ModelAdmin):
    list_display = ["name"]


# --- SUBMISSIONS (заявки от пользователей) ---

class LocationSubmissionAdminForm(forms.ModelForm):
    """Кастомная форма заявки: эмодзи в лейблах чекбоксов совпадают с формой на /submit/"""

    class Meta:
        model = LocationSubmission
        fields = "__all__"
        labels = {
            "google_maps_url": "Google Maps URL",
            "photo_url": "Photo URL",
            "has_city_pins": "🏙️ City pins",
            "has_country_pins": "🌍 Country pins",
            "has_place_pins": "🏛️ Place pins",
        }
        help_texts = {
            "google_maps_url": "",  # и так понятно, подсказка из модели тут лишняя
        }


@admin.register(LocationSubmission)
class LocationSubmissionAdmin(admin.ModelAdmin):
    form = LocationSubmissionAdminForm
    list_display = ["location_name", "city_name", "country_name", "contributor_column", "status", "created_at"]
    list_filter = ["status", "has_city_pins", "has_country_pins", "has_place_pins"]
    search_fields = ["location_name", "city_name", "country_name"]
    readonly_fields = ["created_at", "pin_types_label", "create_location_link"]
    formfield_overrides = {
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 4})},
    }
    list_editable = ["status"]  # статус можно менять прямо в списке без захода в каждую запись
    # явный порядок полей: description показывается раньше google_maps_url,
    # а photo_url — после чекбоксов с типами пинов
    # (в модели порядок другой, но так удобнее читать заявку при модерации)
    fieldsets = [
        (None, {"fields": [
            ("location_name", "status"),  # кортеж = два поля в одной строке
            ("country_name", "city_name"),
            "description", "google_maps_url",
            # pin_types_label — пустое readonly-поле, нужно только чтобы получить
            # подпись "Pin types:" точно в том же стиле, что и у остальных полей
            ("pin_types_label", "has_city_pins", "has_country_pins", "has_place_pins"),
            "photo_url",
            ("submitter_email", "contributor_nickname"),
            "create_location_link",
        ]}),
        ("Meta", {"fields": ["created_at", "notes"]}),
    ]

    @admin.display(description="Pin types")
    def pin_types_label(self, obj):
        return ""

    @admin.display(description="Contributor", ordering="contributor_nickname")
    def contributor_column(self, obj):
        # тот же contributor_nickname, но с укороченным заголовком колонки в списке
        return obj.contributor_nickname

    @admin.display(description="Quick create")
    def create_location_link(self, obj):
        # кнопка, открывающая форму "Add location" с уже заполненными name/description/
        # google_maps_url/pin_types из этой заявки — остаётся выбрать только city (и создать
        # его при необходимости, указав country)
        if obj.pk is None:
            return "Save the submission first"

        pin_type_names = []
        if obj.has_city_pins:
            pin_type_names.append(PinType.CITY)
        if obj.has_country_pins:
            pin_type_names.append(PinType.COUNTRY)
        if obj.has_place_pins:
            pin_type_names.append(PinType.PLACE)
        pin_type_ids = PinType.objects.filter(name__in=pin_type_names).values_list("pk", flat=True)

        params = {
            "name": obj.location_name,
            "description": obj.description,
            "google_maps_url": obj.google_maps_url,
            "source": Location.SOURCE_COMMUNITY,
            "contributor_nickname": obj.contributor_nickname,
        }
        if pin_type_ids:
            # Django admin ждёт m2m initial data одной строкой через запятую, не повторяющимися ключами
            params["pin_types"] = ",".join(str(pk) for pk in pin_type_ids)

        url = reverse("admin:locations_location_add") + "?" + urlencode(params)
        # обычный "+", а не эмодзи ➕ — у цветного эмодзи свой фиксированный цвет глифа,
        # CSS color на него не действует, поэтому на тёмно-зелёной кнопке он плохо виден
        return format_html(
            '<a class="button" href="{}" target="_blank">+ Create Location from this submission</a>',
            url,
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name == "description":
            # это поле шире остальных текстовых полей — так удобнее читать длинные описания
            formfield.widget.attrs["style"] = "width: 150%; max-width: 150%;"
        return formfield

    class Media:
        css = {"all": ["admin_custom.css"]}  # жирный лейбл "Pin types:"


# на главной странице админки подписываем "Location submissions" количеством заявок в
# статусе Pending (чтобы новые заявки было видно сразу, без захода внутрь) и выставляем
# ручной порядок моделей в разделе Locations вместо дефолтного алфавитного.
# get_app_list вызывается на каждый рендер главной, поэтому и счётчик, и порядок всегда актуальны.
_original_get_app_list = admin.site.get_app_list

# порядок моделей в разделе Locations на главной странице (по object_name модели)
_LOCATIONS_MODEL_ORDER = ["LocationSubmission", "Location", "City", "Country", "State", "PinType"]

# эмодзи-префикс для названий моделей в разделе Locations на главной странице (чисто визуально)
_LOCATIONS_MODEL_EMOJI = {
    "LocationSubmission": "📥",
    "Location": "📍",
    "City": "🏙️",
    "Country": "🌍",
    "State": "🗺️",
    "PinType": "📌",
}


def _get_app_list_with_pending_badge(self, request, app_label=None):
    app_list = _original_get_app_list(request, app_label)
    pending_count = LocationSubmission.objects.filter(status=LocationSubmission.PENDING).count()
    for app in app_list:
        if app["app_label"] == "locations":
            app["models"].sort(
                key=lambda m: (
                    _LOCATIONS_MODEL_ORDER.index(m["object_name"])
                    if m["object_name"] in _LOCATIONS_MODEL_ORDER
                    else len(_LOCATIONS_MODEL_ORDER)
                )
            )
            for model in app["models"]:
                emoji = _LOCATIONS_MODEL_EMOJI.get(model["object_name"])
                if emoji:
                    model["name"] = f"{emoji} {model['name']}"
                if pending_count and model["object_name"] == "LocationSubmission":
                    model["name"] = format_html(
                        "{} <span class=\"pending-badge\">{}</span>", model["name"], pending_count
                    )
    return app_list


admin.site.get_app_list = _get_app_list_with_pending_badge.__get__(admin.site, admin.AdminSite)
