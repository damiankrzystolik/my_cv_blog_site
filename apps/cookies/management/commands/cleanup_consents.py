from cookies import conf
from cookies.models import CookieConsent
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    """Oznacza wygasłe zgody jako nieważne i trwale usuwa stare rekordy.

    Zastępuje poprzednie podejście, w którym CookieCleanupMiddleware losowo
    (1% żądań) odpalał UPDATE na każdym żądaniu HTTP - co dawało efekty
    uboczne przy zwykłym GET i niedeterministyczne czyszczenie (PLAN.md C4/C5).

    Uruchamiać z crona, np. raz dziennie:
        0 3 * * * python manage.py cleanup_consents

    Usuwanie starych zgód po COOKIE_CONSENT_RETENTION_DAYS realizuje zasadę
    minimalizacji danych z RODO - IP i User-Agent to dane osobowe, które nie
    powinny być przechowywane bez końca (PLAN.md A3).
    """

    help = "Oznacza wygasłe zgody jako nieważne i usuwa zgody starsze niż okres retencji."

    def handle(self, *args, **options):
        now = timezone.now()

        expired_count = CookieConsent.objects.filter(expires_at__lt=now, is_valid=True).update(is_valid=False)
        self.stdout.write(f"Oznaczono jako nieważne: {expired_count} zgód.")

        retention_cutoff = now - timezone.timedelta(days=conf.CONSENT_RETENTION_DAYS)
        deleted_count, _ = CookieConsent.objects.filter(is_valid=False, updated_at__lt=retention_cutoff).delete()
        self.stdout.write(f"Trwale usunięto: {deleted_count} starych zgód (wraz z logami, CASCADE).")

        self.stdout.write(self.style.SUCCESS("Czyszczenie zgód zakończone."))
