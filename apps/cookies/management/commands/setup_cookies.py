from cookies.models import Cookie, CookieGroup
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Tworzy podstawowe grupy i ciasteczka (dane startowe / fixtures)."

    def handle(self, *args, **options):
        self.stdout.write("Tworzenie grup ciasteczek...")

        necessary, created = CookieGroup.objects.get_or_create(
            name="necessary",
            defaults={
                "display_name": "Obowiązkowe",
                "description": (
                    "Te ciasteczka są niezbędne do prawidłowego działania strony internetowej. "
                    "Nie można ich wyłączyć."
                ),
                "is_required": True,
            },
        )
        if created:
            self.stdout.write(f"Utworzono grupę: {necessary.display_name}")

        analytics, created = CookieGroup.objects.get_or_create(
            name="analytics",
            defaults={
                "display_name": "Analityczne",
                "description": (
                    "Te ciasteczka pomagają nam zrozumieć, jak odwiedzający korzystają z naszej strony, "
                    "zbierając informacje anonimowo."
                ),
                "is_required": False,
            },
        )
        if created:
            self.stdout.write(f"Utworzono grupę: {analytics.display_name}")

        marketing, created = CookieGroup.objects.get_or_create(
            name="marketing",
            defaults={
                "display_name": "Marketingowe",
                "description": "Te ciasteczka są używane do personalizacji treści i wyświetlania odpowiednich reklam.",
                "is_required": False,
            },
        )
        if created:
            self.stdout.write(f"Utworzono grupę: {marketing.display_name}")

        cookies_data = [
            {
                "group": necessary,
                "name": "sessionid",
                "domain": "",
                "purpose": (
                    "Ciasteczka sesyjne to tymczasowe pliki, które przechowujemy na Twoim urządzeniu wyłącznie "
                    "na czas Twojej wizyty na naszej stronie. Są one niezbędne do prawidłowego działania serwisu, "
                    "ponieważ pozwalają utrzymać kluczowe funkcje, takie jak stan zalogowania czy zawartość koszyka. "
                    "Pliki te są automatycznie usuwane w momencie zamknięcia przeglądarki internetowej i nie "
                    "gromadzą Twoich danych osobowych."
                ),
                "expiry": "Session",
                "provider": "Django",
            },
            {
                "group": necessary,
                "name": "csrftoken",
                "domain": "",
                "purpose": (
                    "Ciasteczka z tokenem CSRF (Cross-Site Request Forgery) to kluczowy element bezpieczeństwa, "
                    "chroniący Twoje konto przed nieautoryzowanymi działaniami. Działają jak unikalny, jednorazowy "
                    "identyfikator dla każdej Twojej akcji na stronie, takiej jak zmiana hasła czy dokonanie "
                    "zakupu. Kiedy wysyłasz żądanie, serwer sprawdza, czy dołączony token CSRF pasuje do tego, "
                    "który został wcześniej wygenerowany specjalnie dla Ciebie."
                ),
                "expiry": "1 rok",
                "provider": "Django",
            },
            {
                "group": necessary,
                "name": "messages",
                "domain": "",
                "purpose": (
                    "Przechowywanie komunikatów systemowych i powiadomień wyświetlanych użytkownikowi "
                    "po wykonaniu określonych akcji. Nie zawierają danych osobowych, tylko teksty informacyjne."
                ),
                "expiry": "Session",
                "provider": "Django",
            },
            {
                "group": necessary,
                "name": "cookie_consent_id",
                "domain": "",
                "purpose": (
                    "Przechowuje identyfikator Twojej zgody na ciasteczka, dzięki czemu nie musimy pytać o nią "
                    "przy każdej wizycie. Nie zawiera danych osobowych - to wyłącznie techniczny identyfikator."
                ),
                "expiry": "180 dni",
                "provider": "Ta strona",
            },
            {
                "group": analytics,
                "name": "Licznik odwiedzin",
                "domain": "",
                "purpose": "Zliczanie odwiedzających - pomaga nam zrozumieć, ile osób odwiedza naszą stronę.",
                "expiry": "2 lata",
                "provider": "Google Analytics",
            },
            {
                "group": analytics,
                "name": "Statystyki dzienne",
                "domain": "",
                "purpose": "Śledzi aktywność użytkowników w ciągu dnia.",
                "expiry": "24 godziny",
                "provider": "Google Analytics",
            },
        ]

        for cookie_data in cookies_data:
            # get_or_create po (name, domain) - identyczne z constraintem
            # unique_together modelu, dzięki domain="" (nie NULL) (PLAN.md C9/C10).
            cookie, created = Cookie.objects.get_or_create(
                name=cookie_data["name"],
                domain=cookie_data["domain"],
                defaults={
                    "group": cookie_data["group"],
                    "purpose": cookie_data["purpose"],
                    "expiry": cookie_data["expiry"],
                    "provider": cookie_data["provider"],
                },
            )
            if created:
                self.stdout.write(f"Utworzono ciasteczko: {cookie.name}")

        self.stdout.write(self.style.SUCCESS("Pomyślnie utworzono grupy i ciasteczka!"))
