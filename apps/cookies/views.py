import json
import logging

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from . import conf
from .models import CookieConsent, CookieConsentLog, CookieGroup

logger = logging.getLogger("cookies")

# Baner NIE jest osobnym widokiem/URL-em (PLAN.md D4) - jest partialem
# wstrzykiwanym do base.html przez {% cookie_consent_banner %},
# patrz templatetags/cookie_tags.py.


def cookie_preferences(request):
    """Strona zarządzania preferencjami ciasteczek."""
    if request.method == "POST":
        return handle_cookie_consent(request)

    groups = CookieGroup.objects.filter(is_active=True).prefetch_related("cookie_set")
    current_consent = getattr(request, "cookie_consent", None)
    accepted_groups = list(getattr(request, "cookie_consent_groups", set()))

    return render(
        request,
        "cookies/preferences.html",
        {"groups": groups, "current_consent": current_consent, "accepted_groups": accepted_groups},
    )


def cookie_policy(request):
    """Strona z polityką ciasteczek."""
    groups = CookieGroup.objects.filter(is_active=True).prefetch_related("cookie_set")
    return render(request, "cookies/policy.html", {"groups": groups, "contact_email": conf.CONTACT_EMAIL})


@require_http_methods(["POST"])
def handle_cookie_consent(request):
    """Obsługuje zapisy zgody na ciasteczka.

    Brak @csrf_exempt (PLAN.md B1) - żądania JSON wysyłają nagłówek
    X-CSRFToken, a formularz HTML ma {% csrf_token %}, więc standardowa
    ochrona CSRF Django działa bez wyjątków.
    """
    is_json = request.content_type == "application/json"

    try:
        data = json.loads(request.body) if is_json else request.POST
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"success": False, "error": "Nieprawidłowe dane żądania."}, status=400)

    action = data.get("action")
    selected_groups = data.getlist("selected_groups") if hasattr(data, "getlist") else data.get("selected_groups", [])

    consent = _get_or_create_consent(request)
    old_groups = list(consent.accepted_groups.values_list("name", flat=True))
    required_groups = CookieGroup.objects.filter(is_required=True, is_active=True)

    if action == "accept_all":
        consent.accepted_groups.set(CookieGroup.objects.filter(is_active=True))
        log_action = "accept_all"
    elif action == "reject_all":
        consent.accepted_groups.set(required_groups)
        log_action = "reject_all"
    elif action == "save_preferences":
        # Obowiązkowe grupy zawsze dołączone, niezależnie od tego, co przyszło z formularza.
        consent.accepted_groups.set(
            CookieGroup.objects.filter(
                Q(name__in=list(selected_groups)) | Q(is_required=True),
                is_active=True,
            )
        )
        log_action = "partial"
    else:
        return JsonResponse({"success": False, "error": "Nieznana akcja."}, status=400)

    consent.is_valid = True
    consent.updated_at = timezone.now()
    consent.save()

    new_groups = list(consent.accepted_groups.values_list("name", flat=True))
    CookieConsentLog.objects.create(
        consent=consent,
        action=log_action,
        groups_before=old_groups,
        groups_after=new_groups,
    )

    if is_json:
        response = JsonResponse({"success": True})
    else:
        messages.success(request, "Preferencje ciasteczek zostały zapisane.")
        response = redirect("cookies:preferences")

    _set_consent_cookie(response, consent)
    return response


def withdraw_consent(request):
    """Wycofanie zgody na ciasteczka - pozostają tylko grupy obowiązkowe."""
    consent = getattr(request, "cookie_consent", None)
    if not consent:
        messages.info(request, "Nie masz aktywnej zgody na ciasteczka.")
        return redirect("cookies:preferences")

    old_groups = list(consent.accepted_groups.values_list("name", flat=True))
    required_groups = CookieGroup.objects.filter(is_required=True, is_active=True)

    CookieConsentLog.objects.create(
        consent=consent,
        action="withdraw",
        groups_before=old_groups,
        groups_after=list(required_groups.values_list("name", flat=True)),
    )

    consent.accepted_groups.set(required_groups)
    consent.updated_at = timezone.now()
    consent.save()

    messages.success(request, "Zgoda na ciasteczka została wycofana. Pozostały tylko niezbędne ciasteczka.")
    response = redirect("cookies:preferences")
    _set_consent_cookie(response, consent)
    return response


def _get_or_create_consent(request):
    """Znajduje zgodę po consent-cookie albo tworzy nową (PLAN.md C1/C2).

    Identyfikator zgody żyje we własnym ciasteczku, niezależnie od sesji,
    więc przeżywa cycle_key() wywoływane przez Django przy logowaniu.
    """
    consent_id = request.COOKIES.get(conf.CONSENT_COOKIE_NAME)
    consent = None
    if consent_id:
        consent = CookieConsent.objects.filter(consent_id=consent_id).first()

    if consent is None:
        consent = CookieConsent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            ip_address=_get_client_ip(request) if conf.STORE_IP else None,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            expires_at=timezone.now() + timezone.timedelta(days=conf.CONSENT_DURATION_DAYS),
        )
    elif consent.user is None and request.user.is_authenticated:
        consent.user = request.user
        consent.save(update_fields=["user"])

    return consent


def _set_consent_cookie(response, consent):
    response.set_cookie(
        conf.CONSENT_COOKIE_NAME,
        str(consent.consent_id),
        max_age=conf.consent_cookie_max_age(),
        secure=conf.CONSENT_COOKIE_SECURE,
        httponly=True,
        samesite=conf.CONSENT_COOKIE_SAMESITE,
    )


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# Alias zachowany dla kompatybilności z istniejącymi testami/importami.
get_client_ip = _get_client_ip
