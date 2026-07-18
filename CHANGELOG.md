# Changelog

## [Unreleased]

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
