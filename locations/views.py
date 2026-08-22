# Логика страниц. Каждая функция получает запрос, достаёт данные из БД и возвращает HTML. Мозг приложения.
from django.shortcuts import render, get_object_or_404, redirect
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
    # только страны у которых есть хотя бы одна локация (не показываем пустые)
    # Evaluating countries QuerySet into a list here avoids a redundant SQL COUNT(*) query
    # when computing country_count, saving one DB query per home page render.
    countries = list(
        Country.objects.filter(cities__locations__isnull=False)
        .distinct()
        .order_by("name")
    )

    query = request.GET.get("q", "").strip()
    results = []

    # последняя добавленная локация для плитки "Last added" на главной
    latest_location = Location.objects.select_related(
        "city", "city__country", "city__state"
    ).order_by("-created_at").first()

    location_count = Location.objects.count()
    country_count = len(countries)

    if query:
        # ищем по вхождению строки в название города или страны (case-insensitive)
        # плюс алиасы вроде "usa" -> "united states", чтобы такие запросы тоже находились
        alias_target = COUNTRY_ALIASES.get(query.lower().strip())

        country_filter = Q(name__icontains=query)
        city_filter = Q(name__icontains=query)
        if alias_target:
            country_filter |= Q(name__icontains=alias_target)
            city_filter |= Q(country__name__icontains=alias_target)

        # исключаем города/страны без единой локации — им некуда вести со страницы поиска
        cities = City.objects.filter(city_filter, locations__isnull=False).select_related(
            "country", "state"
        ).distinct()

        countries_found = Country.objects.filter(
            country_filter, cities__locations__isnull=False
        ).distinct()

        results = {
            "cities": cities,
            "countries": countries_found,
            "query": query,
        }

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


def country_detail(request, country_slug):
    # 404 если страна не найдена
    country = get_object_or_404(Country, slug=country_slug)

    # Общее число локаций в стране — используется в meta description для более конкретного сниппета
    total_locations = Location.objects.filter(city__country=country).count()

    if country.has_states:
        # "штатные" страны (например США): сначала показываем штаты, в которых есть
        # хотя бы один город с добавленными локациями — как на главной для стран
        states = State.objects.filter(country=country).annotate(
            location_count=Count("cities__locations", distinct=True),
        ).filter(location_count__gt=0).order_by("name")
        return render(request, "locations/country_detail.html", {
            "country": country,
            "states": states,
            "page_country_slug": country.slug,
            "total_locations": total_locations,
        })

    cities = City.objects.filter(country=country).annotate(location_count=Count("locations")).order_by("name")
    return render(request, "locations/country_detail.html", {
        "country": country,
        "cities": cities,
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
    state = get_object_or_404(State, slug=state_slug, country=country)
    cities = City.objects.filter(state=state).select_related("country", "state").annotate(
        location_count=Count("locations")
    ).order_by("name")
    # Общее число локаций в штате — используется в meta description для более конкретного сниппета
    total_locations = Location.objects.filter(city__state=state).count()
    return render(request, "locations/state_detail.html", {
        "country": country,
        "state": state,
        "cities": cities,
        "page_country_slug": country.slug,
        "total_locations": total_locations,
    })


def city_detail(request, country, city_slug, state=None):
    # slug города уникален в рамках штата (если есть) или страны (если штатов нет)
    lookup = {"slug": city_slug, "country": country}
    if state is not None:
        lookup["state"] = state
    city = get_object_or_404(City, **lookup)
    # сначала локации с бóльшим числом разных типов пинов (3 -> 2 -> 1), внутри группы — по имени
    locations = Location.objects.filter(city=city).prefetch_related("pin_types").annotate(
        pin_type_count=Count("pin_types", distinct=True)
    ).order_by("-pin_type_count", "name")
    return render(request, "locations/city_detail.html", {
        "city": city,
        "locations": locations,
        "page_country_slug": country.slug,
    })


def city_detail_in_state(request, country_slug, state_slug, city_slug):
    # Полный трёхсегментный URL /country/state/city/ — только для "штатных" стран
    country = get_object_or_404(Country, slug=country_slug)
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

    # fetch only name and code dicts instead of constructing full Country instances.
    # Dynamically compute emoji flags from uppercase ISO code, saving memory and model instantiation overhead.
    country_flags = {
        c["name"].lower(): "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in c["code"].upper())
        for c in Country.objects.values("name", "code")
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
        if flag and flag not in entry["flags"]:
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