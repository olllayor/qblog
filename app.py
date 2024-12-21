import os
from datetime import datetime
from slugify import slugify
from flask import Flask, render_template, redirect, url_for, request, session, flash
from articles import Article
from functools import wraps
import logging
from api_analytics.flask import add_middleware
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
add_middleware(app, os.getenv('API_ANALYTICS_KEY'))  # Add middleware

# articles = Article.all() # Removed, now loading from db

# Environment configuration
app.secret_key = os.getenv('FLASK_SECRET_KEY')
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Logger configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Dummy check for the username and password. Replace with your database check or more secure checks.
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
def index():
    return render_template('index.html')

@app.route('/projects')
def projects():
    return render_template('projects.html')

@app.route('/blog')
def blog():
    articles = Article.get_all_articles()
    # published_articles = [article for article in articles if article.is_published]
    return render_template('blog.html', articles=articles)

@app.route('/media/ollayor-cv.pdf')
def cv_redirect():
    return redirect(url_for('static', filename='media/Olloyor_s_resume.pdf'))

@app.route('/blog/<slug>')
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
            return redirect(url_for('article', slug = article.slug))
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
    else:
        print('Error deleting article from the database.')
        flash('Error deleting article from the database.', 'error')

    
    return redirect(url_for('blog'))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(port=4200, debug=True)