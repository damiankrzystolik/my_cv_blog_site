import bleach
import markdown as md
from django.utils.safestring import mark_safe

# HTML, który może wyjść z Markdowna wpisu. Wszystko spoza listy (np. <script>, onerror=, javascript:)
# bleach usuwa — nawet jeśli trafi do treści przez wklejony surowy HTML.
ALLOWED_TAGS = {
    "p", "br", "hr", "h1", "h2", "h3", "h4", "h5", "h6",
    "strong", "em", "b", "i", "del", "blockquote",
    "ul", "ol", "li", "a", "img",
    "pre", "code", "span", "div",
    "table", "thead", "tbody", "tr", "th", "td",
}  # fmt: skip
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "img": ["src", "alt", "title"],
    "span": ["class"],  # klasy Pygments (kolorowanie składni)
    "div": ["class"],
    "code": ["class"],
    "th": ["align"],
    "td": ["align"],
}
ALLOWED_PROTOCOLS = {"http", "https", "mailto"}

MARKDOWN_EXTENSIONS = ["fenced_code", "codehilite", "tables"]
MARKDOWN_EXTENSION_CONFIGS = {"codehilite": {"css_class": "highlight", "guess_lang": False}}


def _escape_alt(text):
    # Podpis trafia do składni ![alt](url) — nawiasy kwadratowe zepsułyby link.
    return text.replace("[", "(").replace("]", ")")


def insert_images(body, images):
    """Zamienia [[image1]], [[image2]]... na obrazki w składni Markdown (w kolejności `images`)."""
    for number, image in enumerate(images, start=1):
        body = body.replace(f"[[image{number}]]", f"![{_escape_alt(image.caption)}]({image.image.url})")
    return body


def render_markdown(text, images=()):
    html = md.markdown(
        insert_images(text, images),
        extensions=MARKDOWN_EXTENSIONS,
        extension_configs=MARKDOWN_EXTENSION_CONFIGS,
    )
    clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, protocols=ALLOWED_PROTOCOLS)
    return mark_safe(clean)  # nosec B308 B703 — HTML przeszedł przez bleach.clean z listą dozwolonych tagów
