# Таблица маршрутов. Связывает URL адреса с функциями из views.py. Грубо говоря "какой адрес → какая функция".
from django.urls import path
from . import views

app_name = "locations"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("terms/", views.terms, name="terms"),
    path("submit/", views.submit_location, name="submit_location"),
    path("submit/success/", views.submit_success, name="submit_success"),
    path("contributors/", views.contributors, name="contributors"),
    path("<slug:country_slug>/", views.country_detail, name="country_detail"),
    # Второй сегмент — либо штат (для стран с Country.has_states=True, например США),
    # либо сразу город (для всех остальных стран). Решает country_child_detail.
    path("<slug:country_slug>/<slug:second_slug>/", views.country_child_detail, name="country_child_detail"),
    # Третий сегмент существует только для "штатных" стран: /country/state/city/
    path("<slug:country_slug>/<slug:state_slug>/<slug:city_slug>/", views.city_detail_in_state, name="city_detail_in_state"),
]
