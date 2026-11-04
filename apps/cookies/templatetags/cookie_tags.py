from django import template

register = template.Library()


@register.inclusion_tag("cookies/includes/group_script.html", takes_context=True)
def group_script(context, group_name, script_content):
    """Ładuje skrypt (np. Google Analytics, piksel marketingowy) tylko gdy
    użytkownik wyraził zgodę na daną grupę cookies.

    Zastępuje dawne analytics_script/marketing_script jedną generyczną
    funkcją - reużywalną dla dowolnej grupy, nie tylko dwóch zahardkodowanych
    (PLAN.md C8/F1).

    Użycie w szablonie:
        {% load cookie_tags %}
        {% group_script "analytics" google_analytics_snippet %}
    """
    request = context["request"]
    accepted_groups = getattr(request, "cookie_consent_groups", set())
    return {"has_consent": group_name in accepted_groups, "script_content": script_content}


@register.inclusion_tag("cookies/banner.html", takes_context=True)
def cookie_consent_banner(context):
    """Renderuje baner zgody jako partial - wstaw raz w base.html, tuż przed
    </body>: {% load cookie_tags %}{% cookie_consent_banner %} (PLAN.md D1-D3, D5).

    Wcześniejsza wersja zwracała mark_safe() z zahardkodowanym HTML/CSS/JS
    inline, co łamie restrykcyjne CSP i nie da się tego przetłumaczyć (i18n).
    """
    request = context["request"]
    show_banner = not getattr(request, "has_cookie_consent", False)
    return {"show_banner": show_banner, "request": request}
