import factory
from django.utils import timezone

from apps.blog.models import Comment, Post
from apps.users.tests.factories import UserFactory


class PostFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Post
        skip_postgeneration_save = True

    title = factory.Sequence(lambda n: f"Wpis numer {n}")
    slug = factory.Sequence(lambda n: f"wpis-numer-{n}")
    author = factory.SubFactory(UserFactory)
    body = "Treść **wpisu** w Markdownie."
    status = Post.Status.PUBLISHED
    publish = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if create and extracted:
            self.tags.add(*extracted)


class CommentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Comment

    post = factory.SubFactory(PostFactory)
    name = "Czytelnik"
    email = "czytelnik@example.com"
    body = "Dobry wpis."
