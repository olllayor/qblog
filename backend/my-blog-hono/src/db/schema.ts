import { D1Database } from '@cloudflare/workers-types';

export interface Article {
	id: number;
	title: string;
	content: string;
	date_published: string;
	date_updated?: string;
	is_published: boolean;
	slug: string;
}

export interface Project {
	id: number;
	title: string;
	description: string;
	image_url?: string;
	technologies?: string;
	github_link?: string;
	live_demo_link?: string;
	date_added: string;
}

export interface ArticleView {
	id: number;
	article_slug: string;
	ip_address: string;
	user_agent?: string;
	viewed_at: string;
}

export async function initDb(db: D1Database): Promise<void> {
	const statements = [
		`
    CREATE TABLE IF NOT EXISTS articles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      date_published DATETIME NOT NULL,
      date_updated DATETIME,
      is_published BOOLEAN NOT NULL DEFAULT FALSE,
      slug TEXT UNIQUE NOT NULL
    )
    `,
		`
    CREATE TABLE IF NOT EXISTS projects (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      description TEXT NOT NULL,
      image_url TEXT,
      technologies TEXT,
      github_link TEXT,
      live_demo_link TEXT,
      date_added DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    `,
		`
    CREATE TABLE IF NOT EXISTS article_views (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      article_slug TEXT NOT NULL,
      ip_address TEXT NOT NULL,
      user_agent TEXT,
      viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(article_slug, ip_address)
    )
    `,
		`
    CREATE INDEX IF NOT EXISTS idx_articles_published_date 
    ON articles (is_published, date_published DESC)
    `,
		`
    CREATE INDEX IF NOT EXISTS idx_article_views_slug 
    ON article_views (article_slug)
    `,
	];

	for (const statement of statements) {
		try {
			await db.prepare(statement).run();
		} catch (error) {
			console.error('Error executing schema statement:', error);
		}
	}

	console.info('Database initialized or already exists.');
}
