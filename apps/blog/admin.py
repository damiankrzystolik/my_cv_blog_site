from django.contrib import admin

from .models import BlogImage, Comment, Post


class BlogImageInline(admin.TabularInline):
    model = BlogImage
    extra = 1
    fields = ["image", "caption", "is_featured"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "author", "publish", "status"]
    list_filter = ["status", "created_at", "publish", "author"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ["title"]}
    raw_id_fields = ["author"]
    date_hierarchy = "publish"
    ordering = ["status", "-publish"]
    show_facets = admin.ShowFacets.ALWAYS
    inlines = [BlogImageInline]

    def get_changeform_initial_data(self, request):
        return {"author": request.user.pk, **super().get_changeform_initial_data(request)}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "post", "created_at", "active"]
    list_filter = ["active", "created_at"]
    list_editable = ["active"]
    search_fields = ["name", "email", "body"]
    readonly_fields = ["created_at", "updated_at"]
    actions = ["hide", "show"]

    @admin.action(description="Ukryj zaznaczone komentarze")
    def hide(self, request, queryset):
        queryset.update(active=False)

    @admin.action(description="Pokaż zaznaczone komentarze")
    def show(self, request, queryset):
        queryset.update(active=True)
