# apps.cookies

Aplikacja do zarządzania zgodą na ciasteczka (banner, preferencje, polityka,
logi zgód) zgodna z wymogami RODO/UODO — z minimalizacją danych i bez
ciasteczek śledzących bez zgody użytkownika.

## 1. Instalacja w projekcie

### 1.1 INSTALLED_APPS

W `config/settings/base.py` w `LOCAL_APPS`:

```python
LOCAL_APPS = [
    ... ,
    "apps.cookies",
]
```

### 1.2 MIDDLEWARE

`CookieConsentMiddleware` odczytuje ciasteczko zgody i dołącza do `request`
atrybuty `cookie_consent`, `has_cookie_consent`, `cookie_consent_groups`,
`has_analytics_consent`, `has_marketing_consent`. Tylko czyta — nigdy nie
zapisuje do bazy przy GET.

Dodać w `config/settings/base.py` w `MIDDLEWARE` (po
`apps.core.middleware.RequestContextMiddleware`, przed
`PrometheusAfterMiddleware` — nie jest to krytyczne, ale middleware musi być
zarejestrowany, żeby request miał te atrybuty):

```python
MIDDLEWARE = [
    ...
    "apps.core.middleware.RequestContextMiddleware",
    "apps.cookies.middleware.CookieConsentMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]
```

### 1.3 urls.py

W `config/urls.py` dołączyć URL-e aplikacji pod prefiksem `cookies/`:

```python
urlpatterns = [
    ...
    path("cookies/", include("apps.cookies.urls")),
]
```

Udostępnia to:

| Nazwa (namespace `cookies:`) | URL                     | Opis                                   |
|-------------------------------|-------------------------|-----------------------------------------|
| `cookies:preferences`         | `/cookies/preferences/` | Strona zarządzania preferencjami        |
| `cookies:policy`              | `/cookies/policy/`      | Strona z polityką ciasteczek            |
| `cookies:consent`             | `/cookies/consent/`     | POST — zapis zgody (AJAX/JSON lub form) |
| `cookies:withdraw`            | `/cookies/withdraw/`    | Wycofanie zgody                         |

Sam baner **nie ma** własnego URL-a — jest partialem wstrzykiwanym do
szablonu przez templatetag (patrz pkt 1.4).

### 1.4 Baner w base.html

W szablonie bazowym projektu (`templates/base.html`), tuż przed `</body>`:

```django
{% load static cookie_tags %}
<link rel="stylesheet" href="{% static 'cookies/css/cookies.css' %}">
...
{% cookie_consent_banner %}
<script src="{% static 'cookies/js/cookies.js' %}"></script>
```

`cookie_consent_banner` renderuje `templates/cookies/banner.html` tylko gdy
`request.has_cookie_consent` jest `False` (czyli gdy użytkownik jeszcze nie
podjął decyzji albo zgoda wygasła).

### 1.5 Wstrzykiwanie skryptów warunkowo na zgodę

Do osadzania skryptów (Google Analytics, piksele marketingowe itd.), które
mogą się wykonać tylko po zgodzie na daną grupę:

```django
{% load cookie_tags %}
{% group_script "analytics" google_analytics_snippet %}
```

`script_content` to string z kodem skryptu — renderowany tylko jeśli grupa
`group_name` jest w `request.cookie_consent_groups`.

### 1.6 Migracje

```
python manage.py migrate cookies
```

albo w Dockerze:

```
make docker-migrate
```

### 1.7 Statyczne pliki (CSS/JS)

CSS/JS leżą w `static/cookies/` (nie `apps/cookies/static/` — projekt trzyma
wszystkie statyki centralnie, patrz `STATICFILES_DIRS` w
`config/settings/base.py`). Po dodaniu/zmianie plików **trzeba odpalić
`collectstatic`**, inaczej nginx (który serwuje `/static/` z `staticfiles/`,
nie z `static/`) zwróci 404 dla CSS/JS, a baner będzie wyglądał jak
niestylowany div i przyciski nie będą reagować na kliknięcie:

```
make docker-collectstatic
```

### 1.8 Dane startowe (grupy i ciasteczka)

Bez tego kroku `/cookies/policy/` i `/cookies/preferences/` będą puste, a w
adminie nie zobaczysz żadnych `CookieGroup`/`Cookie`:

```
python manage.py setup_cookies
```

albo w Dockerze:

```
docker compose -f docker-compose.local.yml exec web python manage.py setup_cookies
```

Komenda jest idempotentna (`get_or_create`) — można odpalać wielokrotnie.

### 1.9 Czyszczenie wygasłych zgód (cron)

`cleanup_consents` oznacza wygasłe zgody jako nieważne i trwale usuwa stare
rekordy po `COOKIE_CONSENT_RETENTION_DAYS` (minimalizacja danych RODO — IP i
User-Agent to dane osobowe). Middleware **nigdy** nie robi tego przy GET.

Odpalać z crona, raz dziennie:

```
0 3 * * * python manage.py cleanup_consents
```

## 2. Konfiguracja (opcjonalna)

Wszystkie ustawienia mają sensowne wartości domyślne (`apps/cookies/conf.py`).
Można je nadpisać w `settings.py` projektu:

| Ustawienie                          | Domyślnie                  | Opis                                              |
|--------------------------------------|-----------------------------|----------------------------------------------------|
| `COOKIE_CONSENT_COOKIE_NAME`         | `"cookie_consent_id"`       | Nazwa first-party ciasteczka z UUID zgody          |
| `COOKIE_CONSENT_DURATION_DAYS`       | `180`                        | Ważność zgody w dniach                             |
| `COOKIE_CONSENT_RETENTION_DAYS`      | `365`                        | Po ilu dniach od wygaśnięcia dane są trwale usuwane|
| `COOKIE_CONSENT_STORE_IP`            | `True`                       | Czy zapisywać adres IP przy zgodzie                |
| `COOKIE_CONSENT_COOKIE_SECURE`       | `not DEBUG`                  | Flaga `Secure` ciasteczka zgody                    |
| `COOKIE_CONSENT_COOKIE_SAMESITE`     | `"Lax"`                      | Atrybut `SameSite` ciasteczka zgody                |
| `COOKIE_CONSENT_CONTACT_EMAIL`       | `"damiankrzystolik@gmail.com"` | E-mail wyświetlany w polityce cookies            |

## 3. Architektura — kluczowe decyzje

- **`consent_id` (UUID) w osobnym ciasteczku, nie `session_key`.** Klucz
  sesji rotuje się przy logowaniu (`cycle_key`), co sprawiałoby, że zgoda
  "znika" i baner wraca tuż po zalogowaniu.
- **`domain=""` (nie `NULL`) w modelu `Cookie`.** W Postgresie `NULL != NULL`
  psuje `unique_together` i pozwala wstawić duplikaty.
- **Middleware nigdy nie zapisuje do bazy przy GET.** Oznaczanie wygasłych
  zgód i czyszczenie odbywa się wyłącznie w `cleanup_consents` (cron) —
  unika to efektów ubocznych przy zwykłym żądaniu GET.
- **Brak `mark_safe()`/inline JS/CSS w bannerze.** CSS/JS są w plikach
  statycznych, co pozwala na restrykcyjne CSP bez `'unsafe-inline'`.
- **`group_script` jest generyczny**, nie ma osobnych
  `analytics_script`/`marketing_script` — działa dla dowolnej grupy
  zdefiniowanej w `CookieGroup`.

## 4. Modele

- `CookieGroup` — kategoria ciasteczek (`necessary`, `analytics`,
  `marketing`); `is_required=True` oznacza grupę zawsze włączoną.
- `Cookie` — katalogowy wpis pojedynczego ciasteczka (do polityki cookies),
  przypisany do grupy.
- `CookieConsent` — zgoda użytkownika, identyfikowana przez `consent_id`;
  `accepted_groups` (M2M do `CookieGroup`); `expires_at`/`is_valid`.
- `CookieConsentLog` — rejestr działań (`accept_all`, `reject_all`,
  `partial`, `withdraw`) do wykazania zgodności (audit trail).

## 5. Checklist wdrożenia w nowym projekcie

- [ ] `apps.cookies` w `INSTALLED_APPS`
- [ ] `CookieConsentMiddleware` w `MIDDLEWARE`
- [ ] `path("cookies/", include("apps.cookies.urls"))` w `config/urls.py`
- [ ] `{% cookie_consent_banner %}` + CSS/JS w `templates/base.html`
- [ ] `python manage.py migrate cookies`
- [ ] `python manage.py collectstatic` (po każdej zmianie w `static/cookies/`)
- [ ] `python manage.py setup_cookies` (dane startowe grup/ciasteczek)
- [ ] wpis crona dla `cleanup_consents`
