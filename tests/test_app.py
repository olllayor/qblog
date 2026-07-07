"""Route, auth, and SEO regression tests.

These run without a database: DB helpers degrade gracefully (empty lists /
zero counts), so pages must still render.
"""

import xml.dom.minidom

import app as app_module


class TestPublicRoutes:
    def test_index(self, client):
        assert client.get("/").status_code == 200

    def test_blog(self, client):
        assert client.get("/blog").status_code == 200

    def test_projects(self, client):
        assert client.get("/projects").status_code == 200

    def test_about(self, client):
        assert client.get("/about").status_code == 200

    def test_login_page(self, client):
        assert client.get("/login").status_code == 200

    def test_for_llms(self, client):
        assert client.get("/for-llms").status_code == 200

    def test_404(self, client):
        assert client.get("/definitely-not-a-page").status_code == 404


class TestSeoEndpoints:
    def test_robots_txt_is_generated(self, client):
        resp = client.get("/robots.txt")
        assert resp.status_code == 200
        body = resp.get_data(as_text=True)
        assert "Disallow: /admin/" in body
        assert "Sitemap:" in body

    def test_rss_is_wellformed_xml(self, client):
        resp = client.get("/rss")
        assert resp.status_code == 200
        xml.dom.minidom.parseString(resp.get_data())

    def test_rss_aliases(self, client):
        for path in ("/feed", "/rss.xml", "/feed.xml"):
            assert client.get(path).status_code == 200

    def test_sitemap(self, client):
        resp = client.get("/sitemap.xml")
        assert resp.status_code == 200
        xml.dom.minidom.parseString(resp.get_data())

    def test_single_person_schema_on_index(self, client):
        # Only one JSON-LD block may DECLARE the #person node (@type: Person);
        # other blocks may reference it by @id.
        import json
        import re

        body = client.get("/").get_data(as_text=True)
        blocks = re.findall(
            r'<script type="application/ld\+json">(.*?)</script>', body, re.S
        )
        declarations = 0
        for block in blocks:
            node = json.loads(block)
            if (
                node.get("@type") == "Person"
                and node.get("@id") == "https://ollayor.uz/#person"
            ):
                declarations += 1
        assert declarations == 1

    def test_twitter_handle(self, client):
        body = client.get("/").get_data(as_text=True)
        assert 'content="@olllayor"' in body
        assert 'content="@ollayor"' not in body

    def test_canonical_strips_query_string(self, client):
        body = client.get("/blog?q=test").get_data(as_text=True)
        assert 'rel="canonical" href="http://localhost/blog"' in body


class TestAuth:
    def test_check_admin_valid(self):
        assert app_module.check_admin("testadmin", "testpassword") is True

    def test_check_admin_wrong_password(self):
        assert app_module.check_admin("testadmin", "wrong") is False

    def test_check_admin_none_credentials_rejected(self):
        # Regression: unset env vars must never authenticate a None/None login.
        assert app_module.check_admin(None, None) is False

    def test_check_admin_empty_credentials_rejected(self):
        assert app_module.check_admin("", "") is False

    def test_check_admin_hashed_password(self, monkeypatch):
        from werkzeug.security import generate_password_hash

        monkeypatch.setattr(
            app_module, "ADMIN_PASSWORD_HASH", generate_password_hash("hunter2")
        )
        assert app_module.check_admin("testadmin", "hunter2") is True
        assert app_module.check_admin("testadmin", "wrong") is False

    def test_admin_requires_login(self, client):
        resp = client.get("/admin")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_login_open_redirect_blocked(self, client):
        resp = client.post(
            "/login",
            data={
                "username": "testadmin",
                "password": "testpassword",
                "next": "//evil.com",
            },
        )
        assert resp.status_code == 302
        assert "evil.com" not in resp.headers["Location"]

    def test_session_cookie_hardening(self, app):
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


class TestAdminPanel:
    def test_admin_homepage_requires_login(self, client):
        resp = client.get("/admin/homepage")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_project_toggles_require_login(self, client):
        for path in (
            "/admin/projects/1/toggle-visibility",
            "/admin/projects/1/toggle-featured",
            "/admin/projects/1/move/up",
        ):
            resp = client.post(path)
            assert resp.status_code == 302
            assert "/login" in resp.headers["Location"]

    def test_homepage_settings_defaults(self):
        from settings import HOMEPAGE_DEFAULTS, get_homepage_settings

        with app_module.app.app_context():
            settings = get_homepage_settings()
        # every default key present, regardless of DB state
        assert set(HOMEPAGE_DEFAULTS) <= set(settings)

    def test_index_renders_hero_from_settings(self, client):
        body = client.get("/").get_data(as_text=True)
        # default greeting shows until admin changes it (Jinja escapes the apostrophe)
        assert "hey! i&#39;m ollayor" in body

    def test_homepage_projects_fallback(self, monkeypatch):
        from projects import Project

        class FakeProject:
            def __init__(self, featured):
                self.is_featured = featured

        visible = [FakeProject(False), FakeProject(True), FakeProject(False)]
        monkeypatch.setattr(Project, "get_visible_projects", lambda: visible)
        assert Project.get_homepage_projects() == [visible[1]]

        none_featured = [FakeProject(False), FakeProject(False)]
        monkeypatch.setattr(Project, "get_visible_projects", lambda: none_featured)
        assert Project.get_homepage_projects() == none_featured


class TestPublishFlow:
    def test_publish_requires_login(self, client):
        resp = client.get("/publish")
        assert resp.status_code == 302

    def test_classic_editor_removed(self, client):
        assert client.get("/publish/classic").status_code == 404

    def test_unique_slug_dedupes(self, monkeypatch):
        from articles import Article

        existing = {"my-post", "my-post-2"}
        monkeypatch.setattr(
            Article, "get_by_slug", lambda slug: object() if slug in existing else None
        )
        assert app_module._unique_slug(None, "My Post") == "my-post-3"
        assert app_module._unique_slug("Custom Slug!", "ignored") == "custom-slug"
        assert app_module._unique_slug("", "") is None

    def test_new_publish_page_has_no_duplicate_slug_bug(self, auth_client):
        body = auth_client.get("/publish").get_data(as_text=True)
        # currentSlug starts null (tracked in JS) so auto-save updates, not re-creates
        assert "this.currentSlug = null" in body
        # editable slug form field removed (title is the single source of truth)
        assert 'name="slug"' not in body
        # always-available image insert exists (not only in the selection toolbar)
        assert 'id="imageBtn"' in body

    def test_autosave_reuses_slug_no_duplicate(self, auth_client, monkeypatch):
        """Second auto-save with the returned slug must UPDATE, not create a 2nd row.

        Regression test for a bug where the editor always sent slug=null, so
        every auto-save created a brand-new article instead of updating the
        first draft. Monkeypatched (no live DB required) to match this
        suite's DB-free approach — CI has no DATABASE_URL configured.
        """
        from articles import Article

        created = []
        updated = []

        class FakeArticle:
            def __init__(self, title, content, date_published, is_published, slug):
                self.slug = slug

        monkeypatch.setattr(Article, "get_by_slug", lambda slug: None)
        monkeypatch.setattr(
            Article, "save_article", lambda a: created.append(a.slug) or True
        )

        r1 = auth_client.post(
            "/api/auto-save",
            json={"title": "Regression Dup Check", "content": "<p>a</p>", "slug": None},
        ).get_json()
        assert r1["status"] == "success"
        slug = r1["slug"]
        assert len(created) == 1

        # Second call simulates the fixed JS: it sends back the slug it got
        # from the first response, so the route must take the update path.
        monkeypatch.setattr(
            Article, "get_by_slug", lambda s: FakeArticle("", "", None, False, s)
        )
        monkeypatch.setattr(
            Article, "update_article", lambda a: updated.append(a.slug) or True
        )
        r2 = auth_client.post(
            "/api/auto-save",
            json={"title": "Regression Dup Check", "content": "<p>b</p>", "slug": slug},
        ).get_json()
        assert r2["status"] == "success"
        assert r2["slug"] == slug

        # Exactly one create, one update — never a second create for the same story.
        assert len(created) == 1
        assert len(updated) == 1


class TestArticleAdminAndStats:
    def test_admin_articles_requires_login(self, client):
        resp = client.get("/admin/articles")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_device_classifier(self):
        from articles import _classify_device

        assert _classify_device("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)") == "Mobile"
        assert (
            _classify_device("Mozilla/5.0 (Android 13; SM-G991B) Mobile Safari")
            == "Mobile"
        )
        assert _classify_device("Mozilla/5.0 (iPad; CPU OS 17_0)") == "Tablet"
        assert (
            _classify_device("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") == "Desktop"
        )
        assert (
            _classify_device("Googlebot/2.1 (+http://www.google.com/bot.html)") == "Bot"
        )
        assert _classify_device("") == "Desktop"
        assert _classify_device(None) == "Desktop"

    def test_referrer_host_extraction(self, app):
        with app.test_request_context("/", base_url="http://localhost"):
            assert (
                app_module._referrer_host("https://www.google.com/search?q=x")
                == "google.com"
            )
            assert (
                app_module._referrer_host("https://news.ycombinator.com/")
                == "news.ycombinator.com"
            )
            assert app_module._referrer_host(None) is None
            # same-site referrer counts as direct
            assert app_module._referrer_host("http://localhost/blog") is None


class TestImageUpload:
    def test_upload_requires_login(self, client):
        resp = client.post("/admin/upload-image")
        assert resp.status_code == 302

    def test_serve_missing_image_404(self, client):
        assert client.get("/media/img/doesnotexist").status_code == 404

    def test_optimize_resizes_and_converts(self):
        import io

        from PIL import Image

        from images import MAX_WIDTH, optimize

        src = Image.new("RGB", (3000, 1500), (10, 20, 30))
        buf = io.BytesIO()
        src.save(buf, format="PNG")
        data, content_type = optimize(buf.getvalue())
        assert content_type == "image/webp"
        out = Image.open(io.BytesIO(data))
        assert out.width == MAX_WIDTH
        assert out.height == MAX_WIDTH // 2

    def test_optimize_rejects_garbage(self):
        import pytest

        from images import optimize

        with pytest.raises(ValueError):
            optimize(b"not an image")


class TestSitemapGenerators:
    def test_generate_sitemap_empty(self, app):
        from sitemap_generator import generate_sitemap

        with app.test_request_context("/"):
            pages = generate_sitemap(app, articles=[])
        assert len(pages) >= 5
        assert all("url" in p and "lastmod" in p for p in pages)

    def test_generate_image_sitemap_empty(self, app):
        from sitemap_generator import generate_image_sitemap

        with app.test_request_context("/"):
            images = generate_image_sitemap(app, articles=[])
        assert len(images) >= 2
