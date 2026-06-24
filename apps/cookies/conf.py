"""Ustawienia aplikacji cookies z bezpiecznymi wartościami domyślnymi.

Nadpisywalne w settings.py projektu, np.:
    COOKIE_CONSENT_DURATION_DAYS = 365
    COOKIE_CONSENT_STORE_IP = False
"""

from django.conf import settings

# Nazwa first-party ciasteczka z identyfikatorem zgody (UUID).
# Niezależne od sesji -> przeżywa rotację session_key przy logowaniu (PLAN.md C1).
CONSENT_COOKIE_NAME = getattr(settings, "COOKIE_CONSENT_COOKIE_NAME", "cookie_consent_id")

# Ważność zgody w dniach. Praktyka UODO/CNIL: ~6-13 miesięcy (PLAN.md A4).
CONSENT_DURATION_DAYS = getattr(settings, "COOKIE_CONSENT_DURATION_DAYS", 180)

# Po ilu dniach od wygaśnięcia komenda cleanup_consents trwale usuwa rekordy (PLAN.md A3).
CONSENT_RETENTION_DAYS = getattr(settings, "COOKIE_CONSENT_RETENTION_DAYS", 365)

# Czy zapisywać adres IP przy zgodzie - dane osobowe, minimalizacja (PLAN.md A5).
STORE_IP = getattr(settings, "COOKIE_CONSENT_STORE_IP", True)

# Atrybuty ciasteczka zgody (PLAN.md B4).
CONSENT_COOKIE_SECURE = getattr(settings, "COOKIE_CONSENT_COOKIE_SECURE", not settings.DEBUG)
CONSENT_COOKIE_SAMESITE = getattr(settings, "COOKIE_CONSENT_COOKIE_SAMESITE", "Lax")

# E-mail administratora danych wyświetlany w polityce cookies (PLAN.md A6).
CONTACT_EMAIL = getattr(settings, "COOKIE_CONSENT_CONTACT_EMAIL", "damiankrzystolik@gmail.com")


def consent_cookie_max_age() -> int:
    """Czas życia ciasteczka zgody w sekundach."""
    return CONSENT_DURATION_DAYS * 24 * 60 * 60
