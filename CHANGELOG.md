# Changelog

## [Unreleased]

## [1.0.1] - 2026-05-22
### Fixed
- Docker: nginx starts after `web` is healthy — eliminates "host not found in upstream" race condition (`docker-compose.prod.yml`, `docker-compose.local.yml`)

## [1.0.0] - 2026-05-22
### Added
- Initial project structure
- Custom User model (email as USERNAME_FIELD)
- Health check endpoints (/health/, /ready/, /live/)
- structlog JSON logging with per-request context (request_id, user_id, path)
- Production settings: HTTPS, HSTS, Sentry, Prometheus/Grafana
- Docker Compose for local and production environments
