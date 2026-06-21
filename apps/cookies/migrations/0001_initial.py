import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Migracja inicjalna dla NOWEGO projektu.

    Jeśli wgrywasz tę aplikację do projektu, w którym już istniała stara
    wersja (z polem session_id), nie nadpisuj tym plikiem istniejącej
    migracji - wygeneruj migrację różnicową (`makemigrations`), która
    przeprowadzi dane (np. usunie stare CookieConsent, bo nie da się
    sensownie zmapować session_id -> consent_id).
    """

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CookieGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.CharField(
                        choices=[
                            ("necessary", "Obowiązkowe"),
                            ("analytics", "Analityczne"),
                            ("marketing", "Marketingowe"),
                        ],
                        max_length=100,
                        unique=True,
                        verbose_name="Nazwa",
                    ),
                ),
                ("display_name", models.CharField(max_length=200, verbose_name="Nazwa wyświetlana")),
                ("description", models.TextField(verbose_name="Opis")),
                ("is_required", models.BooleanField(default=False, verbose_name="Obowiązkowe")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktywne")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Utworzono")),
            ],
            options={
                "verbose_name": "Grupa ciasteczek",
                "verbose_name_plural": "Grupy ciasteczek",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="CookieConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("consent_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="ID zgody")),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True, verbose_name="Adres IP")),
                ("user_agent", models.TextField(blank=True, verbose_name="User Agent")),
                ("consent_given_at", models.DateTimeField(auto_now_add=True, verbose_name="Zgoda udzielona")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Aktualizacja")),
                ("expires_at", models.DateTimeField(verbose_name="Wygasa")),
                ("is_valid", models.BooleanField(default=True, verbose_name="Ważna")),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Użytkownik",
                    ),
                ),
                (
                    "accepted_groups",
                    models.ManyToManyField(blank=True, to="cookies.cookiegroup", verbose_name="Zaakceptowane grupy"),
                ),
            ],
            options={
                "verbose_name": "Zgoda na ciasteczka",
                "verbose_name_plural": "Zgody na ciasteczka",
                "ordering": ["-consent_given_at"],
            },
        ),
        migrations.CreateModel(
            name="CookieConsentLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("accept_all", "Zaakceptowano wszystkie"),
                            ("reject_all", "Odrzucono wszystkie"),
                            ("partial", "Częściowa zgoda"),
                            ("withdraw", "Wycofanie zgody"),
                        ],
                        max_length=50,
                        verbose_name="Działanie",
                    ),
                ),
                ("groups_before", models.JSONField(blank=True, default=list, verbose_name="Grupy przed")),
                ("groups_after", models.JSONField(blank=True, default=list, verbose_name="Grupy po")),
                ("timestamp", models.DateTimeField(auto_now_add=True, verbose_name="Znacznik czasu")),
                (
                    "consent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="cookies.cookieconsent", verbose_name="Zgoda"
                    ),
                ),
            ],
            options={
                "verbose_name": "Log zgody na ciasteczka",
                "verbose_name_plural": "Logi zgód na ciasteczka",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="Cookie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, verbose_name="Nazwa ciasteczka")),
                ("domain", models.CharField(blank=True, default="", max_length=255, verbose_name="Domena")),
                ("path", models.CharField(default="/", max_length=255, verbose_name="Ścieżka")),
                ("purpose", models.TextField(verbose_name="Cel użycia")),
                ("expiry", models.CharField(default="Session", max_length=100, verbose_name="Wygaśnięcie")),
                ("provider", models.CharField(blank=True, max_length=100, verbose_name="Dostawca")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktywne")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Utworzono")),
                (
                    "group",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="cookies.cookiegroup", verbose_name="Grupa"
                    ),
                ),
            ],
            options={
                "verbose_name": "Ciasteczko",
                "verbose_name_plural": "Ciasteczka",
                "unique_together": {("name", "domain")},
            },
        ),
        migrations.AddIndex(
            model_name="cookieconsent",
            index=models.Index(fields=["is_valid"], name="cookies_coo_is_vali_idx"),
        ),
        migrations.AddIndex(
            model_name="cookieconsent",
            index=models.Index(fields=["expires_at"], name="cookies_coo_expires_idx"),
        ),
    ]
