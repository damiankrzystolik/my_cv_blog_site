from django.contrib import admin
from django.utils.html import format_html

from .models import Cookie, CookieConsent, CookieConsentLog, CookieGroup


@admin.register(CookieGroup)
class CookieGroupAdmin(admin.ModelAdmin):
    list_display = ["display_name", "name", "is_required", "is_active", "cookie_count"]
    list_filter = ["is_required", "is_active"]
    search_fields = ["name", "display_name"]

    def cookie_count(self, obj):
        return obj.cookie_set.count()

    cookie_count.short_description = "Liczba ciasteczek"


@admin.register(Cookie)
class CookieAdmin(admin.ModelAdmin):
    list_display = ["name", "group", "provider", "expiry", "is_active"]
    list_filter = ["group", "is_active", "provider"]
    search_fields = ["name", "purpose"]


@admin.register(CookieConsent)
class CookieConsentAdmin(admin.ModelAdmin):
    list_display = [
        "consent_id_short",
        "user",
        "consent_status",
        "accepted_groups_list",
        "consent_given_at",
        "expires_at",
        "is_expired_status",
    ]
    list_filter = ["is_valid", "consent_given_at", "expires_at", "accepted_groups"]
    search_fields = ["consent_id", "user__username", "user__email", "ip_address"]
    readonly_fields = ["consent_id", "ip_address", "user_agent", "consent_given_at"]

    def consent_id_short(self, obj):
        return f"{str(obj.consent_id)[:8]}..."

    consent_id_short.short_description = "ID zgody"

    def consent_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Wygasła</span>')
        elif obj.is_valid:
            return format_html('<span style="color: green;">Aktywna</span>')
        return format_html('<span style="color: orange;">Nieważna</span>')

    consent_status.short_description = "Status"

    def accepted_groups_list(self, obj):
        return ", ".join(g.display_name for g in obj.accepted_groups.all())

    accepted_groups_list.short_description = "Zaakceptowane grupy"

    def is_expired_status(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Tak</span>')
        return format_html('<span style="color: green;">Nie</span>')

    is_expired_status.short_description = "Wygasła"


@admin.register(CookieConsentLog)
class CookieConsentLogAdmin(admin.ModelAdmin):
    list_display = ["consent_short", "action", "timestamp"]
    list_filter = ["action", "timestamp"]
    readonly_fields = ["consent", "action", "groups_before", "groups_after", "timestamp"]

    def consent_short(self, obj):
        return f"{str(obj.consent.consent_id)[:8]}..."

    consent_short.short_description = "Zgoda"
