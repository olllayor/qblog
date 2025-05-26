import logging
import os
import time

from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_caching import Cache
from api_analytics.flask import add_middleware

from articles import Article
from database import close_db, init_db  # Import get_db and close_db
from projects import Project  # Add this import

load_dotenv()
app = Flask(__name__)
add_middleware(app, os.getenv('API_ANALYTICS_KEY'))
logger = logging.getLogger(__name__)
# Configure caching
app.config['CACHE_TYPE'] = 'RedisCache'
app.config['CACHE_REDIS_URL'] = os.getenv('REDIS_URL')
app.config['CACHE_DEFAULT_TIMEOUT'] = 180

# Initialize cache
cache = Cache(app)


app.secret_key = os.getenv('FLASK_SECRET_KEY')
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize database within an application context
with app.app_context():
    try:
        if not init_db():
            logger.error("Error initializing database during app setup") # Changed print to logger.error
    except Exception as e:
        logger.error(f"Exception during db initialization: {e}") # Changed print to logger.error

@app.teardown_appcontext
def teardown_db(exception):
    close_db(exception)

def check_admin(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if check_admin(request.form['username'], request.form['password']):
            session['logged_in'] = True
            flash('You were just logged in!')
            return redirect(url_for('blog'))
        else:
            flash('Wrong credentials!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('logged_in', None)
    flash('You were just logged out!')
    return redirect(url_for('login'))

@app.route('/')
@cache.cached(timeout=300)
def index():
    return render_template('index.html')

@app.route('/projects')
@cache.cached(timeout=180)
def projects():
    all_projects = Project.get_all_projects()
    return render_template('projects.html', projects=all_projects)

@app.route('/blog')
@cache.cached(timeout=180)
def blog():
    start = time.time()
    articles = Article.get_all_articles()
    duration = time.time() - start
    logger.info(f"/blog route executed in {duration:.3f} seconds")
    return render_template('blog.html', articles=articles)

@app.route('/media/ollayor-cv.pdf')
def cv_redirect():
    return redirect(url_for('static', filename='media/Olloyor_s_resume.pdf'))

@app.route('/blog/<slug>')
@cache.cached(timeout=180, query_string=False)
def article(slug: str):
    article = Article.get_by_slug(slug)
    if not article:
        return render_template('404.html'), 404
    return render_template('article.html', article=article)

@app.route('/talks')
def talks():
    return render_template('talks.html')

@app.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        is_published = request.form.get('is_published') == 'on'
        date_published = datetime.utcnow()
        if not title or not content:
            flash("Title or content is missing", "error")
            return redirect(url_for('publish'))

        new_article = Article(title, content, date_published, is_published=is_published)
        Article.save_article(new_article)
        # remove the article from cache

        cache.delete_memoized(blog)
        cache.delete_memoized(article, new_article.slug)

        flash("Article saved successfully. You can publish it now.", "success")
        return redirect(url_for('article', slug=new_article.slug))

    return render_template('publish.html')
    
@app.route('/blog/<slug>/edit', methods=['GET', 'POST'])
@login_required
def edit_article(slug):
    article = Article.get_by_slug(slug)
    if not article:
        return render_template('404.html'), 404
    if request.method == 'POST':
        article.title = request.form.get('title')
        article.content = request.form.get('content')
        article.is_published = request.form.get('is_published') == 'on'
        
        if Article.update_article(article):
            flash('Article updated successfully', 'success')

            cache.delete_memoized(blog)
            cache.delete_memoized(article, article.slug)
            return redirect(url_for('article', slug=article.slug))
        else:
             flash('Error updating article', 'error')
        
    return render_template('publish.html', article=article)
    

@app.route('/blog/<slug>/delete', methods=['DELETE', 'POST', 'GET'])
@login_required
def delete_article(slug):
    print(f"Attempting to delete article with slug: {slug}") 

    
    success = Article.delete_article_by_slug(slug)
    if success:
        try:
            print(f"Deleting article file: {slug}")
            flash('Article deleted successfully.', 'success')
        except OSError as e:
            print(f'Error deleting article file: {e.strerror}')
            flash(f'Error deleting article file: {e.strerror}', 'error')
        
        cache.delete_memoized(blog)
        cache.delete_memoized(article, slug)
    else:
        print('Error deleting article from the database.')
        flash('Error deleting article from the database.', 'error')

    
    return redirect(url_for('blog'))

@app.route('/admin/projects')
@login_required
def admin_projects():
    all_projects = Project.get_all_projects()
    return render_template('admin_projects.html', projects=all_projects)

@app.route('/admin/projects/add', methods=['GET', 'POST'])
@login_required
def add_project():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        image_url = request.form.get('image_url')
        technologies = request.form.get('technologies') # Comma-separated string
        github_link = request.form.get('github_link')
        live_demo_link = request.form.get('live_demo_link')

        if not title or not description:
            flash('Title and description are required.', 'error')
            return render_template('add_edit_project.html', project=request.form)
        
        # Convert comma-separated string to list for storage, or handle as string if preferred
        tech_list = [tech.strip() for tech in technologies.split(',')] if technologies else []

        new_project = Project(
            title=title,
            description=description,
            image_url=image_url,
            technologies=tech_list, # Pass as list
            github_link=github_link,
            live_demo_link=live_demo_link
        )
        if Project.save_project(new_project):
            flash('Project added successfully!', 'success')
            return redirect(url_for('admin_projects'))
        else:
            flash('Error adding project.', 'error')
    return render_template('add_edit_project.html')

@app.route('/admin/projects/edit/<int:project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    project_to_edit = Project.get_project_by_id(project_id)
    if not project_to_edit:
        flash('Project not found.', 'error')
        return redirect(url_for('admin_projects'))

    if request.method == 'POST':
        project_to_edit.title = request.form.get('title')
        project_to_edit.description = request.form.get('description')
        project_to_edit.image_url = request.form.get('image_url')
        technologies = request.form.get('technologies')
        project_to_edit.technologies = [tech.strip() for tech in technologies.split(',')] if technologies else []
        project_to_edit.github_link = request.form.get('github_link')
        project_to_edit.live_demo_link = request.form.get('live_demo_link')

        if not project_to_edit.title or not project_to_edit.description:
            flash('Title and description are required.', 'error')
            # Pass technologies back as a string for the form
            project_form_data = project_to_edit
            project_form_data.technologies = technologies # Keep it as string for re-rendering form
            return render_template('add_edit_project.html', project=project_form_data, is_edit=True)

        if Project.update_project(project_to_edit):
            flash('Project updated successfully!', 'success')
            return redirect(url_for('admin_projects'))
        else:
            flash('Error updating project.', 'error')
    # For GET request, convert technologies list to comma-separated string for the form
    project_to_edit.technologies = ", ".join(project_to_edit.technologies) if project_to_edit.technologies else ""
    return render_template('add_edit_project.html', project=project_to_edit, is_edit=True)

@app.route('/admin/projects/delete/<int:project_id>', methods=['POST'])
@login_required
def delete_project(project_id):
    if Project.delete_project_by_id(project_id):
        flash('Project deleted successfully!', 'success')
    else:
        flash('Error deleting project.', 'error')
    return redirect(url_for('admin_projects'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(port=4200)