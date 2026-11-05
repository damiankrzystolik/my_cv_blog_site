# Strona Portfolio - CV + Blog

Osobista strona portfolio — CV na stronie tytułowej i blog pod `/blog/`. Zbudowana na bazie produkcyjnego szablonu Django (Docker, monitoring, CI, bezpieczeństwo) opisanego poniżej.

---

## Stack

| Warstwa        | Technologia                                        |
|----------------|----------------------------------------------------|
| Framework      | Django 5.2                                         |
| API            | Django REST Framework 3.17 + drf-spectacular       |
| Baza danych    | PostgreSQL 17 + psycopg 3                          |
| Auth           | Custom User model + JWT (simplejwt)                |
| Logging        | structlog → JSON                                   |
| Monitoring     | django-prometheus → Prometheus → Grafana           |
| Error tracking | Sentry SDK                                         |
| Bezpieczeństwo | django-csp, bleach, python-magic                   |
| Admin          | django-axes (brute-force), django-otp (2FA TOTP)   |
| Blog           | django-taggit, Markdown + Pygments, Pillow, pg_trgm |
| Config         | python-decouple (`.env`)                           |
| Serwer         | uWSGI + Nginx                                      |
| SSL            | Let's Encrypt (certbot)                            |
| Kontenery      | Docker / Docker Compose                            |
| Jakość kodu    | ruff, mypy, bandit, pip-audit, pre-commit          |
| Testy          | pytest + factory-boy + coverage                    |

---

## Biblioteki — uzasadnienie

### Framework i API

**Django 5.2** — LTS release z pełnym ekosystemem: ORM, admin, migracje, middleware. Wersja `<5.3` przypięta żeby uniknąć nieoczekiwanych breaking changes przy patch-ach.

**Django REST Framework 3.17** — de facto standard REST API w Django. Serializery, widoki generyczne, permissions, throttling. Zintegrowany z resztą stacku.

**drf-spectacular** — generuje schemat OpenAPI 3 (Swagger UI / ReDoc) bezpośrednio z kodu DRF. Alternatywa `drf-yasg` nie wspiera OpenAPI 3. Schemat jest niezbędny przy API-first development i generowaniu klientów TypeScript/mobile.

**djangorestframework-simplejwt** — JWT authentication dla SPA i klientów mobilnych. SessionAuthentication pozostaje jako fallback dla przeglądarki. JWT nie wymaga trzymania sesji po stronie serwera, co upraszcza skalowanie horyzontalne.

### Baza danych

**psycopg[binary] 3.x** — psycopg3, następca psycopg2. Szybsze pipeline queries, natywna obsługa async, lepiej rozwijane. Django 5.2 ma pełne wsparcie psycopg3. `[binary]` bundle zawiera prebuilt libpq — nie wymaga systemowego `libpq-dev` w runtime image.

**django-prometheus** (backend bazy) — zamienia domyślny backend PostgreSQL na wrapper który mierzy czas i liczbę zapytań SQL. Zmiana jednej linii w settings, zero zmian w kodzie.

### Bezpieczeństwo

**django-csp** — dodaje nagłówek `Content-Security-Policy` do każdej odpowiedzi. CSP blokuje XSS na poziomie przeglądarki — nawet jeśli atakujący wstrzyknie skrypt, przeglądarka odmówi jego wykonania bo nie pochodzi z whitelisty. Konfiguracja w `base.py`.

**bleach** — sanityzacja HTML na poziomie aplikacji: `sanitize_html()` w `apps/core/utils.py`. Używać wszędzie tam gdzie user-generated content trafia do bazy i z powrotem do HTML. django-csp chroni przed XSS w przeglądarce, bleach chroni przed XSS zanim dane trafią do bazy.

**python-magic** — weryfikuje rzeczywisty MIME type pliku przez odczyt magic bytes, nie tylko rozszerzenie. Plik `evil.exe` z rozszerzeniem `.jpg` zostanie odrzucony. Używany w `validate_file_extension()` w `apps/core/validators.py`. Wymaga `libmagic1` w kontenerze (jest w Dockerfile).

**django-axes** — blokuje logowanie po 5 nieudanych próbach dla pary użytkownik + IP, blokada znika po 1 godzinie (`AXES_*` w `base.py`). Ten sam login z innego IP i inne loginy z tego IP nie są blokowane, więc ktoś znający login nie odetnie właściciela od panelu. `AXES_LOCKOUT_PARAMETERS` musi być listą zagnieżdżoną (`[["username", "ip_address"]]` = kombinacja; płaska lista oznacza „lub”), a przy logowaniu po e-mailu potrzebne jest `AXES_USERNAME_FORM_FIELD = "username"` — bez tego axes zapisuje login jako `None`. `AxesStandaloneBackend` stoi pierwszy w `AUTHENTICATION_BACKENDS`, więc blokada jest sprawdzana zanim `ModelBackend` w ogóle zweryfikuje hasło. W testach wyłączony (`AXES_ENABLED = False` w `testing.py`), żeby testy logowania nie wyzwalały blokady.

**django-otp** — drugi składnik logowania do panelu admina. `admin.site` jest podmieniony na `OTPAdminSite` (`config/urls.py`): formularz logowania ma pole na kod, a dostęp wymaga `request.user.is_verified()` oprócz `is_staff`. Urządzenia: `TOTPDevice` (kody z aplikacji typu Google Authenticator / Aegis) i `StaticDevice` (jednorazowe kody zapasowe). Bez `django-two-factor-auth` nie ma ekranu rejestracji urządzenia — zakłada się je przez shell (patrz [Panel admina — 2FA](#panel-admina--2fa)).

### Blog

**django-taggit** — tagi postów (`TaggableManager`) bez własnych modeli i tabel pośrednich. `TAGGIT_CASE_INSENSITIVE = True`, żeby „Django” i „django” były jednym tagiem.

**Markdown + Pygments** — treść postów pisana w Markdownie, bloki kodu podświetlane przez Pygments (style w `static/blog/css/pygments.css`). Wynikowy HTML przechodzi przez bleach z osobną whitelistą (`apps/blog/rendering.py`) zanim trafi do szablonu.

**Pillow** — wymagany przez `ImageField` (obrazki postów, `BlogImage`).

**pg_trgm** (`django.contrib.postgres`) — wyszukiwarka po tytułach przez `TrigramSimilarity`, odporna na literówki. Rozszerzenie włącza migracja `blog.0002` — kod bloga nie zadziała na SQLite.

### Logging

**structlog** — logi jako JSON zamiast płaskiego tekstu. Każdy log-line to obiekt z polami `event`, `level`, `timestamp`, plus dowolne pola kontekstowe (request_id, user_id). JSON może być parsowany przez Loki, Elasticsearch, CloudWatch bez regexów. Zintegrowany z Django `logging` przez `ProcessorFormatter` — logi Django (`django.request`, `django.db`) też idą przez structlog.

### Monitoring i obserwowalność

**django-prometheus** — instrumentuje Django bez zmian w kodzie aplikacji:
- middleware mierzy czas i liczbę requestów HTTP (z podziałem na status, metodę, widok)
- backend bazy mierzy zapytania SQL
- metryki eksportuje na porcie `9100` (wewnętrznym, niedostępnym z zewnątrz)

**Prometheus** — baza danych szeregów czasowych wyspecjalizowana w metrykach. Co 15s robi GET na `web:9100/metrics` i zapisuje dane. Posiada własny język zapytań (PromQL) i silnik alertów. Dane trzymane 30 dni (konfigurowalne).

**Grafana** — wizualizacja metryk z Prometheusa. Dostępna na `localhost:3000` (przez SSH tunnel — nie wystawiona publicznie). Datasource i lokalizacja dashboardów skonfigurowane automatycznie przez provisioning (`config/grafana/provisioning/`). Import gotowych dashboardów: [Django](https://grafana.com/grafana/dashboards/17658), [PostgreSQL](https://grafana.com/grafana/dashboards/9628).

### Error tracking

**Sentry SDK** — przechwytuje nieobsłużone wyjątki i wysyła do Sentry (SaaS lub self-hosted) wraz z pełnym stack trace, kontekstem requesta i zmiennymi lokalnymi. `send_default_pii=False` — nie wysyła danych osobowych. `traces_sample_rate=0.1` — 10% requestów jest tracowanych (performance). Konfiguracja przez `SENTRY_DSN` w `.env`.

### Konfiguracja

**python-decouple** — odczytuje zmienne ze środowiska lub pliku `.env`. Hierarchia: env var → `.env` → wartość domyślna. `Csv()` cast automatycznie splituje `ALLOWED_HOSTS=foo.com,bar.com` na listę. `.env` nie trafia do repozytorium (`.gitignore`), `.env.example` dokumentuje wszystkie wymagane zmienne.

### Serwer

**uWSGI** — WSGI application server dla produkcji. Obsługuje wiele workerów, preforking, graceful reload (`SIGUSR1`). Konfiguracja w `config/uwsgi/uwsgi.ini`. Tylko w produkcji — development używa `runserver`.

**Nginx** — reverse proxy przed uWSGI. Obsługuje SSL termination, serwuje static files i media bez angażowania Pythona, buforuje upload plików. W dev: HTTP na 80. W prod: HTTP redirect → HTTPS na 443, certyfikaty z Let's Encrypt.

### CORS

**django-cors-headers** — nagłówki CORS dla requestów z przeglądarki (SPA, mobile). W produkcji lista domen w `CORS_ALLOWED_ORIGINS`. W developmencie `CORS_ALLOW_ALL_ORIGINS=True` dla wygody.

### Jakość kodu i testy

**ruff** — linter i formatter (zastępuje flake8 + isort + black). Napisany w Rust, ~100x szybszy. Konfiguracja w `pyproject.toml`.

**mypy + django-stubs** — statyczna analiza typów. `django-stubs` dostarcza typy dla Django ORM, requestów, modeli. Konfiguracja w `pyproject.toml` pod `[tool.mypy]`.

**bandit** — SAST: skanuje AST w poszukiwaniu typowych błędów bezpieczeństwa (hardcoded passwords, SQL injection, insecure deserialization). Uruchamiany w CI.

**pip-audit** — sprawdza zainstalowane pakiety pod kątem znanych CVE (baza OSV). Uruchamiany w CI.

**pytest + django** — testy z `pytest-django`. Fixtures w `conftest.py`. Coverage minimum 70%.

**factory-boy** — fabryki testowych obiektów Django zamiast ręcznego tworzenia fixtures. Integracja z Faker.

**pre-commit** — git hooks: ruff przed każdym commitem, blokuje push z nieformatowanym kodem. Konfiguracja w `.pre-commit-config.yaml`.

---

## Struktura projektu

```
.
├── apps/
│   ├── core/                   # shared utilities, middleware, base models
│   │   ├── utils.py            # generate_unique_slug, sanitize_html, get_client_ip
│   │   ├── validators.py       # validate_file_extension (MIME + magic bytes)
│   │   ├── middleware.py       # RequestContextMiddleware (request_id)
│   │   └── exceptions.py
│   ├── users/                  # custom user model + CRUD API
│   ├── cookies/                # cookie consent management (banner, preferences, policy)
│   │   ├── models.py           # CookieConsent
│   │   ├── middleware.py       # CookieConsentMiddleware
│   │   ├── management/commands/ # setup_cookies, cleanup_consents
│   │   └── README.md
│   ├── cv/                     # static CV/homepage app (served at "/")
│   └── blog/                   # blog at "/blog/": posts (Markdown), tags, comments, search, RSS, sitemap
│       ├── models.py           # Post, Comment, BlogImage
│       ├── selectors.py        # PostSelector — zapytania (prefetch, wyszukiwanie trigramowe)
│       ├── services.py         # CommentService — limit, hash IP, e-mail do właściciela
│       ├── rendering.py        # Markdown → sanityzowany HTML, znaczniki [[imageN]]
│       ├── feeds.py / sitemaps.py
│       └── tests/
├── config/
│   ├── settings/
│   │   ├── base.py             # wspólne: apps, middleware, DRF, CSP, structlog, LOGGING
│   │   ├── development.py      # debug toolbar, CORS allow all, SQLite-like dev settings
│   │   ├── production.py       # security headers, Sentry, Prometheus port
│   │   └── testing.py          # Postgres z env DB_*, fast hashers, locmem e-mail
│   ├── nginx/
│   │   ├── local.conf.template     # HTTP, proxy do runserver
│   │   └── default.conf.template   # HTTPS + Let's Encrypt
│   ├── prometheus/
│   │   ├── prometheus.yml      # scrape config (web:9100)
│   │   └── alerts.yml          # reguły alertów (500 errors, slow responses)
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── datasources/    # auto-konfiguracja Prometheusa jako datasource
│   │       └── dashboards/     # lokalizacja plików .json z dashboardami
│   ├── uwsgi/
│   │   └── uwsgi.ini
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── requirements/
│   ├── base.txt / base.lock         # produkcja
│   ├── development.txt / dev.lock   # lokalne dev
│   ├── production.txt / prod.lock   # + uWSGI
│   └── testing.txt / test.lock      # + pytest, mypy, bandit
├── scripts/
│   └── wait-for-it.sh
├── docker-compose.local.yml    # dev: db + web (runserver) + nginx
├── docker-compose.prod.yml     # prod: db + web (uWSGI) + nginx + certbot + prometheus + grafana
├── docker-compose.test.yml     # pytest w kontenerze + Postgres test-db (tmpfs)
├── Dockerfile
├── Makefile
├── pyproject.toml              # ruff + pytest + coverage + mypy config
└── conftest.py
```

---

## Quick Start

### Lokalnie z Dockerem

```bash
cp .env .env
# uzupełnij SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD

make docker-build
make docker-up       # http://localhost
make docker-logs
make docker-down
```

### Lokalnie bez Dockera

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
make install         # uv pip install -r requirements/development.lock + pre-commit
make migrate
make run             # http://localhost:8000
```

---

## Environment Variables

Skopiuj `.env.example` i uzupełnij:

```env
SECRET_KEY=
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=5432
DJANGO_SETTINGS_MODULE=config.settings.development

# Produkcja
ALLOWED_HOSTS=
DOMAIN=                  # domena bez https:// i www, np. example.com — nginx i certyfikat
CORS_ALLOWED_ORIGINS=
CSRF_TRUSTED_ORIGINS=
SENTRY_DSN=
ADMIN_URL=admin/         # ścieżka panelu admina (domyślnie admin/) — tylko redukcja szumu od botów, nie zabezpieczenie
GRAFANA_ADMIN_PASSWORD=

# Poczta (powiadomienia o komentarzach na blogu) — bez EMAIL_HOST maile lądują w logach (console)
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=
BLOG_COMMENT_NOTIFY_EMAILS=   # adresy oddzielone przecinkami
```

---

## Settings

| Plik             | Kiedy używany                                         |
|------------------|-------------------------------------------------------|
| `base.py`        | wspólny — apps, middleware, DRF, CSP, structlog       |
| `development.py` | lokalnie — debug toolbar, CORS allow all              |
| `production.py`  | produkcja — security headers, Sentry, Prometheus port |
| `testing.py`     | testy — Postgres (env `DB_*`), szybkie hashery        |

---

## Makefile

### Development

```bash
make lock             # regeneruj .lock przez uv pip compile (Linux/py3.12)
make install          # uv pip install + pre-commit

make run              # runserver
make migrate          # makemigrations + migrate
make test             # pytest + coverage
make test-fast        # pytest -x -q
make lint             # ruff check + format check
make lint-fix         # ruff autofix
make security         # bandit + pip-audit
make ci               # lint + test + security
make shell            # shell_plus
```

### Docker lokalny

```bash
make docker-build              # zbuduj image
make docker-up                 # uruchom stack (db + web + nginx)
make docker-down
make docker-stop               # zatrzymaj kontenery bez usuwania
make docker-start              # wznów zatrzymane kontenery
make docker-logs
make docker-migrate            # makemigrations + migrate w kontenerze
make docker-check-makemigrations  # czy brakuje plików migracji (--check --dry-run)
make docker-check-migrate      # czy wszystkie migracje są zastosowane
make docker-showmigrations     # lista migracji i ich stan
make docker-check-deploy       # manage.py check --deploy
make docker-collectstatic
make docker-createsuperuser
make docker-shell              # shell_plus w kontenerze
make docker-test               # pytest w kontenerze
make docker-clean              # down -v + docker system prune
```

### Produkcja

```bash
make prod-build                # zbuduj image (uv + lock files)
make prod-up                   # uruchom cały stack
make prod-migrate              # migracje
make prod-collectstatic        # pliki statyczne
make prod-createsuperuser      # konto admina
make prod-ssl DOMAIN=example.com EMAIL=admin@example.com  # certyfikat SSL
make prod-cron-install         # autoodnowienie certyfikatu (cron co 12h, wpisuje się do crontab)
make prod-logs                 # sprawdź logi
make prod-deploy               # kolejne aktualizacje: build + up + migrate + collectstatic
make prod-restart              # restart tylko kontenera web
make prod-ssl-renew            # ręczne wymuszenie odnowienia certyfikatu
make prod-cron-remove          # usuń autoodnowienie z crontab
make prod-shell                # manage.py shell
make prod-down
```

---

## Deploy (produkcja)

### Wymagania na serwerze

```bash
# docker + docker compose v2
curl -fsSL https://get.docker.com | sh

# uv (do generowania lock files gdy requirements się zmienią)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Pierwsze wdrożenie

```bash
git clone <repo> && cd <repo>

cp .env .env
nano .env                  # uzupełnij SECRET_KEY, DB_*, ALLOWED_HOSTS, GRAFANA_ADMIN_PASSWORD ...

make prod-build            # zbuduj image (pobiera uv, instaluje z lock files)
make prod-up               # uruchom: db, web, nginx, certbot, prometheus, grafana
make prod-migrate
make prod-collectstatic
make prod-createsuperuser
make prod-shell            # załóż urządzenie 2FA dla admina — patrz "Panel admina — 2FA"

# certyfikat SSL — domena musi już wskazywać na serwer (A record w DNS)
make prod-ssl DOMAIN=example.com EMAIL=admin@example.com

# autoodnowienie — wpisuje zadanie do crontab hosta, uruchamia certbot co 12h
# certbot pomija odnowienie jeśli certyfikat ma >30 dni ważności, więc jest bezpieczne
make prod-cron-install

make prod-logs             # sprawdź czy wszystko działa
```

### Kolejne aktualizacje

```bash
git pull
make prod-deploy           # build web + up + migrate + collectstatic jedną komendą
```

---

## Panel admina — 2FA

Panel jest pod `/admin/` albo pod ścieżką z `ADMIN_URL` w `.env` (po zmianie: restart kontenera). Hasła kont muszą mieć min. 12 znaków.

Logowanie do panelu wymaga hasła **i** kodu z aplikacji uwierzytelniającej. Superuser bez urządzenia OTP nie zaloguje się wcale — dotyczy to każdej nowej lub wyczyszczonej bazy (np. po `make docker-clean`).

Urządzenie zakłada się w shellu (`make docker-shell` lokalnie, `make prod-shell` na serwerze):

```python
from django.contrib.auth import get_user_model
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

user = get_user_model().objects.get(email="admin@example.com")

totp = TOTPDevice.objects.create(user=user, name="authenticator", confirmed=True)
print(totp.config_url)  # otpauth://... → wklej/zeskanuj w aplikacji (Aegis, Google Authenticator)

backup = StaticDevice.objects.create(user=user, name="backup")
for _ in range(10):
    print(StaticToken.objects.create(device=backup, token=StaticToken.random_token()).token)
```

Kody zapasowe zapisz poza serwerem — każdy działa jeden raz. Urządzenia są też widoczne i edytowalne w adminie (sekcje *OTP_TOTP* / *OTP_STATIC*).

Zablokowany przez axes (5 błędnych logowań): poczekaj godzinę albo `manage.py axes_reset`.

---

## Monitoring (Prometheus + Grafana)

Po `make prod-up` dostępne przez SSH tunnel:

```bash
# Na serwerze:
ssh -L 9090:localhost:9090 -L 3000:localhost:3000 user@your-server.com

# Lokalnie:
# Prometheus UI  →  http://localhost:9090
# Grafana        →  http://localhost:3000   (admin / $GRAFANA_ADMIN_PASSWORD)
```

Porty `9090` i `3000` **nie są wystawione publicznie** — bindują tylko do `127.0.0.1` na serwerze.

Port `9100` (metryki Django) nie jest wystawiony w ogóle poza siecią Docker — dostępny tylko dla kontenera Prometheus.

### Architektura monitoringu

```
internet ──► nginx:443 ──► web:8000 (uWSGI)
                               │ :9100/metrics (tylko sieć Docker)
                               ▼
                          prometheus:9090 ──scrape co 15s
                               │
                               ▼
                          grafana:3000 ──── dashboardy
```

### Gotowe dashboardy

Importuj przez Grafana UI (Dashboards → Import → wpisz ID):

| Dashboard | ID |
|---|---|
| Django (requests, errors, latency) | `17658` |
| PostgreSQL | `9628` |
| Node Exporter (CPU/RAM serwera) | `1860` |

### Alerty

Reguły w `config/prometheus/alerts.yml`:

| Alert | Warunek |
|---|---|
| `HighErrorRate` | >5% odpowiedzi 500 przez 2 minuty |
| `SlowResponses` | p95 latency >2s przez 5 minut |
| `DatabaseQuerySlow` | p95 czasu SQL >500ms przez 5 minut |
| `AppDown` | Django nie odpowiada na scrape |

Alerty są widoczne w Prometheus UI (`/alerts`). Żeby dostawać powiadomienia (Slack, email, PagerDuty) — dodaj Alertmanager do `docker-compose.prod.yml` i uzupełnij `alertmanagers` w `config/prometheus/prometheus.yml`.

---

## Tests

```bash
make test           # lokalnie
make docker-test    # w kontenerze (docker-compose.test.yml)
```

Testy idą na PostgreSQL, tak jak produkcja: `make docker-test` stawia osobny kontener `test-db` (baza na tmpfs), w CI działa service `postgres`. `make test` lokalnie wymaga Postgresa dostępnego pod `DB_HOST`/`DB_PORT` z `testing.py`.

Coverage minimum: **70%** (`pyproject.toml`).
