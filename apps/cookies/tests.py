import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import conf
from .management.commands.cleanup_consents import Command as CleanupCommand
from .middleware import CookieConsentMiddleware
from .models import Cookie, CookieConsent, CookieConsentLog, CookieGroup
from .views import get_client_ip

User = get_user_model()


class CookieGroupModelTests(TestCase):
    def setUp(self):
        self.necessary_group = CookieGroup.objects.create(
            name="necessary", display_name="Obowiązkowe", description="Niezbędne dla działania strony", is_required=True
        )
        self.analytics_group = CookieGroup.objects.create(
            name="analytics", display_name="Analityczne", description="Służą do analizy ruchu"
        )

    def test_string_representation(self):
        self.assertEqual(str(self.necessary_group), "Obowiązkowe")

    def test_cookie_group_creation(self):
        self.assertEqual(self.necessary_group.name, "necessary")
        self.assertTrue(self.necessary_group.is_required)
        self.assertTrue(self.analytics_group.is_active)


class CookieModelTests(TestCase):
    def setUp(self):
        self.analytics_group = CookieGroup.objects.create(
            name="analytics", display_name="Analityczne", description="Analiza ruchu"
        )
        self.cookie = Cookie.objects.create(
            group=self.analytics_group,
            name="Licznik odwiedzin",
            domain=".example.com",
            purpose="Google Analytics tracking",
            expiry="2 years",
            provider="Google",
        )

    def test_string_representation(self):
        self.assertEqual(str(self.cookie), "Licznik odwiedzin (Analityczne)")

    def test_cookie_creation(self):
        self.assertEqual(self.cookie.name, "Licznik odwiedzin")
        self.assertEqual(self.cookie.group, self.analytics_group)
        self.assertEqual(self.cookie.path, "/")
        self.assertTrue(self.cookie.is_active)

    def test_two_cookies_same_name_different_domain_allowed(self):
        # domain="" (default) zamiast NULL - unique_together działa poprawnie
        # nawet w Postgres, gdzie NULL != NULL (PLAN.md C9).
        Cookie.objects.create(group=self.analytics_group, name="tracker", domain="a.example.com", purpose="x")
        Cookie.objects.create(group=self.analytics_group, name="tracker", domain="b.example.com", purpose="x")
        self.assertEqual(Cookie.objects.filter(name="tracker").count(), 2)


class CookieConsentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        self.necessary_group = CookieGroup.objects.create(
            name="necessary", display_name="Obowiązkowe", description="Niezbędne", is_required=True
        )
        self.analytics_group = CookieGroup.objects.create(
            name="analytics", display_name="Analityczne", description="Analiza"
        )

    def test_consent_creation_has_uuid(self):
        consent = CookieConsent.objects.create(user=self.user, ip_address="127.0.0.1", user_agent="Test Browser")

        self.assertIsInstance(consent.consent_id, uuid.UUID)
        self.assertEqual(consent.user, self.user)
        self.assertTrue(consent.is_valid)
        self.assertIsNotNone(consent.expires_at)

    def test_auto_expires_at_setting(self):
        consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser")

        expected_date = timezone.now() + timedelta(days=conf.CONSENT_DURATION_DAYS)
        self.assertAlmostEqual(consent.expires_at.date(), expected_date.date())

    def test_is_expired(self):
        past_date = timezone.now() - timedelta(days=1)
        consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser", expires_at=past_date)

        self.assertTrue(consent.is_expired())

    def test_has_group_consent(self):
        consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser")
        consent.accepted_groups.add(self.analytics_group)

        self.assertTrue(consent.has_group_consent("analytics"))
        self.assertFalse(consent.has_group_consent("marketing"))

    def test_has_group_consent_expired(self):
        past_date = timezone.now() - timedelta(days=1)
        consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser", expires_at=past_date)
        consent.accepted_groups.add(self.analytics_group)

        self.assertFalse(consent.has_group_consent("analytics"))

    def test_has_group_consent_invalid(self):
        consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser", is_valid=False)
        consent.accepted_groups.add(self.analytics_group)

        self.assertFalse(consent.has_group_consent("analytics"))


class CookieConsentLogModelTests(TestCase):
    def setUp(self):
        CookieGroup.objects.create(name="necessary", display_name="Obowiązkowe", description="Niezbędne")
        self.consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser")

    def test_log_creation_with_jsonfield(self):
        log = CookieConsentLog.objects.create(
            consent=self.consent, action="accept_all", groups_before=[], groups_after=["necessary", "analytics"]
        )

        self.assertEqual(log.consent, self.consent)
        self.assertEqual(log.action, "accept_all")
        self.assertEqual(log.groups_after, ["necessary", "analytics"])
        self.assertIsNotNone(log.timestamp)


class CookieConsentMiddlewareTests(TestCase):
    """PLAN.md C1/C2: middleware czyta zgodę z consent-cookie, nie z sesji."""

    def setUp(self):
        self.middleware = CookieConsentMiddleware(lambda request: None)
        self.necessary_group = CookieGroup.objects.create(
            name="necessary", display_name="Obowiązkowe", description="Niezbędne", is_required=True
        )
        self.analytics_group = CookieGroup.objects.create(
            name="analytics", display_name="Analityczne", description="Analiza"
        )

    def _request(self, path="/", cookies=None):
        from django.http import HttpRequest

        request = HttpRequest()
        request.path = path
        request.COOKIES = cookies or {}
        return request

    def test_no_consent_cookie(self):
        request = self._request()
        self.middleware._attach_consent(request)

        self.assertFalse(request.has_cookie_consent)
        self.assertIsNone(request.cookie_consent)
        self.assertFalse(request.has_analytics_consent)

    def test_valid_consent_cookie(self):
        consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser")
        consent.accepted_groups.add(self.analytics_group)

        request = self._request(cookies={conf.CONSENT_COOKIE_NAME: str(consent.consent_id)})
        self.middleware._attach_consent(request)

        self.assertTrue(request.has_cookie_consent)
        self.assertEqual(request.cookie_consent, consent)
        self.assertTrue(request.has_analytics_consent)

    def test_expired_consent_cookie_not_attached_without_db_write(self):
        past_date = timezone.now() - timedelta(days=1)
        consent = CookieConsent.objects.create(ip_address="127.0.0.1", user_agent="Test Browser", expires_at=past_date)

        request = self._request(cookies={conf.CONSENT_COOKIE_NAME: str(consent.consent_id)})
        self.middleware._attach_consent(request)

        self.assertFalse(request.has_cookie_consent)
        # PLAN.md C4: middleware nie zapisuje do bazy przy GET.
        consent.refresh_from_db()
        self.assertTrue(consent.is_valid)

    def test_skips_static_and_admin_paths(self):
        request = self._request(path="/static/css/site.css")
        self.middleware._attach_consent(request)

        self.assertFalse(request.has_cookie_consent)
        self.assertIsNone(request.cookie_consent)


class CookieConsentViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.necessary_group = CookieGroup.objects.create(
            name="necessary", display_name="Obowiązkowe", description="Niezbędne", is_required=True
        )
        self.analytics_group = CookieGroup.objects.create(
            name="analytics", display_name="Analityczne", description="Analiza"
        )
        self.marketing_group = CookieGroup.objects.create(
            name="marketing", display_name="Marketingowe", description="Personalizacja"
        )

    def test_cookie_preferences_view(self):
        response = self.client.get(reverse("cookies:preferences"))
        self.assertEqual(response.status_code, 200)

    def test_cookie_policy_view(self):
        response = self.client.get(reverse("cookies:policy"))
        self.assertEqual(response.status_code, 200)

    def test_handle_cookie_consent_accept_all_sets_consent_cookie(self):
        response = self.client.post(
            reverse("cookies:consent"), data='{"action": "accept_all"}', content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertIn(conf.CONSENT_COOKIE_NAME, response.cookies)

        consent = CookieConsent.objects.first()
        self.assertIsNotNone(consent)
        self.assertEqual(consent.accepted_groups.count(), 3)

    def test_handle_cookie_consent_reject_all_keeps_required_only(self):
        response = self.client.post(
            reverse("cookies:consent"), data='{"action": "reject_all"}', content_type="application/json"
        )

        self.assertEqual(response.status_code, 200)
        consent = CookieConsent.objects.first()
        self.assertEqual(consent.accepted_groups.count(), 1)
        self.assertTrue(consent.accepted_groups.filter(name="necessary").exists())

    def test_handle_cookie_consent_partial_always_keeps_required(self):
        response = self.client.post(
            reverse("cookies:consent"),
            data='{"action": "save_preferences", "selected_groups": ["analytics"]}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        consent = CookieConsent.objects.first()
        names = set(consent.accepted_groups.values_list("name", flat=True))
        self.assertEqual(names, {"necessary", "analytics"})

    def test_handle_cookie_consent_unknown_action_returns_400(self):
        response = self.client.post(
            reverse("cookies:consent"), data='{"action": "unknown_action"}', content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_csrf_protection_is_enforced(self):
        # PLAN.md B1: brak @csrf_exempt - klient bez tokenu CSRF dostaje 403.
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("cookies:consent"), data='{"action": "accept_all"}', content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)

    def test_consent_survives_login(self):
        """PLAN.md C1/G2: zgoda oparta o consent-cookie przeżywa cycle_key() przy logowaniu."""
        response = self.client.post(
            reverse("cookies:consent"), data='{"action": "accept_all"}', content_type="application/json"
        )
        consent_cookie_value = response.cookies[conf.CONSENT_COOKIE_NAME].value
        consent_before = CookieConsent.objects.get(consent_id=consent_cookie_value)

        self.client.login(username="testuser", password="testpass123")

        response = self.client.get(reverse("cookies:preferences"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.cookies[conf.CONSENT_COOKIE_NAME].value, str(consent_before.consent_id))

    def test_withdraw_consent_view(self):
        response = self.client.post(
            reverse("cookies:consent"), data='{"action": "accept_all"}', content_type="application/json"
        )
        consent_id = response.cookies[conf.CONSENT_COOKIE_NAME].value

        response = self.client.get(reverse("cookies:withdraw"))
        self.assertEqual(response.status_code, 302)

        consent = CookieConsent.objects.get(consent_id=consent_id)
        self.assertEqual(consent.accepted_groups.count(), 1)
        self.assertTrue(consent.accepted_groups.filter(name="necessary").exists())
        self.assertTrue(CookieConsentLog.objects.filter(action="withdraw").exists())

    def test_get_client_ip_with_forwarded_for(self):
        from django.http import HttpRequest

        request = HttpRequest()
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.1, 10.0.0.1"
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        self.assertEqual(get_client_ip(request), "192.168.1.1")

    def test_get_client_ip_without_forwarded_for(self):
        from django.http import HttpRequest

        request = HttpRequest()
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        self.assertEqual(get_client_ip(request), "127.0.0.1")


class CookieConsentTemplateTagTests(TestCase):
    def setUp(self):
        CookieGroup.objects.create(name="necessary", display_name="Obowiązkowe", description="Niezbędne")

    def test_group_script_not_rendered_without_consent(self):
        """PLAN.md G4: bez zgody skrypt analityczny nie renderuje się."""
        from django.http import HttpRequest
        from django.template import Context, Template

        request = HttpRequest()
        request.cookie_consent_groups = set()

        template = Template('{% load cookie_tags %}{% group_script "analytics" "<script>track()</script>" %}')
        rendered = template.render(Context({"request": request}))

        self.assertNotIn("track()", rendered)

    def test_group_script_rendered_with_consent(self):
        from django.http import HttpRequest
        from django.template import Context, Template

        request = HttpRequest()
        request.cookie_consent_groups = {"analytics"}

        template = Template('{% load cookie_tags %}{% group_script "analytics" "<script>track()</script>" %}')
        rendered = template.render(Context({"request": request}))

        self.assertIn("track()", rendered)

    def test_banner_hidden_when_consent_given(self):
        from django.http import HttpRequest
        from django.template import Context, Template

        request = HttpRequest()
        request.has_cookie_consent = True

        template = Template("{% load cookie_tags %}{% cookie_consent_banner %}")
        rendered = template.render(Context({"request": request}))

        self.assertNotIn("cookie-banner", rendered)

    def test_banner_contains_csrf_token(self):
        # cookies.js czyta token z baneru, bo CSRF_COOKIE_HTTPONLY ukrywa ciasteczko przed JS.
        response = self.client.get(reverse("cookies:policy"))

        self.assertRegex(
            response.content.decode(),
            r"data-cookie-banner[^>]*>\s*<input[^>]*csrfmiddlewaretoken",
        )


class CleanupConsentsCommandTests(TestCase):
    """PLAN.md A3/C5/G3: retencja danych przez komendę zarządzającą, nie przez
    losowanie w middleware."""

    def setUp(self):
        CookieGroup.objects.create(name="necessary", display_name="Obowiązkowe", description="Niezbędne")

    def test_marks_expired_consents_invalid(self):
        past_date = timezone.now() - timedelta(days=1)
        consent = CookieConsent.objects.create(
            ip_address="127.0.0.1", user_agent="x", expires_at=past_date, is_valid=True
        )

        CleanupCommand().handle()

        consent.refresh_from_db()
        self.assertFalse(consent.is_valid)

    def test_deletes_old_invalid_consents_past_retention(self):
        old_date = timezone.now() - timedelta(days=conf.CONSENT_RETENTION_DAYS + 10)
        consent = CookieConsent.objects.create(
            ip_address="127.0.0.1", user_agent="x", expires_at=old_date, is_valid=False
        )
        CookieConsent.objects.filter(pk=consent.pk).update(updated_at=old_date)

        CleanupCommand().handle()

        self.assertFalse(CookieConsent.objects.filter(pk=consent.pk).exists())

    def test_keeps_recent_invalid_consents(self):
        consent = CookieConsent.objects.create(
            ip_address="127.0.0.1", user_agent="x", expires_at=timezone.now() - timedelta(days=1), is_valid=False
        )

        CleanupCommand().handle()

        self.assertTrue(CookieConsent.objects.filter(pk=consent.pk).exists())
