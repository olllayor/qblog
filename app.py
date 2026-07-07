import hmac
import logging
import os
import threading
import time
from datetime import UTC, datetime
from functools import wraps
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from xml.sax.saxutils import escape as xml_escape

import redis
import sentry_sdk
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_caching import Cache
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_wtf.csrf import CSRFProtect
from posthog import Posthog
from werkzeug.security import check_password_hash

from articles import Article
from database import close_db, get_database_url, init_db
from images import ImageStore
from projects import Project
from search import get_search_service
from settings import HOMEPAGE_DEFAULTS, get_homepage_settings, save_homepage_settings

load_dotenv()

# Configure logging early so we can see startup messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY")
POSTHOG_HOST = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")
posthog = None
if POSTHOG_API_KEY:
    posthog = Posthog(project_api_key=POSTHOG_API_KEY, host=POSTHOG_HOST)
else:
    logger.info("POSTHOG_API_KEY not set. PostHog analytics disabled.")

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Add data like request headers and IP for users,
        # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
        send_default_pii=True,
    )
else:
    logger.info("SENTRY_DSN not set. Sentry error tracking disabled.")

app = Flask(__name__)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


@app.context_processor
def inject_globals():
    return {"now_year": datetime.now(UTC).year}


TWITTER_IMAGE_HOSTS = {"pbs.twimg.com"}


@app.template_filter("image_thumb")
def image_thumb(url, size="thumb"):
    """Request a smaller rendition for known CDN hosts (currently just Twitter's
    `name=` sizing param); other hosts are returned unchanged since we don't
    control their resizing API."""
    if not url:
        return url
    parsed = urlparse(url)
    if parsed.netloc not in TWITTER_IMAGE_HOSTS:
        return url
    query = parse_qs(parsed.query)
    query["name"] = [size]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


# Simple User class for Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id


@login_manager.user_loader
def load_user(user_id):
    if user_id == ADMIN_USERNAME:
        return User(user_id)
    return None


BLOG_ARTICLES_PER_PAGE = 6


# Configure caching with fallback
def setup_cache():
    # Disable cache in development environment
    if os.getenv("FLASK_ENV") == "development" or os.getenv("FLASK_DEBUG") == "1":
        logger.info("Development mode detected. Caching disabled (NullCache).")
        app.config["CACHE_TYPE"] = "NullCache"
        return Cache(app)

    redis_url = os.getenv("REDIS_URL")

    # Try to use Redis if available
    if redis_url:
        try:
            # Test Redis connection
            redis_client = redis.from_url(redis_url)
            redis_client.ping()

            app.config["CACHE_TYPE"] = "RedisCache"
            app.config["CACHE_REDIS_URL"] = redis_url
            app.config["CACHE_DEFAULT_TIMEOUT"] = 300
            logger.info("Using Redis cache")

        except redis.RedisError as e:
            logger.warning(f"Redis connection failed: {e}. Falling back to SimpleCache")
            app.config["CACHE_TYPE"] = "SimpleCache"
            app.config["CACHE_DEFAULT_TIMEOUT"] = 300
    else:
        logger.info("No Redis URL provided. Using SimpleCache")
        app.config["CACHE_TYPE"] = "SimpleCache"
        app.config["CACHE_DEFAULT_TIMEOUT"] = 360

    return Cache(app)


# Initialize cache with error handling
cache = setup_cache()


# Cache decorator with error handling
def safe_cached(timeout=360, **kwargs):
    def decorator(f):
        # Build the cached view once at decoration time, not per request.
        cached_func = cache.cached(timeout=timeout, **kwargs)(f)

        @wraps(f)
        def wrapper(*args, **kwargs_inner):
            try:
                return cached_func(*args, **kwargs_inner)
            except (redis.ConnectionError, redis.TimeoutError) as e:
                logger.warning(
                    f"Cache error for {f.__name__}: {e}. Executing function without cache."
                )
                # Execute function without cache if Redis fails
                return f(*args, **kwargs_inner)

        return wrapper

    return decorator


# Cache key management functions
def get_cache_key(view_name, **kwargs):
    """Generate cache key for a given view function that matches Flask-Caching's format"""
    # Flask-Caching uses 'view//' + endpoint format for @cache.cached
    if kwargs:
        # For parameterized routes like article(slug='test')
        params = "&".join([f"{k}={v}" for k, v in sorted(kwargs.items())])
        return f"view//{view_name}?{params}"
    return f"view//{view_name}"


def invalidate_view_cache(view_name, **kwargs):
    """Safely invalidate cache for a specific view"""
    try:
        cache_key = get_cache_key(view_name, **kwargs)
        cache.delete(cache_key)
        logger.info(f"Cache invalidated for {view_name} with key: {cache_key}")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache for {view_name}: {e}")


def invalidate_multiple_caches(*view_specs):
    """Invalidate multiple view caches"""
    for view_spec in view_specs:
        if isinstance(view_spec, str):
            invalidate_view_cache(view_spec)
        elif isinstance(view_spec, tuple):
            view_name, kwargs = view_spec
            invalidate_view_cache(view_name, **kwargs)
        else:
            logger.warning(f"Invalid view spec: {view_spec}")


app.secret_key = os.getenv("FLASK_SECRET_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
# Prefer a hashed password; fall back to plaintext for backward compatibility.
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

_IS_DEV = os.getenv("FLASK_ENV") == "development" or os.getenv("FLASK_DEBUG") == "1"

# Fail fast in production when required secrets are missing, rather than booting
# with secret_key=None (insecure sessions) or an unauthenticatable admin.
_missing = [
    name
    for name, val in (
        ("FLASK_SECRET_KEY", app.secret_key),
        ("ADMIN_USERNAME", ADMIN_USERNAME),
        ("ADMIN_PASSWORD/ADMIN_PASSWORD_HASH", ADMIN_PASSWORD or ADMIN_PASSWORD_HASH),
    )
    if not val
]
if _missing:
    msg = f"Required secrets not set in environment: {', '.join(_missing)}"
    if _IS_DEV:
        logger.error(msg)
    else:
        raise RuntimeError(msg)

# Harden the session cookie for production HTTPS.
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=not _IS_DEV,
)

_db_init_lock = threading.Lock()
_db_initialized = False


@app.before_request
def _ensure_db_initialized():
    # Defer schema init off the import path (Vercel cold starts) and run it at
    # most once per process, on the first request that actually needs the DB.
    global _db_initialized
    if _db_initialized:
        return
    with _db_init_lock:
        if _db_initialized:
            return
        try:
            if not init_db():
                logger.error("Error initializing database during first request")
        except Exception as e:
            logger.error(f"Exception during db initialization: {e}")
        _db_initialized = True


@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)


def check_admin(username, password):
    # Reject empty/None credentials outright so unset env vars can never match.
    if not username or not password or not ADMIN_USERNAME:
        return False
    user_ok = hmac.compare_digest(username, ADMIN_USERNAME)
    if ADMIN_PASSWORD_HASH:
        pass_ok = check_password_hash(ADMIN_PASSWORD_HASH, password)
    elif ADMIN_PASSWORD:
        pass_ok = hmac.compare_digest(password, ADMIN_PASSWORD)
    else:
        pass_ok = False
    return user_ok and pass_ok


def get_blog_articles(page: int, per_page: int, query: str):
    clean_query = (query or "").strip()
    if not clean_query:
        articles, total_articles = Article.get_published_articles_paginated(
            page=page, per_page=per_page
        )
        return articles, total_articles, False

    search_service = get_search_service()
    search_result = search_service.search_published_slugs(
        query=clean_query, page=page, per_page=per_page
    )

    if search_result.degraded:
        articles, total_articles = Article.get_published_articles_paginated(
            page=page, per_page=per_page
        )
        return articles, total_articles, True

    articles = Article.get_published_articles_by_slugs(search_result.slugs)
    return articles, search_result.total, False


@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in and next specified, go there
    if current_user.is_authenticated:
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if check_admin(username, password):
            user = User(username)
            login_user(user)
            flash("You were just logged in!", "success")

            # Redirect back to the original destination if provided and safe
            next_url = request.form.get("next") or request.args.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Wrong credentials!", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You were just logged out!", "info")
    return redirect(url_for("login"))


@app.route("/")
@safe_cached(timeout=300)
def index():
    settings = get_homepage_settings()

    projects = []
    if settings.get("show_projects", True):
        try:
            projects = Project.get_homepage_projects()
        except Exception as e:
            logger.warning(f"Failed to load projects: {e}")

    all_time_readers = 0
    if settings.get("show_readers_badge", True):
        try:
            view_totals = Article.get_view_totals()
            all_time_readers = view_totals.get(
                "all_time", view_totals.get("monthly", 0)
            )
        except Exception as e:
            logger.warning(f"Failed to load view totals: {e}")

    return render_template(
        "index.html",
        projects=projects,
        all_time_readers=all_time_readers,
        hp=settings,
    )


@app.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="favicon.ico"))


@app.route("/rss")
@app.route("/feed")
@app.route("/rss.xml")
@app.route("/feed.xml")
@safe_cached(timeout=600)
def rss_feed():
    """Generate RSS feed for blog articles"""
    articles = Article.get_published_articles()[:20]  # Latest 20 articles

    # Build RSS XML
    rss_items = []
    for article in articles:
        pub_date = article.date_published.strftime("%a, %d %b %Y %H:%M:%S GMT")
        description = article.get_summary(300)
        title = xml_escape(article.title or "")
        slug = xml_escape(article.slug or "")
        # A CDATA block cannot contain the sequence "]]>"; split it if present.
        safe_description = (description or "").replace("]]>", "]]]]><![CDATA[>")

        rss_items.append(f"""
        <item>
            <title>{title}</title>
            <link>https://ollayor.uz/blog/{slug}</link>
            <guid isPermaLink="true">https://ollayor.uz/blog/{slug}</guid>
            <pubDate>{pub_date}</pubDate>
            <description><![CDATA[{safe_description}]]></description>
            <author>contact@ollayor.uz (Ollayor Maxammadnabiyev)</author>
        </item>""")

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>Ollayor Maxammadnabiyev - Blog</title>
        <link>https://ollayor.uz/blog</link>
        <description>Software engineering, web development, and technology articles by Ollayor Maxammadnabiyev</description>
        <language>en-us</language>
        <lastBuildDate>{datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")}</lastBuildDate>
        <atom:link href="https://ollayor.uz/rss.xml" rel="self" type="application/rss+xml" />
        <webMaster>contact@ollayor.uz (Ollayor Maxammadnabiyev)</webMaster>
        <managingEditor>contact@ollayor.uz (Ollayor Maxammadnabiyev)</managingEditor>
        <image>
            <url>https://ollayor.uz/static/myself-social-optimized.jpg</url>
            <title>Ollayor Maxammadnabiyev</title>
            <link>https://ollayor.uz</link>
        </image>
        {"".join(rss_items)}
    </channel>
</rss>"""

    return Response(rss_xml, mimetype="application/rss+xml")


@app.route("/projects")
@safe_cached(timeout=180)
def projects():
    visible_projects = Project.get_visible_projects()
    return render_template("projects.html", projects=visible_projects)


@app.route("/blog")
@safe_cached(timeout=180, query_string=True)
def blog():
    start = time.time()
    per_page = BLOG_ARTICLES_PER_PAGE
    query = (request.args.get("q") or "").strip()
    articles, total_articles, search_degraded = get_blog_articles(
        page=1, per_page=per_page, query=query
    )
    duration = time.time() - start
    logger.info(f"/blog route executed in {duration:.3f} seconds")
    has_more = per_page < total_articles
    return render_template(
        "blog.html",
        articles=articles,
        per_page=per_page,
        total_articles=total_articles,
        has_more=has_more,
        query=query,
        search_degraded=search_degraded,
    )


@app.route("/api/articles")
def api_articles():
    try:
        page = int(request.args.get("page", 1))
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = int(request.args.get("per_page", BLOG_ARTICLES_PER_PAGE))
    except (TypeError, ValueError):
        per_page = BLOG_ARTICLES_PER_PAGE

    per_page = max(1, min(per_page, 24))
    query = (request.args.get("q") or "").strip()

    articles, total_articles, search_degraded = get_blog_articles(
        page=page, per_page=per_page, query=query
    )

    has_more = page * per_page < total_articles

    article_payload = []
    for article in articles:
        formatted_date = (
            article.date_published.strftime("%d %B, %Y")
            if article.date_published
            else ""
        )
        article_payload.append(
            {
                "slug": article.slug,
                "title": article.title,
                "summary": article.get_summary(200),
                "published_on": formatted_date,
                "reading_time": article.get_reading_time(),
            }
        )

    return jsonify(
        {
            "articles": article_payload,
            "has_more": has_more,
            "total": total_articles,
            "query": query,
            "search_degraded": search_degraded,
        }
    )


@app.route("/media/ollayor-cv.pdf")
def cv_redirect():
    return redirect(url_for("static", filename="media/Olloyor_s_resume.pdf"))


@app.route("/blog/<slug>")
def article(slug: str):
    # Always track the view (not cached) - this should always run
    ip_address = request.environ.get(
        "HTTP_X_FORWARDED_FOR", request.environ.get("REMOTE_ADDR", "unknown")
    )
    user_agent = request.environ.get("HTTP_USER_AGENT", "")
    referrer_host = _referrer_host(request.referrer)
    Article.track_view(slug, ip_address, user_agent, referrer_host)

    # Get article with caching (article content rarely changes)
    cache_key = f"article_content_{slug}"
    article = cache.get(cache_key)

    if article is None:
        article = Article.get_by_slug(slug)
        if article:
            # Cache article for 10 minutes (content doesn't change often)
            cache.set(cache_key, article, timeout=600)

    if not article:
        return render_template("404.html"), 404

    # Check if article is published (unless user is logged in as admin)
    if not article.is_published and not current_user.is_authenticated:
        return render_template("404.html"), 404

    # Get current view count (real-time, not cached) - this should always be fresh
    view_count = Article.get_view_count(slug)

    # Extract first image for social media sharing
    first_image = article.get_first_image(request.url_root.rstrip("/"))

    return render_template(
        "article.html", article=article, view_count=view_count, first_image=first_image
    )


@app.route("/talks")
def talks():
    return render_template("talks.html")


@app.route("/about")
@safe_cached(timeout=600)
def about():
    return render_template("about.html")


@app.route("/for-llms")
@safe_cached(timeout=600)
def for_llms():
    return render_template("for_llms.html")


@app.route("/matrix")
def matrix():
    return render_template("matrix.html")


def _referrer_host(referrer):
    """Extract a bare host from a referrer URL; None for direct/self visits."""
    if not referrer:
        return None
    try:
        parsed = urlparse(referrer)
        host = (parsed.hostname or "").lower()
        if not host or host == request.host.split(":")[0]:
            return None  # direct or same-site navigation
        return host[4:] if host.startswith("www.") else host
    except (ValueError, AttributeError):
        return None


def _unique_slug(desired_slug, title):
    """Slugify and dedupe against existing articles."""
    from slugify import slugify

    base = slugify(desired_slug or "") or slugify(title or "")
    if not base:
        return None
    candidate = base
    suffix = 2
    while Article.get_by_slug(candidate) is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


@app.route("/publish", methods=["GET", "POST"])
@login_required
def publish():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        is_published = request.form.get("is_published") == "on"
        date_published = datetime.now(UTC)
        if not title or not content:
            flash("Title or content is missing", "error")
            return redirect(url_for("publish"))

        slug = _unique_slug(request.form.get("slug"), title)
        if not slug:
            flash("Could not derive a URL slug from the title.", "error")
            return redirect(url_for("publish"))

        new_article = Article(
            title, content, date_published, is_published=is_published, slug=slug
        )
        if not Article.save_article(new_article):
            flash("Error saving article — nothing was published.", "error")
            return redirect(url_for("publish"))

        # remove the article from cache
        try:
            invalidate_multiple_caches("blog", ("article", {"slug": new_article.slug}))
            # Also clear the article content cache for new articles
            cache.delete(f"article_content_{new_article.slug}")
            logger.info(
                f"Blog and article caches invalidated after publishing new article: {new_article.slug}"
            )
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")

        if is_published:
            flash("Article published successfully!", "success")
            return redirect(url_for("article", slug=new_article.slug))
        else:
            flash("Article saved as draft. You can publish it later.", "info")
            return redirect(url_for("edit_article", slug=new_article.slug))

    return render_template("publish_modern.html")


@app.route("/blog/<slug>/edit", methods=["GET", "POST"])
@login_required
def edit_article(slug):
    article = Article.get_by_slug(slug)
    if not article:
        return render_template("404.html"), 404
    if request.method == "POST":
        old_published_status = article.is_published
        title = (request.form.get("title") or "").strip()
        content = (request.form.get("content") or "").strip()
        if not title or not content:
            flash("Title or content is missing", "error")
            return render_template("publish_modern.html", article=article)
        article.title = title
        article.content = content
        article.is_published = request.form.get("is_published") == "on"

        if Article.update_article(article):
            # Provide appropriate flash message based on publish status
            if article.is_published and not old_published_status:
                flash("Article updated and published successfully!", "success")
            elif not article.is_published and old_published_status:
                flash("Article updated and moved to drafts.", "info")
            elif article.is_published:
                flash("Published article updated successfully!", "success")
            else:
                flash("Draft article updated successfully.", "info")

            try:
                # Invalidate both blog list and specific article caches
                invalidate_multiple_caches("blog", ("article", {"slug": article.slug}))
                # Also clear the article content cache
                cache.delete(f"article_content_{article.slug}")
                logger.info(
                    f"Blog and article caches invalidated after updating article: {article.slug}"
                )
            except Exception as e:
                logger.warning(f"Cache invalidation failed: {e}")
            return redirect(url_for("article", slug=article.slug))
        else:
            flash("Error updating article", "error")

    return render_template("publish_modern.html", article=article)


@app.route("/blog/<slug>/delete", methods=["DELETE", "POST"])
@login_required
def delete_article(slug):
    logger.info(f"Attempting to delete article with slug: {slug}")

    success = Article.delete_article_by_slug(slug)
    if success:
        flash("Article deleted successfully.", "success")

        try:
            invalidate_multiple_caches("blog", ("article", {"slug": slug}))
            # Also clear the article content cache
            cache.delete(f"article_content_{slug}")
            logger.info(
                f"Blog and article caches invalidated after deleting article: {slug}"
            )
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
    else:
        logger.error("Error deleting article from the database.")
        flash("Error deleting article from the database.", "error")

    return redirect(url_for("blog"))


@app.route("/admin")
@login_required
def admin_dashboard():
    # Aggregate basic stats via COUNT queries — avoid loading article bodies
    try:
        articles_count, published_count = Article.get_article_counts()
    except Exception as e:
        logger.warning("Failed to fetch article counts: %s", e)
        articles_count, published_count = 0, 0
    drafts_count = articles_count - published_count

    try:
        projects_count = len(Project.get_all_projects())
    except Exception as e:
        logger.warning("Failed to fetch projects count: %s", e)
        projects_count = 0

    view_totals = {"daily": 0, "monthly": 0}
    try:
        view_totals = Article.get_view_totals()
    except Exception as exc:
        logger.warning("Failed to fetch view totals: %s", exc)

    try:
        recent_articles = Article.get_recent_articles(5)
    except Exception as e:
        logger.warning("Failed to fetch recent articles: %s", e)
        recent_articles = []

    try:
        views_by_day = Article.get_views_by_day(30)
    except Exception as e:
        logger.warning("Failed to fetch daily views: %s", e)
        views_by_day = []
    max_daily_views = max((d["views"] for d in views_by_day), default=0)

    try:
        top_articles = Article.get_top_articles_by_views(5)
    except Exception as e:
        logger.warning("Failed to fetch top articles: %s", e)
        top_articles = []

    try:
        device_breakdown = Article.get_device_breakdown(30)
    except Exception as e:
        logger.warning("Failed to fetch device breakdown: %s", e)
        device_breakdown = []
    device_total = sum(d["count"] for d in device_breakdown)

    try:
        top_referrers = Article.get_top_referrers(30)
    except Exception as e:
        logger.warning("Failed to fetch referrers: %s", e)
        top_referrers = []

    return render_template(
        "admin_dashboard.html",
        articles_count=articles_count,
        published_count=published_count,
        drafts_count=drafts_count,
        projects_count=projects_count,
        daily_views=view_totals.get("daily", 0),
        monthly_views=view_totals.get("monthly", 0),
        recent_articles=recent_articles,
        views_by_day=views_by_day,
        max_daily_views=max_daily_views,
        top_articles=top_articles,
        device_breakdown=device_breakdown,
        device_total=device_total,
        top_referrers=top_referrers,
    )


@app.route("/admin/articles")
@login_required
def admin_articles():
    status = request.args.get("status", "all")
    if status not in ("all", "published", "draft"):
        status = "all"
    query = (request.args.get("q") or "").strip() or None
    articles = Article.get_articles_admin(status=status, query=query)
    return render_template(
        "admin_articles.html", articles=articles, status=status, query=query or ""
    )


@app.route("/admin/upload-image", methods=["POST"])
@login_required
def upload_image():
    file = request.files.get("image")
    if file is None or not file.filename:
        return jsonify({"status": "error", "message": "No image provided"}), 400
    try:
        image_id = ImageStore.save(
            file.read(),
            filename=file.filename,
            content_type=file.mimetype,
        )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    if not image_id:
        return jsonify({"status": "error", "message": "Failed to store image"}), 500
    return jsonify(
        {"status": "success", "url": url_for("serve_image", image_id=image_id)}
    )


@app.route("/media/img/<image_id>")
def serve_image(image_id):
    result = ImageStore.get(image_id)
    if result is None:
        return "Not found", 404
    data, content_type = result
    response = app.response_class(data, mimetype=content_type)
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@app.route("/admin/projects")
@login_required
def admin_projects():
    all_projects = Project.get_all_projects()
    return render_template("admin_projects.html", projects=all_projects)


@app.route("/admin/db-info")
@login_required
def admin_db_info():
    # Summarize which DB is currently configured and show counts
    url, source = get_database_url()
    # Safe summary for template
    from urllib.parse import urlparse

    parsed = urlparse(url) if url else None
    db_summary = {
        "host": parsed.hostname if parsed else None,
        "db": (parsed.path.lstrip("/") if parsed and parsed.path else None),
        "user": parsed.username if parsed else None,
        "scheme": parsed.scheme if parsed else None,
        "source": source,
    }

    articles_count, _ = Article.get_article_counts()
    projects_count = len(Project.get_all_projects())

    return render_template(
        "admin_db_info.html",
        db_summary=db_summary,
        articles_count=articles_count,
        projects_count=projects_count,
    )


@app.route("/admin/projects/add", methods=["GET", "POST"])
@login_required
def add_project():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        image_url = request.form.get("image_url")
        technologies = request.form.get("technologies")  # Comma-separated string
        github_link = request.form.get("github_link")
        live_demo_link = request.form.get("live_demo_link")

        if not title or not description:
            flash("Title and description are required.", "error")
            return render_template("add_edit_project.html", project=request.form)

        # Convert comma-separated string to list for storage, or handle as string if preferred
        tech_list = (
            [tech.strip() for tech in technologies.split(",")] if technologies else []
        )

        new_project = Project(
            title=title,
            description=description,
            image_url=image_url,
            technologies=tech_list,  # Pass as list
            github_link=github_link,
            live_demo_link=live_demo_link,
        )
        if Project.save_project(new_project):
            flash("Project added successfully!", "success")

            try:
                # Invalidate cache for projects pages
                invalidate_multiple_caches("projects", "index")
                logger.info("Project caches invalidated after adding new project")
            except Exception as e:
                logger.warning(f"Cache invalidation failed: {e}")
            return redirect(url_for("admin_projects"))
        else:
            flash("Error adding project.", "error")
    return render_template("add_edit_project.html")


@app.route("/admin/projects/edit/<int:project_id>", methods=["GET", "POST"])
@login_required
def edit_project(project_id):
    project_to_edit = Project.get_project_by_id(project_id)
    if not project_to_edit:
        flash("Project not found.", "error")
        return redirect(url_for("admin_projects"))

    if request.method == "POST":
        project_to_edit.title = request.form.get("title")
        project_to_edit.description = request.form.get("description")
        project_to_edit.image_url = request.form.get("image_url")
        technologies = request.form.get("technologies")
        project_to_edit.technologies = (
            [tech.strip() for tech in technologies.split(",")] if technologies else []
        )
        project_to_edit.github_link = request.form.get("github_link")
        project_to_edit.live_demo_link = request.form.get("live_demo_link")

        if not project_to_edit.title or not project_to_edit.description:
            flash("Title and description are required.", "error")
            # Pass technologies back as a string for the form
            project_form_data = project_to_edit
            project_form_data.technologies = (
                technologies  # Keep it as string for re-rendering form
            )
            return render_template(
                "add_edit_project.html", project=project_form_data, is_edit=True
            )

        if Project.update_project(project_to_edit):
            flash("Project updated successfully!", "success")
            try:
                # Invalidate cache for projects pages
                invalidate_multiple_caches("projects", "index")
                logger.info("Project caches invalidated after updating project")
            except Exception as e:
                logger.warning(f"Cache invalidation failed: {e}")
            return redirect(url_for("admin_projects"))
        else:
            flash("Error updating project.", "error")
    # For GET request, convert technologies list to comma-separated string for the form
    project_to_edit.technologies = (
        ", ".join(project_to_edit.technologies) if project_to_edit.technologies else ""
    )
    return render_template(
        "add_edit_project.html", project=project_to_edit, is_edit=True
    )


@app.route("/admin/projects/delete/<int:project_id>", methods=["POST"])
@login_required
def delete_project(project_id):
    if Project.delete_project_by_id(project_id):
        try:
            # Invalidate cache for projects pages
            invalidate_multiple_caches("projects", "index")
            logger.info("Project caches invalidated after deleting project")
        except Exception as e:
            logger.warning(f"Cache invalidation failed: {e}")
        flash("Project deleted successfully!", "success")
    else:
        flash("Error deleting project.", "error")
    return redirect(url_for("admin_projects"))


def _invalidate_project_caches():
    try:
        invalidate_multiple_caches("projects", "index")
    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")


@app.route("/admin/projects/<int:project_id>/toggle-visibility", methods=["POST"])
@login_required
def toggle_project_visibility(project_id):
    project = Project.get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "error")
    elif Project.set_flag(project_id, "is_visible", not project.is_visible):
        _invalidate_project_caches()
        state = "hidden from" if project.is_visible else "visible on"
        flash(f"'{project.title}' is now {state} the site.", "success")
    else:
        flash("Error updating project visibility.", "error")
    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<int:project_id>/toggle-featured", methods=["POST"])
@login_required
def toggle_project_featured(project_id):
    project = Project.get_project_by_id(project_id)
    if not project:
        flash("Project not found.", "error")
    elif Project.set_flag(project_id, "is_featured", not project.is_featured):
        _invalidate_project_caches()
        state = "unfeatured" if project.is_featured else "featured on the homepage"
        flash(f"'{project.title}' {state}.", "success")
    else:
        flash("Error updating featured flag.", "error")
    return redirect(url_for("admin_projects"))


@app.route("/admin/projects/<int:project_id>/move/<direction>", methods=["POST"])
@login_required
def move_project(project_id, direction):
    if direction not in ("up", "down"):
        flash("Invalid direction.", "error")
    elif Project.move(project_id, direction):
        _invalidate_project_caches()
    else:
        flash("Error reordering projects.", "error")
    return redirect(url_for("admin_projects"))


@app.route("/admin/homepage", methods=["GET", "POST"])
@login_required
def admin_homepage():
    if request.method == "POST":
        values = {
            "hero_emoji": (request.form.get("hero_emoji") or "").strip()
            or HOMEPAGE_DEFAULTS["hero_emoji"],
            "hero_greeting": (request.form.get("hero_greeting") or "").strip()
            or HOMEPAGE_DEFAULTS["hero_greeting"],
            "hero_line1": (request.form.get("hero_line1") or "").strip(),
            "hero_line2": (request.form.get("hero_line2") or "").strip(),
            "blog_cta_text": (request.form.get("blog_cta_text") or "").strip()
            or HOMEPAGE_DEFAULTS["blog_cta_text"],
            "show_readers_badge": request.form.get("show_readers_badge") == "on",
            "show_projects": request.form.get("show_projects") == "on",
        }
        if save_homepage_settings(values):
            _invalidate_project_caches()  # also clears the cached index view
            flash("Homepage settings saved.", "success")
        else:
            flash("Error saving homepage settings.", "error")
        return redirect(url_for("admin_homepage"))

    return render_template(
        "admin_homepage.html",
        settings=get_homepage_settings(),
        defaults=HOMEPAGE_DEFAULTS,
    )


@app.route("/compare")
def compare_projects():
    # Logic for comparing projects
    return render_template("compare.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500


@app.route("/health")
def health_check():
    """Health check endpoint to monitor application and cache status"""
    status = {
        "status": "healthy",
        "cache_type": app.config.get("CACHE_TYPE", "unknown"),
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Test cache connection
    try:
        cache.set("health_check", "ok", timeout=5)
        cache_result = cache.get("health_check")
        status["cache_status"] = "connected" if cache_result == "ok" else "disconnected"
        cache.delete("health_check")
    except Exception as e:
        status["cache_status"] = f"error: {str(e)}"
        logger.warning(f"Cache health check failed: {e}")

    return status


@app.route("/sitemap.xml")
def sitemap():
    """Generate sitemap for SEO"""
    try:
        articles = Article.get_published_articles()

        from sitemap_generator import generate_sitemap

        pages = generate_sitemap(app, articles=articles)

        sitemap_xml = render_template("sitemap.xml", pages=pages)
        response = app.response_class(sitemap_xml, mimetype="application/xml")
        return response
    except Exception as e:
        logger.error(f"Error generating sitemap: {e}")
        return "Error generating sitemap", 500


@app.route("/image-sitemap.xml")
def image_sitemap():
    """Generate image sitemap for better image SEO"""
    try:
        articles = Article.get_published_articles()

        from sitemap_generator import generate_image_sitemap

        images = generate_image_sitemap(app, articles=articles)

        sitemap_xml = render_template("image_sitemap.xml", images=images)
        response = app.response_class(sitemap_xml, mimetype="application/xml")
        return response
    except Exception as e:
        logger.error(f"Error generating image sitemap: {e}")
        return "Error generating image sitemap", 500


@app.route("/robots.txt")
def robots():
    """Generate robots.txt for SEO"""
    robots_content = f"""User-agent: *
Allow: /

# Sitemap
Sitemap: {url_for("sitemap", _external=True)}
Sitemap: {url_for("image_sitemap", _external=True)}

# Disallow admin and private areas
Disallow: /admin/
Disallow: /login
Disallow: /logout
Disallow: /publish
"""

    response = app.response_class(robots_content, mimetype="text/plain")
    return response


@app.route("/admin/clear-cache")
@login_required
def clear_cache():
    """Clear all caches for testing"""
    try:
        cache.clear()
        flash("Cache has been cleared!", "success")
        logger.info("All caches cleared manually")
    except Exception as e:
        flash(f"Error clearing cache: {e}", "error")
        logger.error(f"Error clearing cache: {e}")

    return redirect(url_for("admin_dashboard"))


@app.route("/api/auto-save", methods=["POST"])
@login_required
def auto_save():
    """Auto-save endpoint for the modern editor"""
    try:
        data = request.get_json()
        title = data.get("title", "")
        content = data.get("content", "")
        slug = data.get("slug")

        if not title.strip():
            return {"status": "error", "message": "Title is required"}, 400

        if slug:
            # Update existing article
            article = Article.get_by_slug(slug)
            if not article:
                return {"status": "error", "message": "Article not found"}, 404

            article.title = title
            article.content = content

            if Article.update_article(article):
                # Clear cache
                cache.delete(f"article_content_{article.slug}")
                return {
                    "status": "success",
                    "message": "Auto-saved",
                    "slug": article.slug,
                }
            else:
                return {"status": "error", "message": "Failed to save"}, 500
        else:
            # Create new draft - check if title already exists and append timestamp
            import time

            from slugify import slugify

            base_slug = slugify(title)
            final_slug = base_slug

            # Check if slug exists and make it unique
            existing_article = Article.get_by_slug(final_slug)
            if existing_article:
                timestamp = int(time.time())
                final_slug = f"{base_slug}-{timestamp}"

            new_article = Article(
                title=title,
                content=content,
                date_published=datetime.now(UTC),
                is_published=False,
                slug=final_slug,
            )

            if Article.save_article(new_article):
                return {
                    "status": "success",
                    "message": "Draft created",
                    "slug": new_article.slug,
                }
            else:
                return {"status": "error", "message": "Failed to create draft"}, 500

    except Exception as e:
        logger.error(f"Auto-save error: {e}")
        return {"status": "error", "message": "Server error"}, 500


if __name__ == "__main__":
    debug_mode = (
        os.getenv("FLASK_ENV") == "development" or os.getenv("FLASK_DEBUG") == "1"
    )
    app.run(port=4200, debug=debug_mode)
