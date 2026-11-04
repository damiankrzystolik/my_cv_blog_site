import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.blog.models import BlogImage
from apps.blog.templatetags.blog_tags import polish_pluralize

from .factories import PostFactory

# Najmniejszy poprawny PNG 1x1 — przechodzi walidację python-magic.
PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6300010000000500010d0a2db40000000049454e44ae426082"
)


@pytest.mark.parametrize(
    ("count", "expected"),
    [(0, "komentarzy"), (1, "komentarz"), (2, "komentarze"), (4, "komentarze"), (5, "komentarzy"),
     (12, "komentarzy"), (14, "komentarzy"), (22, "komentarze"), (25, "komentarzy"), (112, "komentarzy")],
)  # fmt: skip
def test_polish_pluralize(count, expected):
    assert polish_pluralize(count, "komentarz,komentarze,komentarzy") == expected


@pytest.mark.django_db
class TestBlogImage:
    def _image(self, post, name, featured=False):
        return BlogImage.objects.create(
            post=post, image=SimpleUploadedFile(name, PNG_1X1, content_type="image/png"), is_featured=featured
        )

    def test_only_one_featured_image_per_post(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        post = PostFactory()
        first = self._image(post, "a.png", featured=True)
        second = self._image(post, "b.png", featured=True)

        first.refresh_from_db()
        assert not first.is_featured
        assert post.featured_image() == second

    def test_first_image_is_fallback_for_featured(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        post = PostFactory()
        first = self._image(post, "a.png")
        self._image(post, "b.png")

        assert post.featured_image() == first

    def test_upload_path_has_no_duplicated_media_prefix(self, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        image = self._image(PostFactory(), "a.png")

        assert image.image.name.startswith("blog/")
        assert image.image.url.startswith("/media/blog/")

    def test_rejects_file_that_is_not_an_image(self):
        image = BlogImage(post=PostFactory(), image=SimpleUploadedFile("evil.png", b"MZ\x90\x00 not a png"))
        with pytest.raises(Exception, match="typ pliku"):
            image.full_clean()
