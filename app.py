import logging
import os
import time
from datetime import UTC, datetime
from functools import wraps

import redis
import sentry_sdk
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_caching import Cache
from posthog import Posthog

from articles import Article
from database import close_db, get_database_url, init_db
from projects import Project

# from api_analytics.flask import add_middleware

load_dotenv()

posthog = Posthog(
    project_api_key="phc_CfLxspEhOAhLn6L3vQH2wP5Os31vXojDeaIqK8f4Y0W",
    host="https://us.i.posthog.com",
)

# Configure logging early so we can see startup messages
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sentry_sdk.init(
    dsn="https://abb5b78f25e14da8713e4d4c8be6c5da@o4508810359144448.ingest.de.sentry.io/4509507866001488",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

app = Flask(__name__)

logger = logging.getLogger(__name__)


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

        except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
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
        @wraps(f)
        def wrapper(*args, **kwargs_inner):
            try:
                # Try to use cache
                cached_func = cache.cached(timeout=timeout, **kwargs)(f)
                result = cached_func(*args, **kwargs_inner)
                logger.debug(f"Cache hit for {f.__name__}")
                return result
            except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
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
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

with app.app_context():
    try:
        if not init_db():
            logger.error("Error initializing database during app setup")
    except Exception as e:
        logger.error(f"Exception during db initialization: {e}")


@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)


def check_admin(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("You need to login first.")
            qs = request.query_string.decode() if request.query_string else ""
            next_path = request.path + (f"?{qs}" if qs else "")
            return redirect(url_for("login", next=next_path))

    return wrap


@app.route("/login", methods=["GET", "POST"])
def login():
    # If already logged in and next specified, go there
    if request.method == "GET" and session.get("logged_in"):
        next_url = request.args.get("next")
        if next_url and next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
    if request.method == "POST":
        if check_admin(request.form["username"], request.form["password"]):
            session["logged_in"] = True
            flash("You were just logged in!")
            # Redirect back to the original destination if provided and safe
            next_url = request.form.get("next") or request.args.get("next")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("blog"))
        else:
            flash("Wrong credentials!")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("logged_in", None)
    flash("You were just logged out!")
    return redirect(url_for("login"))


@app.route("/")
@safe_cached(timeout=300)
def index():
    try:
        projects = Project.get_all_projects()
    except Exception as e:
        logger.warning(f"Failed to load projects: {e}")
        projects = []

    try:
        view_totals = Article.get_view_totals()
        all_time_readers = view_totals.get("all_time", view_totals.get("monthly", 0))
    except Exception as e:
        logger.warning(f"Failed to load view totals: {e}")
        all_time_readers = 0

    # PostHog feature flag implementation
    distinct_id = request.remote_addr or "anonymous"
    is_my_flag_enabled = posthog.feature_enabled("my-flag", distinct_id)

    if is_my_flag_enabled:
        # Do something differently for this user
        logger.info(f"Feature flag 'my-flag' enabled for user {distinct_id}")

    return render_template(
        "index.html", projects=projects, all_time_readers=all_time_readers
    )


@app.route("/favicon.ico")
def favicon():
    return redirect(url_for("static", filename="favicon.ico"))


@app.route("/projects")
@safe_cached(timeout=180)
def projects():
    all_projects = Project.get_all_projects()
    return render_template("projects.html", projects=all_projects)


@app.route("/blog")
@safe_cached(timeout=180)
def blog():
    start = time.time()
    per_page = BLOG_ARTICLES_PER_PAGE
    articles, total_articles = Article.get_published_articles_paginated(
        page=1, per_page=per_page
    )
    duration = time.time() - start
    logger.info(f"/blog route executed in {duration:.3f} seconds")
    has_more = len(articles) < total_articles
    return render_template(
        "blog.html",
        articles=articles,
        per_page=per_page,
        total_articles=total_articles,
        has_more=has_more,
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

    articles, total_articles = Article.get_published_articles_paginated(
        page=page, per_page=per_page
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
    Article.track_view(slug, ip_address, user_agent)

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
    if not article.is_published and "logged_in" not in session:
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


@app.route("/matrix")
def matrix():
    return render_template("matrix.html")


@app.route("/publish", methods=["GET", "POST"])
@login_required
def publish():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        is_published = request.form.get("is_published") == "on"
        date_published = datetime.now(UTC)
        if not title or not content:
            flash("Title or content is missing", "error")
            return redirect(url_for("publish"))

        new_article = Article(title, content, date_published, is_published=is_published)
        Article.save_article(new_article)
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


@app.route("/publish/classic", methods=["GET", "POST"])
@login_required
def publish_classic():
    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        is_published = request.form.get("is_published") == "on"
        date_published = datetime.now(UTC)
        if not title or not content:
            flash("Title or content is missing", "error")
            return redirect(url_for("publish_classic"))

        new_article = Article(title, content, date_published, is_published=is_published)
        Article.save_article(new_article)
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

    return render_template("publish.html")


@app.route("/blog/<slug>/edit", methods=["GET", "POST"])
@login_required
def edit_article(slug):
    article = Article.get_by_slug(slug)
    if not article:
        return render_template("404.html"), 404
    if request.method == "POST":
        old_published_status = article.is_published
        article.title = request.form.get("title")
        article.content = request.form.get("content")
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


@app.route("/blog/<slug>/delete", methods=["DELETE", "POST", "GET"])
@login_required
def delete_article(slug):
    print(f"Attempting to delete article with slug: {slug}")

    success = Article.delete_article_by_slug(slug)
    if success:
        try:
            print(f"Deleting article file: {slug}")
            flash("Article deleted successfully.", "success")
        except OSError as e:
            print(f"Error deleting article file: {e.strerror}")
            flash(f"Error deleting article file: {e.strerror}", "error")

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
        print("Error deleting article from the database.")
        flash("Error deleting article from the database.", "error")

    return redirect(url_for("blog"))


@app.route("/admin")
@login_required
def admin_dashboard():
    # Aggregate basic stats
    try:
        all_articles = Article.get_all_articles()
    except Exception as e:
        logger.warning("Failed to fetch all articles: %s", e)
        all_articles = []

    articles_count = len(all_articles)
    published_count = sum(1 for a in all_articles if getattr(a, "is_published", False))
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

    # Recent 5 articles by last update or publish date
    def _article_dt(a):
        return (
            getattr(a, "date_updated", None)
            or getattr(a, "date_published", None)
            or datetime.fromtimestamp(0, UTC)
        )

    recent_articles = sorted(all_articles, key=_article_dt, reverse=True)[:5]

    return render_template(
        "admin_dashboard.html",
        articles_count=articles_count,
        published_count=published_count,
        drafts_count=drafts_count,
        projects_count=projects_count,
        daily_views=view_totals.get("daily", 0),
        monthly_views=view_totals.get("monthly", 0),
        recent_articles=recent_articles,
    )


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

    articles_count = len(Article.get_all_articles())
    projects_count = len(Project.get_all_projects())

    return render_template(
        "analytics.html",
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
        articles = Article.get_all_articles()

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
        articles = Article.get_all_articles()

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
        flash("Cache cleared successfully!", "success")
        logger.info("All caches cleared manually")
    except Exception as e:
        flash(f"Error clearing cache: {e}", "error")
        logger.error(f"Error clearing cache: {e}")

    return redirect(url_for("blog"))


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
