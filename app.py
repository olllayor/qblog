from datetime import datetime
from slugify import slugify
import os
from flask import Flask, render_template, redirect, url_for, request, session, flash

from functools import wraps
# from flask_ckeditor import CKEditor

from articles import Article 
app = Flask(__name__)
articles = Article.all()

app.secret_key = 'your_secret_key'


ARTICLES_DIR = "articles"
if not os.path.exists(ARTICLES_DIR):
    os.makedirs(ARTICLES_DIR)  # Make sure the articles directory exists


# Dummy check for the username and password. Replace with your database check or more secure checks.
def check_admin(username, password):
    return username == 'admin' and password == 'password'

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
            return redirect(url_for('publish'))
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
    # Render the main page
    return render_template('index.html')


@app.route('/projects')
def projects():
    # Render the projects page
    return render_template('projects.html')

@app.route('/blog')
def blog():
    articles = Article.all()  # Retrieve all articles
    # Convert the date_published to datetime objects and sort the articles
    sorted_articles = sorted(articles.values(), key=lambda a: datetime.strptime(a.date_published, "%d %B, %Y"), reverse=True)
    return render_template('blog.html', articles=sorted_articles)

@app.route('/blog/<slug>')
def article(slug: str):
    article = articles[slug]    
    return render_template('article.html', article=article)

@app.route('/talks')
def talks():
    # Render the talks page
    return render_template('talks.html')


# @app.errorhandler(404)# type: ignore
# def page_not_found(e): # type: ignore
#     return render_template('404.html'), 404

# @app.errorhandler(500) # type: ignore
# def page_not_found(e):
#     return render_template('500.html'), 500


@app.route('/publish', methods=['GET', 'POST'])
@login_required
def publish():
    if request.method == 'POST':
        title = request.form.get('title')  # Use .get() for safe access
        content = request.form.get('content')  # Use .get() for safe access
        date_published = datetime.utcnow().strftime("%d %B, %Y")
        if not title or not content:
            # Handle the error, such as returning an error message to the user
            flash("Title or content is missing", "error")
            return redirect(url_for('publish'))
        
    
        
        # For example, writing to a file
        article_filename = slugify(title)
        article_path = os.path.join(ARTICLES_DIR, article_filename)
        with open(article_path, 'w', encoding='utf-8') as file:
            file.write(f"{title}\n{date_published}\n\n{content}")               
            

        # Redirect to a new page or display a success message
        new_article = Article(title, content, date_published)
        articles[new_article.slug] = new_article  # Update the dictionary with the new article
        flash("Article published successfully", "success")
        return redirect(url_for('article', slug=new_article.slug))
    return render_template('publish.html')

@app.route('/<slug>/delete', methods=['POST'])
@login_required  # Assuming your admin authentication is done with this decorator
def delete_article(slug):
    if session.get('username') == 'admin':  # Replace with actual admin check
        article_path = os.path.join(ARTICLES_DIR, slug)
        try:
            os.remove(article_path)
            # Assuming articles is a dictionary with slugs as keys
            articles.pop(slug, None)  
            flash('Article deleted successfully.', 'success')
        except OSError as e:
            flash(f'Error deleting article: {e.strerror}', 'error')
    else:
        flash('You do not have permission to delete articles.', 'error')
    
    return redirect(url_for('blog'))


if __name__ == '__main__':
    app.run(port=4200, debug=False)