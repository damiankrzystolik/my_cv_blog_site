# Changelog

## [Unreleased]

## [0.6.0] - 2026-11-04
### Added
- `apps/blog`: pełny blog pod `/blog/` zamiast placeholdera — posty w Markdownie z podświetlaniem składni (Pygments), tagi (`django-taggit`), obrazki wstawiane w treść przez znaczniki `[[image1]]`, `[[image2]]`… (model `BlogImage`, jeden obrazek wyróżniony na liście postów), szkice i publikacja z datą (`Post.published`), paginacja, linki do udostępniania posta
- Komentarze pod postami — widoczne od razu, moderowane w adminie. Ochrona przed spamem: pole-pułapka (honeypot) i limit 10 komentarzy na godzinę z jednego IP (`BLOG_COMMENT_RATE_LIMIT`); w bazie zapisywany jest HMAC adresu IP, nie sam adres. Właściciel dostaje e-mail o nowym komentarzu (`BLOG_COMMENT_NOTIFY_EMAILS`)
- Wyszukiwarka postów po tytule odporna na literówki (`TrigramSimilarity`, rozszerzenie `pg_trgm` włączane migracją `blog.0002`)
- Kanał RSS (`/blog/feed/`) i `sitemap.xml` z postami i tagami
- Wyrenderowany Markdown jest sanityzowany przez bleach (whitelista tagów, atrybutów i protokołów linków) przed oznaczeniem jako bezpieczny
- `apps.core.utils.get_client_ip` — adres klienta z nagłówka `X-Real-IP` ustawianego przez nginx
- Konfiguracja poczty wychodzącej przez `.env` (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`), przekazywana też w `docker-compose.prod.yml`
- Zależności: `django-taggit`, `Markdown`, `Pygments`, `Pillow`
- Testy bloga: sanityzacja Markdownu, widoczność szkiców, tagi, paginacja, liczba zapytań, wyszukiwanie z literówkami, komentarze (limit, honeypot, e-mail, escapowanie), RSS, sitemap

### Changed
- Testy działają na PostgreSQL zamiast SQLite — lokalnie osobny kontener `test-db` (`postgres:17.4-alpine`, baza na tmpfs) w `docker-compose.test.yml`, w CI service `postgres`. SQLite różnił się od produkcji zachowaniem zapytań i nie ma `pg_trgm`
- Ustawienia poczty przeniesione do `base.py`: backend SMTP, gdy ustawiono `EMAIL_HOST`, w przeciwnym razie console (wcześniej console był wpisany na sztywno w `development.py`)

## [0.5.0] - 2026-11-03
### Added
- Ścieżka panelu admina konfigurowalna przez zmienną `ADMIN_URL` w `.env` (domyślnie `admin/`) — tylko redukcja szumu od botów skanujących `/admin/`, nie kontrola dostępu. `CookieConsentMiddleware` pomija tę ścieżkę zamiast na sztywno wpisanego `/admin/`
- Testy zabezpieczeń admina (`apps/users/tests/test_admin_security.py`): polityka haseł, `ADMIN_URL` i zachowanie blokady axes przez prawdziwy formularz logowania

### Changed
- Minimalna długość hasła podniesiona z 8 do 12 znaków (`MinimumLengthValidator`). Rejestracja przez API (`UserSerializer`) używa teraz tych samych `AUTH_PASSWORD_VALIDATORS` zamiast osobnego `min_length=8`. Istniejące hasła działają dalej — reguły obowiązują przy ustawianiu nowego hasła

### Fixed
- Blokada axes nie rozróżniała użytkowników: przy `USERNAME_FIELD = "email"` axes szukał loginu pod kluczem `email`, a formularz admina przekazuje go jako `username`, więc każda nieudana próba była zapisywana z `username = None`. W połączeniu z płaską listą `AXES_LOCKOUT_PARAMETERS` 5 złych prób z dowolnych adresów blokowało logowanie wszystkim, także właścicielowi. Dodano `AXES_USERNAME_FORM_FIELD = "username"` i zmieniono parametry na kombinację `[["username", "ip_address"]]` — blokowana jest tylko para login + IP, z której szły nieudane próby

## [0.4.0] - 2026-11-02
### Added
- Ochrona logowania do panelu admina przed brute-force (`django-axes`) — po 5 nieudanych próbach para użytkownik/IP jest blokowana na 1 godzinę. W ustawieniach testowych wyłączone (`AXES_ENABLED = False`)
- Dwuskładnikowe logowanie do panelu admina (`django-otp`) — `admin.site` działa jako `OTPAdminSite`, formularz logowania wymaga kodu TOTP z aplikacji uwierzytelniającej; jednorazowe kody zapasowe (`StaticDevice`) na wypadek utraty telefonu. Urządzenia zakłada się przez `manage.py shell` (instrukcja w README)
- `APP_VERSION` w `config/settings/base.py` czytane z `pyproject.toml` — jedno źródło numeru wersji dla Sentry (`release`) i schematu OpenAPI
- `make docker-check-deploy` — `manage.py check --deploy` w kontenerze

### Changed
- `make docker-migrate-check` rozbity na `docker-check-makemigrations`, `docker-check-migrate` i `docker-showmigrations`; `docker-migrate` nie wypisuje już `showmigrations`
- `make docker-shell` uruchamia `shell_plus`

### Removed
- Zmienna środowiskowa `APP_VERSION` (`.env`, `docker-compose.prod.yml`) — wersja pochodzi z `pyproject.toml`

### Fixed
- `make docker-test` nie budował obrazu — `docker-compose.test.yml` przekazywał `REQUIREMENTS: testing.txt`, przez co Dockerfile szukał nieistniejącego `testing.txt.lock`
- pytest zawieszał się przy zbieraniu testów w kontenerze (przeszukiwał cały katalog projektu przez bind mount) i pomijał pliki `tests.py` — dodano `testpaths = ["apps"]` i `tests.py` do `python_files`; uruchamia się 40 testów zamiast 7
- Zapis preferencji ciasteczek (`save_preferences`) kończył się błędem bazy na SQLite — `QuerySet.union()` z domyślnym `ORDER BY` zastąpiony jednym zapytaniem z `Q(...) | Q(...)`

## [0.3.1] - 2026-07-30
### Fixed
- Baner zgody na ciasteczka nie reagował na przyciski "Akceptuj wszystkie" / "Tylko niezbędne" przy pierwszej wizycie na świeżym środowisku (np. zaraz po `docker up`, przed zalogowaniem do panelu admina) — Django nie ustawiał jeszcze ciasteczka `csrftoken`, więc `cookies.js` wysyłał POST bez poprawnego tokenu i żądanie odrzucał `CsrfViewMiddleware`. Dodano `{% csrf_token %}` do `templates/cookies/banner.html`, żeby ciasteczko CSRF ustawiało się już przy pierwszym renderze dowolnej strony (baner jest częścią `base.html`)

## [0.3.0] - 2026-07-30
### Added
- `apps/blog`: początkowy szkielet aplikacji blogowej — widok `blog` renderujący placeholder `templates/blog/blog.html`, podpięty pod `/blog/` (dalszy rozwój w kolejnych commitach)
- `make docker-stop` / `make docker-start` — zatrzymywanie/wznawianie kontenerów bez ich usuwania (w odróżnieniu od `docker-down`/`docker-up`)

### Changed
- Zaktualizowano treść bio, listę umiejętności i sekcję projektów na stronie CV (`templates/cv/cv.html`)

## [0.2.0] - 2026-07-18
### Added
- `apps/cv`: static CV/homepage app — renders `templates/cv/cv.html` at the site root (`/`), replacing the placeholder `TemplateView`
- Bootstrap 5 + Bootstrap Icons (CDN) in `base.html` for CV page styling
- `apps/cookies`: cookie consent management — `CookieConsent` model, consent banner, preferences and policy pages, `CookieConsentMiddleware`, `setup_cookies` and `cleanup_consents` management commands, banner/preferences templates
- `apps/cookies/README.md` documenting the cookies app

### Fixed
- Missing template blocks in `base.html`
- Broken imports in cookies management commands
- Ruff formatting and per-file-ignores for settings star imports

## [0.1.1] - 2026-05-22
### Fixed
- Docker: nginx starts after `web` is healthy — eliminates "host not found in upstream" race condition (`docker-compose.prod.yml`, `docker-compose.local.yml`)

## [0.1.0] - 2026-05-22
### Added
- Initial project structure
- Custom User model (email as USERNAME_FIELD)
- Health check endpoints (/health/, /ready/, /live/)
- structlog JSON logging with per-request context (request_id, user_id, path)
- Production settings: HTTPS, HSTS, Sentry, Prometheus/Grafana
- Docker Compose for local and production environments
