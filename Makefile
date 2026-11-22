.PHONY: install run migrate test test-fast lint lint-fix security shell ci lock \
        docker-build docker-up docker-down docker-stop docker-start docker-logs \
        docker-migrate docker-check-makemigrations docker-check-migrate \
        docker-showmigrations docker-collectstatic docker-createsuperuser \
        docker-shell docker-test docker-clean docker-check-deploy \
        prod-build prod-up prod-deploy prod-down prod-restart prod-logs \
        prod-migrate prod-collectstatic prod-createsuperuser prod-shell \
        prod-ssl-init prod-ssl-renew prod-cron-install prod-cron-remove \
        prod-backup prod-backup-cron-install prod-backup-cron-remove

# Wymagania lokalne: python 3.12+, uv (pip install uv), make
# Wymagania na serwerze: git, make, docker (z docker compose v2)
# Instalacja uv na serwerze: curl -LsSf https://astral.sh/uv/install.sh | sh

# ============================================================
# Development — lokalnie bez Dockera
# ============================================================

lock:
	uv pip compile requirements/base.txt --python-version 3.12 --python-platform linux --output-file requirements/base.lock --system-certs
	uv pip compile requirements/development.txt --python-version 3.12 --python-platform linux --output-file requirements/development.lock --system-certs
	uv pip compile requirements/testing.txt --python-version 3.12 --python-platform linux --output-file requirements/testing.lock --system-certs
	python -c "open('requirements/.prod_tmp','w').writelines(l for l in open('requirements/production.txt') if 'uwsgi' not in l.lower())"
	uv pip compile requirements/.prod_tmp --python-version 3.12 --python-platform linux --output-file requirements/production.lock --system-certs
	python -c "import os; os.unlink('requirements/.prod_tmp')"

install:
	uv pip install -r requirements/development.lock
	pre-commit install

run:
	python manage.py runserver

migrate:
	python manage.py makemigrations
	python manage.py migrate

test:
	pytest --cov=apps --cov-report=html -v

test-fast:
	pytest -x -q

lint:
	ruff check .
	ruff format --check .

lint-fix:
	ruff check . --fix
	ruff format .

security:
	bandit -r apps/ -ll
	pip-audit -r requirements/base.txt

shell:
	python manage.py shell_plus

ci: lint test security
	@echo "All CI checks passed!"

# ============================================================
# Docker — lokalny stack (db + web + nginx)
# ============================================================

docker-build:
	docker compose -f docker-compose.local.yml build

docker-up:
	docker compose -f docker-compose.local.yml up -d

docker-down:
	docker compose -f docker-compose.local.yml down

docker-stop:
	docker compose -f docker-compose.local.yml stop

docker-start:
	docker compose -f docker-compose.local.yml start

docker-logs:
	docker compose -f docker-compose.local.yml logs -f

docker-migrate:
	docker compose -f docker-compose.local.yml exec web python manage.py makemigrations
	docker compose -f docker-compose.local.yml exec web python manage.py migrate

docker-check-makemigrations:
	docker compose -f docker-compose.local.yml exec web python manage.py makemigrations --check --dry-run

docker-check-migrate:
	docker compose -f docker-compose.local.yml exec web python manage.py migrate --check

docker-showmigrations:
	docker compose -f docker-compose.local.yml exec web python manage.py showmigrations

docker-collectstatic:
	docker compose -f docker-compose.local.yml exec web python manage.py collectstatic --noinput

docker-createsuperuser:
	docker compose -f docker-compose.local.yml exec web python manage.py createsuperuser

docker-shell:
	docker compose -f docker-compose.local.yml exec web python manage.py shell_plus

docker-test:
	docker compose -f docker-compose.test.yml up --build --abort-on-container-exit

docker-clean:
	docker compose -f docker-compose.local.yml down -v --remove-orphans
	docker system prune -f

docker-check-deploy:
	docker compose -f docker-compose.local.yml exec web python manage.py check  --deploy
# ============================================================
# Produkcja — wdrożenie krok po kroku
#
# Pierwsze wdrożenie na serwerze:
#   1. git clone <repo> && cd <repo>
#   2. cp .env.example .env  →  nano .env          # uzupełnij wszystkie zmienne
#   3. make prod-build                              # zbuduj image (uv + lock files)
#   4. make prod-ssl-init DOMAIN=example.com EMAIL=admin@example.com
#                                                   # pierwszy certyfikat — przed startem nginx
#   5. make prod-up                                 # uruchom cały stack
#   6. make prod-migrate                            # wykonaj migracje bazy
#   7. make prod-collectstatic                      # skopiuj pliki statyczne
#   8. make prod-createsuperuser                    # utwórz konto admina
#   9. make prod-logs                               # sprawdź czy wszystko działa
#
# Każda kolejna aktualizacja:
#   git pull && make prod-deploy
# ============================================================

prod-build:
	docker compose -f docker-compose.prod.yml build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-deploy:
	docker compose -f docker-compose.prod.yml build web
	docker compose -f docker-compose.prod.yml up -d --no-deps web
	docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput
	docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
	@echo "Deployed!"

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-restart:
	docker compose -f docker-compose.prod.yml restart web

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

prod-migrate:
	docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput

prod-collectstatic:
	docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

prod-createsuperuser:
	docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

prod-shell:
	docker compose -f docker-compose.prod.yml exec web python manage.py shell

# Pierwszy certyfikat: certbot sam nasłuchuje na porcie 80, więc nginx nie może jeszcze działać
prod-ssl-init:
	docker compose -f docker-compose.prod.yml run --rm -p 80:80 certbot \
		certonly --standalone \
		-d $(DOMAIN) -d www.$(DOMAIN) --email $(EMAIL) --agree-tos --non-interactive

# --webroot jawnie: certbot renew użyłby zapisanej metody standalone, a port 80 zajmuje nginx
prod-ssl-renew:
	docker compose -f docker-compose.prod.yml run --rm certbot renew --webroot --webroot-path=/var/www/certbot --quiet
	docker compose -f docker-compose.prod.yml exec nginx nginx -s reload

prod-cron-install:
	(crontab -l 2>/dev/null; echo "0 3,15 * * * cd $(PWD) && make prod-ssl-renew >> /var/log/certbot-renew.log 2>&1") | crontab -
	@echo "Cron zainstalowany. Sprawdź: crontab -l"

prod-cron-remove:
	crontab -l 2>/dev/null | grep -v "$(PWD).*prod-ssl-renew" | crontab -
	@echo "Cron usunięty."

# Backup: zrzut bazy (pg_dump) + archiwum mediów (obrazki postów), rotacja po BACKUP_KEEP_DAYS.
# Najpierw zapis do pliku, potem gzip — w potoku `pg_dump | gzip` błąd pg_dump
# zginąłby (sh nie ma pipefail) i zostałby pusty, "udany" backup.
BACKUP_DIR ?= $(HOME)/backups/my_cv_blog_site
BACKUP_KEEP_DAYS ?= 14

prod-backup:
	@set -e; mkdir -p $(BACKUP_DIR); ts=$$(date +%Y%m%d_%H%M%S); \
	db=$(BACKUP_DIR)/db_$$ts.sql; media=$(BACKUP_DIR)/media_$$ts.tar.gz; \
	docker compose -f docker-compose.prod.yml exec -T db \
		sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" --no-owner' > $$db \
		|| { rm -f $$db; echo "pg_dump nie powiódł się"; exit 1; }; \
	gzip $$db; \
	docker compose -f docker-compose.prod.yml exec -T web tar czf - -C /app media > $$media \
		|| { rm -f $$media; echo "Archiwum mediów nie powiodło się"; exit 1; }; \
	find $(BACKUP_DIR) -name 'db_*.sql.gz' -mtime +$(BACKUP_KEEP_DAYS) -delete; \
	find $(BACKUP_DIR) -name 'media_*.tar.gz' -mtime +$(BACKUP_KEEP_DAYS) -delete; \
	echo "$$(date '+%F %T') backup OK: db_$$ts.sql.gz, media_$$ts.tar.gz"

# Codziennie 3:30 (po odnowieniu certyfikatu o 3:00); ponowne uruchomienie nie dubluje wpisu
prod-backup-cron-install:
	(crontab -l 2>/dev/null | grep -v "$(PWD).*prod-backup"; echo "30 3 * * * cd $(PWD) && make prod-backup >> /var/log/my_cv_blog_site-backup.log 2>&1") | crontab -
	@echo "Cron backupu zainstalowany. Sprawdź: crontab -l"

prod-backup-cron-remove:
	crontab -l 2>/dev/null | grep -v "$(PWD).*prod-backup" | crontab -
	@echo "Cron backupu usunięty."
