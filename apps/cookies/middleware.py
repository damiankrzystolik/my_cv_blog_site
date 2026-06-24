from . import conf
from .models import CookieConsent

# Ścieżki, dla których sprawdzanie zgody nie ma sensu i tylko obciąża bazę.
_SKIP_PREFIXES = ("/static/", "/media/", "/admin/")


class CookieConsentMiddleware:
    """Middleware odczytujący zgodę na ciasteczka.

    UWAGA (PLAN.md C3): ten middleware NIE kasuje cookies w odpowiedzi.
    Wcześniejsza wersja próbowała `response.delete_cookie()` dla cookies bez
    zgody, ale to nie działa dla cookies third-party (np. Google Analytics),
    które ustawia JavaScript w przeglądarce - serwer nie ma do nich dostępu
    i nie zna ich Domain/Path. Jedyny skuteczny mechanizm to NIE RENDEROWAĆ
    skryptu, który ustawia cookie, dopóki nie ma zgody - patrz templatetags
    `cookie_tags.py` (script_for_group).

    UWAGA (PLAN.md C4): middleware tylko CZYTA, nigdy nie zapisuje do bazy
    w ścieżce GET. Oznaczanie wygasłych zgód i czyszczenie odbywa się w
    komendzie `cleanup_consents` (cron), nie przy każdym żądaniu.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        self._attach_consent(request)
        return self.get_response(request)

    def _attach_consent(self, request):
        if request.path.startswith(_SKIP_PREFIXES):
            request.cookie_consent = None
            request.has_cookie_consent = False
            return

        consent_id = request.COOKIES.get(conf.CONSENT_COOKIE_NAME)
        consent = None

        if consent_id:
            consent = (
                CookieConsent.objects.filter(consent_id=consent_id, is_valid=True)
                .prefetch_related("accepted_groups")
                .first()
            )
            if consent and consent.is_expired():
                # Tylko w pamięci request - bez zapisu do DB na GET (C4).
                # Realne oznaczenie is_valid=False robi cleanup_consents.
                consent = None

        request.cookie_consent = consent
        request.has_cookie_consent = consent is not None

        accepted = set(consent.accepted_groups.values_list("name", flat=True)) if consent else set()
        request.cookie_consent_groups = accepted
        request.has_analytics_consent = "analytics" in accepted
        request.has_marketing_consent = "marketing" in accepted
