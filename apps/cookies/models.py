import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from . import conf

User = get_user_model()


class CookieGroup(models.Model):
    """Grupa ciasteczek (kategoria)."""

    COOKIE_GROUPS = [
        ("necessary", "Obowiązkowe"),
        ("analytics", "Analityczne"),
        ("marketing", "Marketingowe"),
    ]

    name = models.CharField("Nazwa", max_length=100, choices=COOKIE_GROUPS, unique=True)
    display_name = models.CharField("Nazwa wyświetlana", max_length=200)
    description = models.TextField("Opis")
    # is_required jest jedynym źródłem prawdy o tym, czy grupa wymaga zgody.
    # Nie porównujemy nigdzie name == "necessary" (PLAN.md C8) - dzięki temu
    # projekt może dodać własną grupę "obowiązkową" pod inną nazwą.
    is_required = models.BooleanField("Obowiązkowe", default=False)
    is_active = models.BooleanField("Aktywne", default=True)
    created_at = models.DateTimeField("Utworzono", auto_now_add=True)

    class Meta:
        verbose_name = "Grupa ciasteczek"
        verbose_name_plural = "Grupy ciasteczek"
        ordering = ["name"]

    def __str__(self):
        return self.display_name


class Cookie(models.Model):
    """Definicja pojedynczego ciasteczka (katalog do polityki cookies)."""

    group = models.ForeignKey(CookieGroup, on_delete=models.CASCADE, verbose_name="Grupa")
    name = models.CharField("Nazwa ciasteczka", max_length=255)
    # domain jako "" (nie NULL) - w Postgres NULL != NULL psuje unique_together
    # i pozwala wstawić duplikaty (PLAN.md C9).
    domain = models.CharField("Domena", max_length=255, blank=True, default="")
    path = models.CharField("Ścieżka", max_length=255, default="/")
    purpose = models.TextField("Cel użycia")
    expiry = models.CharField("Wygaśnięcie", max_length=100, default="Session")
    provider = models.CharField("Dostawca", max_length=100, blank=True)
    is_active = models.BooleanField("Aktywne", default=True)
    created_at = models.DateTimeField("Utworzono", auto_now_add=True)

    class Meta:
        verbose_name = "Ciasteczko"
        verbose_name_plural = "Ciasteczka"
        unique_together = ["name", "domain"]

    def __str__(self):
        return f"{self.name} ({self.group.display_name})"


class CookieConsent(models.Model):
    """Zgoda użytkownika na ciasteczka.

    Identyfikowana przez `consent_id` (UUID) trzymany we własnym, first-party
    ciasteczku - NIE przez `session_key`. Klucz sesji rotuje się przy logowaniu
    (django.contrib.auth wywołuje cycle_key), co sprawiałoby, że zgoda "znika"
    i baner wraca tuż po zalogowaniu (PLAN.md C1/C2).
    """

    consent_id = models.UUIDField("ID zgody", default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Użytkownik")
    ip_address = models.GenericIPAddressField("Adres IP", null=True, blank=True)
    user_agent = models.TextField("User Agent", blank=True)
    accepted_groups = models.ManyToManyField(CookieGroup, verbose_name="Zaakceptowane grupy", blank=True)
    consent_given_at = models.DateTimeField("Zgoda udzielona", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualizacja", auto_now=True)
    expires_at = models.DateTimeField("Wygasa")
    is_valid = models.BooleanField("Ważna", default=True)

    class Meta:
        verbose_name = "Zgoda na ciasteczka"
        verbose_name_plural = "Zgody na ciasteczka"
        ordering = ["-consent_given_at"]
        indexes = [
            models.Index(fields=["is_valid"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return str(self.consent_id)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=conf.CONSENT_DURATION_DAYS)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    def has_group_consent(self, group_name):
        if self.is_expired() or not self.is_valid:
            return False
        return self.accepted_groups.filter(name=group_name).exists()


class CookieConsentLog(models.Model):
    """Log działań związanych ze zgodą na ciasteczka (rejestr do wykazania zgodności)."""

    ACTION_CHOICES = [
        ("accept_all", "Zaakceptowano wszystkie"),
        ("reject_all", "Odrzucono wszystkie"),
        ("partial", "Częściowa zgoda"),
        ("withdraw", "Wycofanie zgody"),
    ]

    consent = models.ForeignKey(CookieConsent, on_delete=models.CASCADE, verbose_name="Zgoda")
    action = models.CharField("Działanie", max_length=50, choices=ACTION_CHOICES)
    groups_before = models.JSONField("Grupy przed", blank=True, default=list)
    groups_after = models.JSONField("Grupy po", blank=True, default=list)
    timestamp = models.DateTimeField("Znacznik czasu", auto_now_add=True)

    class Meta:
        verbose_name = "Log zgody na ciasteczka"
        verbose_name_plural = "Logi zgód na ciasteczka"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action} ({self.timestamp})"
