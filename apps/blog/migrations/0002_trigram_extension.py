from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    # pg_trgm — TrigramSimilarity w wyszukiwarce (literówki w tytule).
    dependencies = [("blog", "0001_initial")]

    operations = [TrigramExtension()]
