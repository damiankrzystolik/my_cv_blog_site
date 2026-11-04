from types import SimpleNamespace

from apps.blog.rendering import render_markdown


def _image(url, caption=""):
    return SimpleNamespace(image=SimpleNamespace(url=url), caption=caption)


class TestRenderMarkdown:
    def test_renders_markdown(self):
        html = render_markdown("# Tytuł\n\nTekst **pogrubiony**.")
        assert "<h1>Tytuł</h1>" in html
        assert "<strong>pogrubiony</strong>" in html

    def test_strips_script_tags(self):
        html = render_markdown("Tekst <script>alert(1)</script>")
        assert "<script>" not in html

    def test_strips_event_handler_attributes(self):
        html = render_markdown('<img src="x.png" onerror="alert(1)">')
        assert "onerror" not in html

    def test_strips_javascript_links(self):
        html = render_markdown("[klik](javascript:alert(1))")
        assert "javascript:" not in html

    def test_highlights_fenced_code(self):
        html = render_markdown("```python\nprint('x')\n```")
        assert 'class="highlight"' in html

    def test_inserts_images_by_placeholder_order(self):
        images = [_image("/media/blog/a.png", "Pierwszy"), _image("/media/blog/b.png", "Drugi")]
        html = render_markdown("[[image2]]\n\n[[image1]]", images=images)
        assert html.index("/media/blog/b.png") < html.index("/media/blog/a.png")
        assert 'alt="Pierwszy"' in html

    def test_caption_cannot_break_out_of_alt_attribute(self):
        html = render_markdown("[[image1]]", images=[_image("/media/blog/a.png", '"><script>x</script>')])
        assert "<script>" not in html
        assert 'src="/media/blog/a.png"' in html
