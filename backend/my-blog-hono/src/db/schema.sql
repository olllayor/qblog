-- Articles table
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  date_published DATETIME NOT NULL,
  date_updated DATETIME,
  is_published BOOLEAN NOT NULL DEFAULT FALSE,
  slug TEXT UNIQUE NOT NULL
);

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  image_url TEXT,
  technologies TEXT,
  github_link TEXT,
  live_demo_link TEXT,
  date_added DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Article views tracking table
CREATE TABLE IF NOT EXISTS article_views (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_slug TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  user_agent TEXT,
  viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(article_slug, ip_address)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_articles_published_date 
ON articles (is_published, date_published DESC);

CREATE INDEX IF NOT EXISTS idx_article_views_slug 
ON article_views (article_slug);
