from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from taggit.managers import TaggableManager

from apps.core.models import TimeStampedModel
from apps.core.validators import validate_file_extension, validate_file_size

from .rendering import render_markdown


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Post.Status.PUBLISHED, publish__lte=timezone.now())


class Post(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DF", "Szkic"
        PUBLISHED = "PB", "Opublikowany"

    title = models.CharField("tytuł", max_length=250)
    slug = models.SlugField(max_length=250, unique_for_date="publish")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="blog_posts")
    excerpt = models.CharField(
        "zajawka", max_length=300, blank=True, help_text="Krótki opis na liście postów i w meta description (SEO)."
    )
    body = models.TextField(
        "treść", help_text="Markdown. Obrazki z sekcji poniżej wstawiasz jako [[image1]], [[image2]]…"
    )
    publish = models.DateTimeField("data publikacji", default=timezone.now)
    status = models.CharField(max_length=2, choices=Status, default=Status.DRAFT)
    tags = TaggableManager(blank=True)

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        ordering = ["-publish"]
        indexes = [models.Index(fields=["-publish"])]
        verbose_name = "post"
        verbose_name_plural = "posty"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog:post_detail", args=[self.publish.year, self.publish.month, self.publish.day, self.slug])

    def rendered_body(self):
        return render_markdown(self.body, images=self.images.all())

    def featured_image(self):
        # Działa na prefetch_related("images") bez dodatkowych zapytań.
        images = list(self.images.all())
        return next((image for image in images if image.is_featured), images[0] if images else None)


class Comment(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    name = models.CharField("imię", max_length=80)
    email = models.EmailField("e-mail")
    body = models.TextField("komentarz", max_length=2000)
    active = models.BooleanField("widoczny", default=True)
    # HMAC adresu IP (nie sam adres) — wystarcza do limitu komentarzy, nie przechowuje IP wprost.
    ip_hash = models.CharField(max_length=64, blank=True, editable=False, db_index=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["created_at"])]
        verbose_name = "komentarz"
        verbose_name_plural = "komentarze"

    def __str__(self):
        return f"{self.name} — {self.post}"


class BlogImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        "obrazek", upload_to="blog/%Y/%m/", validators=[validate_file_extension, validate_file_size]
    )
    caption = models.CharField("podpis", max_length=255, blank=True)
    is_featured = models.BooleanField("wyróżniony", default=False, help_text="Obrazek na liście postów.")

    class Meta:
        ordering = ["id"]
        verbose_name = "obrazek"
        verbose_name_plural = "obrazki"

    def __str__(self):
        return self.caption or self.image.name

    def save(self, *args, **kwargs):
        if self.is_featured:
            BlogImage.objects.filter(post=self.post, is_featured=True).exclude(pk=self.pk).update(is_featured=False)
        super().save(*args, **kwargs)
