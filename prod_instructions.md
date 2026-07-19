# WordPress (cknpozytywka) — przejście na produkcję

Kontekst: lokalnie (branch `feature/wordpress-container`) mamy już działający
WordPress w Dockerze pod `cknpozytywka.localhost`, z zaimportowaną prawdziwą
treścią strony cknpozytywka (dawniej hostowanej na home.pl) przez plugin
All-in-One WP Migration. Poniżej co trzeba zrobić, żeby przenieść to na
produkcyjny serwer (`docker-compose.prod.yml`), gdy będzie już znana docelowa
domena (stara `cknpozytywka.pl` wygasa, nowa jeszcze niekupiona).

## 1. Serwisy w `docker-compose.prod.yml`

Dodać te same dwa serwisy co w `docker-compose.local.yml` (`wordpress` +
`wordpress_db`, MariaDB), z poprawkami wypracowanymi lokalnie:

- Healthcheck `wordpress_db` **od razu** z `mariadb-admin` (nie
  `mysqladmin` — ta binarka nie istnieje w obrazie `mariadb:11`, lokalnie
  przez to healthcheck wisiał jako `unhealthy` i blokował start `wordpress`).
- `nginx: depends_on: wordpress`.
- Nowe volumeny `wordpress_data`, `wordpress_db_data` w sekcji `volumes:`.
- Nowe zmienne w `.env` produkcyjnym: `WORDPRESS_DB_NAME`,
  `WORDPRESS_DB_USER`, `WORDPRESS_DB_PASSWORD`, `WORDPRESS_DB_ROOT_PASSWORD`.

## 2. PHP ini i WP-CLI — trzeba to zakodować w obrazie, nie robić ręcznie w kontenerze

Ważna różnica względem tego jak robiliśmy lokalnie: zmiany wprowadzone
ręcznie przez `docker exec` (plik `.ini` w `/usr/local/etc/php/conf.d/`,
instalacja WP-CLI, `chown` na `wp-content`) **znikają**, jeśli kontener
zostanie kiedyś usunięty i odtworzony — bo żyją w warstwie zapisywalnej
kontenera, nie w volumenie. Na produkcji, żeby `docker compose up` na nowym
serwerze działał od razu poprawnie, potrzebny jest własny `Dockerfile`:

```dockerfile
FROM wordpress:php8.3-apache
COPY config/wordpress/uploads.ini /usr/local/etc/php/conf.d/zz-uploads.ini
```

z rozsądnymi wartościami (np. `upload_max_filesize = 64M`, `post_max_size =
64M`) — 768M było potrzebne tylko do jednorazowego importu backupu 525 MB,
na produkcji do zwykłego wgrywania zdjęć w bibliotece mediów wystarczy dużo
mniej.

WP-CLI nie musi być w obrazie na stałe — instaluje się doraźnie przez
`docker exec` gdy jest potrzebne (tak jak przy tej migracji), nie trzeba go
trzymać w `Dockerfile`.

## 3. Nie powtarzać całej migracji (FTP + phpMyAdmin + AI1WM) na produkcji

Skoro lokalnie już mamy poprawnie zaimportowaną, działającą kopię, najprościej
przenieść to co już działa, zamiast przechodzić przez cały proces migracji
jeszcze raz:

- `mysqldump` z lokalnego `wordpress_db` → import do produkcyjnego
  `wordpress_db`.
- Skopiowanie zawartości lokalnego volumenu `wordpress_data` (`wp-content` i
  reszta plików WP) na serwer produkcyjny, do analogicznego volumenu.

## 4. Nginx + SSL dla docelowej domeny

W `config/nginx/default.conf.template` dodać nowy `server` blok (redirect
80→443 + blok 443 z SSL) dla docelowej domeny, analogiczny do istniejącego
bloku dla Django, ale z `proxy_pass http://wordpress:80` zamiast
`uwsgi_pass web:8000`. Certyfikat SSL trzeba wygenerować osobno przez
certbot dla tej nowej domeny:

```
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d <domena> -d www.<domena>
```

## 5. Podmiana adresu URL na docelową domenę

Po przeniesieniu danych na produkcję, adres strony trzeba zamienić z
`http://cknpozytywka.localhost` na docelowy adres produkcyjny (np.
`https://nowa-domena.com`) — przez WP-CLI, które bezpiecznie obsługuje też
dane serializowane (tak jak robił to automatycznie AI1WM przy imporcie
lokalnie):

```
wp search-replace 'http://cknpozytywka.localhost' 'https://nowa-domena.com' --all-tables --allow-root
```

## 6. Kolejność na końcu

Dopiero gdy wszystko powyżej działa i jest przetestowane, przełączyć DNS
(rekord A nowej domeny na IP serwera produkcyjnego) — na samym końcu, żeby
zminimalizować przestój.

## Do ustalenia, zanim zaczniemy ten etap

- Docelowa domena (stara `cknpozytywka.pl` wygasa, nowa jeszcze niekupiona).
- Czy produkcyjny serwer to ta sama maszyna co Django, czy osobna.
