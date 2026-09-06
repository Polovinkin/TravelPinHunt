# Логика страниц. Каждая функция получает запрос, достаёт данные из БД и возвращает HTML. Мозг приложения.
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from .models import Country, State, City, Location, LocationSubmission
from .forms import LocationSubmissionForm
from django.db.models import Count, Q
from django.views.decorators.cache import never_cache
import requests
from django.conf import settings


# Частые варианты написания, которые люди вводят вместо полного названия страны
# (например "USA" вместо "United States"). Используется и в поиске на главной, и в contributors().
COUNTRY_ALIASES = {
    "usa": "united states",
    "us": "united states",
    "u.s.a.": "united states",
    "u.s.": "united states",
    "united states of america": "united states",
}


def home(request):
    query = request.GET.get("q", "").strip()
    results = []
    countries = []
    latest_location = None
    location_count = None
    country_count = None

    if query:
        # ищем по вхождению строки в название города или страны (case-insensitive)
        # плюс алиасы вроде "usa" -> "united states", чтобы такие запросы тоже находились
        alias_target = COUNTRY_ALIASES.get(query.lower().strip())

        country_filter = Q(name__icontains=query)
        city_filter = Q(name__icontains=query)
        if alias_target:
            country_filter |= Q(name__icontains=alias_target)
            city_filter |= Q(country__name__icontains=alias_target)

        # Исключаем только города/страны без локаций и без заметок — им некуда вести со страницы поиска.
        cities = City.objects.filter(
            city_filter,
        ).filter(
            Q(locations__isnull=False) | Q(note__gt=""),
        ).select_related(
            "country", "state"
        ).distinct()

        # Точное уникальное совпадение сразу открывает страницу города.
        # Частичные совпадения и одинаковые названия в разных местах остаются в выдаче.
        exact_cities = list(cities.filter(name__iexact=query)[:2])
        if len(exact_cities) == 1:
            return redirect(exact_cities[0].url)

        countries_found = Country.objects.filter(
            country_filter,
        ).filter(
            Q(cities__locations__isnull=False) | Q(cities__note__gt=""),
        ).distinct()

        results = {
            "cities": cities,
            "countries": countries_found,
            "query": query,
        }
    else:
        # Эти данные отображаются только на главной странице без результатов поиска.
        countries = list(
            Country.objects.filter(Q(cities__locations__isnull=False) | Q(cities__note__gt=""))
            .distinct()
            .order_by("name")
        )
        # Список уже загружен, поэтому len() не выполняет дополнительный COUNT-запрос.
        country_count = len(countries)
        location_count = Location.objects.count()
        # Последняя добавленная локация для плитки "Last added" на главной.
        latest_location = Location.objects.select_related(
            "city", "city__country", "city__state"
        ).order_by("-created_at").first()

    return render(request, "locations/home.html", {
        "countries": countries,
        "results": results,
        "query": query,
        "latest_location": latest_location,
        "location_count": location_count,
        "country_count": country_count,
    })


def about(request):
    return render(request, "locations/about.html")


def terms(request):
    return render(request, "locations/terms.html")


def country_detail(request, country_slug):
    # 404 если страна не найдена
    country = get_object_or_404(Country, slug=country_slug)

    if country.opens_city_directly:
        city = get_object_or_404(
            City.objects.select_related("country", "state"),
            country=country,
            name=country.name,
            state__isnull=True,
        )
        return city_detail(request, country, city.slug)

    if country.has_states:
        # "Штатные" страны (например США): показываем штаты, в которых есть
        # хотя бы один город с локацией или заметкой — как на главной для стран.
        states = list(State.objects.filter(
            country=country,
        ).filter(
            Q(cities__locations__isnull=False) | Q(cities__note__gt=""),
        ).annotate(
            location_count=Count("cities__locations", distinct=True),
        ).distinct().order_by("name"))
        # Количество уже посчитано для каждого штата в основном запросе.
        total_locations = sum(state.location_count for state in states)
        states_with_locations_count = sum(state.location_count > 0 for state in states)
        states_with_note_count = len(states) - states_with_locations_count
        return render(request, "locations/country_detail.html", {
            "country": country,
            "states": states,
            "states_with_locations_count": states_with_locations_count,
            "states_with_note_count": states_with_note_count,
            "page_country_slug": country.slug,
            "total_locations": total_locations,
        })

    cities = list(
        City.objects.filter(country=country)
        .filter(Q(locations__isnull=False) | Q(note__gt=""))
        .distinct()
        .select_related("country", "state")
        .annotate(location_count=Count("locations", distinct=True))
        .order_by("name")
    )
    total_locations = sum(c.location_count for c in cities)
    cities_with_locations_count = sum(city.location_count > 0 for city in cities)
    cities_with_note_count = len(cities) - cities_with_locations_count
    return render(request, "locations/country_detail.html", {
        "country": country,
        "cities": cities,
        "cities_with_locations_count": cities_with_locations_count,
        "cities_with_note_count": cities_with_note_count,
        "page_country_slug": country.slug,
        "total_locations": total_locations,
    })


def country_child_detail(request, country_slug, second_slug):
    # Второй сегмент URL — это либо штат (для стран с has_states=True), либо сразу город.
    country = get_object_or_404(Country, slug=country_slug)

    if country.has_states:
        return state_detail(request, country, second_slug)

    return city_detail(request, country, second_slug)


def state_detail(request, country, state_slug):
    state = get_object_or_404(State, slug=state_slug, country=country, country__has_states=True)
    cities = list(
        City.objects.filter(state=state, country=country)
        .filter(Q(locations__isnull=False) | Q(note__gt=""))
        .distinct()
        .select_related("country", "state")
        .annotate(location_count=Count("locations", distinct=True))
        .order_by("name")
    )
    # Общее число локаций в штате — вычисляется из суммарного количества по городам
    total_locations = sum(c.location_count for c in cities)
    cities_with_locations_count = sum(city.location_count > 0 for city in cities)
    cities_with_note_count = len(cities) - cities_with_locations_count
    return render(request, "locations/state_detail.html", {
        "country": country,
        "state": state,
        "cities": cities,
        "cities_with_locations_count": cities_with_locations_count,
        "cities_with_note_count": cities_with_note_count,
        "page_country_slug": country.slug,
        "total_locations": total_locations,
    })


def city_detail(request, country, city_slug, state=None):
    # slug города уникален в рамках штата (если есть) или страны (если штатов нет)
    lookup = {"slug": city_slug, "country": country}
    if country.has_states:
        lookup["state"] = state
    cities = City.objects.select_related("country", "state").filter(**lookup)
    # При старых дубликатах URL города возвращаем 404 вместо серверной ошибки.
    try:
        city = get_object_or_404(cities)
    except City.MultipleObjectsReturned:
        raise Http404("Ambiguous city URL") from None
    if city.is_country_landing_page and request.path != city.url:
        return redirect(city.url, permanent=True)
    # Show Pincredible locations first, then sort by the number of distinct pin types
    # (3 -> 2 -> 1), and finally by name within each group.
    locations = Location.objects.filter(city=city).prefetch_related("pin_types").annotate(
        pin_type_count=Count("pin_types", distinct=True)
    ).order_by("-is_pincredible", "-pin_type_count", "name")
    return render(request, "locations/city_detail.html", {
        "city": city,
        "locations": locations,
        "page_country_slug": country.slug,
    })


def city_detail_in_state(request, country_slug, state_slug, city_slug):
    # Полный трёхсегментный URL /country/state/city/ — только для "штатных" стран
    country = get_object_or_404(Country, slug=country_slug, has_states=True)
    state = get_object_or_404(State, slug=state_slug, country=country)
    return city_detail(request, country, city_slug, state=state)

@never_cache  # форма не должна кешироваться — иначе браузер может показать старые данные после сабмита
def submit_location(request):
    if request.method == "POST":
        form = LocationSubmissionForm(request.POST)

        # Проверяем Turnstile токен через Cloudflare API
        token = request.POST.get("cf-turnstile-response", "")
        turnstile_ok = False
        if token:
            try:
                cf_response = requests.post(
                    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                    data={
                        "secret": settings.TURNSTILE_SECRET_KEY,
                        "response": token,
                        "remoteip": request.META.get("REMOTE_ADDR"),
                    },
                    timeout=5,
                )
                turnstile_ok = cf_response.json().get("success", False)
            except requests.RequestException:
                turnstile_ok = False

        if form.is_valid() and turnstile_ok:
            form.save()
            return redirect("locations:submit_success")

        if not turnstile_ok:
            form.add_error(None, "Captcha check failed. Please try again.")

    else:
        form = LocationSubmissionForm()

    return render(request, "locations/submit_location.html", {
        "form": form,
        "TURNSTILE_SITE_KEY": settings.TURNSTILE_SITE_KEY,
    })


@never_cache  # аналогично — страница успеха не должна открываться повторно из кеша
def submit_success(request):
    return render(request, "locations/submit_success.html")


def contributors(request):
    # Никнеймы контрибьюторов, у кого хотя бы одна заявка одобрена (Approved).
    # country_name в заявке — это свободный текст, а не FK на Country, поэтому
    # сопоставляем его с моделью Country по названию (без учёта регистра), чтобы взять флаг.
    approved = (
        LocationSubmission.objects
        .filter(status=LocationSubmission.APPROVED)
        .exclude(contributor_nickname="")
        .values("contributor_nickname", "country_name")
    )

    # Берём только данные, необходимые для отображения флагов, не создавая полноценные объекты Country.
    country_flags = {
        c["name"].lower(): {
            "emoji": "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in (c["code"] or "").upper()),
            "custom_flag": c["custom_flag"],
        }
        for c in Country.objects.values("name", "code", "custom_flag")
    }

    def resolve_flag(country_name):
        # Берём часть до запятой на случай "USA, California" — сам штат/город игнорируем
        key = country_name.strip().split(",")[0].strip().lower()
        key = COUNTRY_ALIASES.get(key, key)
        return country_flags.get(key)

    contributors_by_nickname = {}
    for row in approved:
        nickname = row["contributor_nickname"]
        entry = contributors_by_nickname.setdefault(nickname, {"submission_count": 0, "flags": []})
        entry["submission_count"] += 1
        flag = resolve_flag(row["country_name"])
        if flag and (flag["emoji"] or flag["custom_flag"]) and flag not in entry["flags"]:
            entry["flags"].append(flag)

    contributors_list = [
        {"contributor_nickname": nickname, **info}
        for nickname, info in contributors_by_nickname.items()
    ]
    # сортируем по количеству одобренных заявок, при равенстве — по алфавиту
    contributors_list.sort(key=lambda c: (-c["submission_count"], c["contributor_nickname"].lower()))

    return render(request, "locations/contributors.html", {
        "contributors_list": contributors_list,
    })
