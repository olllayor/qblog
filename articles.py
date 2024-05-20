import os
from slugify import slugify
from datetime import datetime

class Article:
    def __init__(self, title, content, date_published):
        self.title = title
        self.content = content
        self.date_published = date_published
        
    @property
    def slug(self):
        return slugify(self.title)
    
    def load_content(self):
        # Assuming the first line of each file is the date_published
        file_path = f"articles/{self.title}"
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            self.date_published = lines[1].strip()  # Assuming the date is on the second line
            self.content = ''.join(lines[2:])  # Join the remaining lines as content
    @classmethod
    def all(cls):
        titles = os.listdir('articles')
        slug_articles = {}                       
        for title in titles:
            slug = slugify(title)
            article = Article(title, "", "")
            article.load_content()
            slug_articles[slug] = article

        # Sort articles by datetime
        return slug_articles
            