from django.urls import path

from . import views

app_name = "cookies"

# Brak "banner/" - baner nie jest osobną stroną, jest partialem wstrzykiwanym
# do base.html przez {% cookie_consent_banner %} (PLAN.md D4/D5).
urlpatterns = [
    path("preferences/", views.cookie_preferences, name="preferences"),
    path("policy/", views.cookie_policy, name="policy"),
    path("consent/", views.handle_cookie_consent, name="consent"),
    path("withdraw/", views.withdraw_consent, name="withdraw"),
]
