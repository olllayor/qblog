import { D1Database } from '@cloudflare/workers-types';
import { Article } from './schema';

const ARTICLES_PER_PAGE = 6;

export class ArticleService {
	constructor(private db: D1Database) {}

	private generateSlug(title: string): string {
		return title
			.toLowerCase()
			.trim()
			.replace(/[^\w\s-]/g, '')
			.replace(/[\s_]+/g, '-')
			.replace(/^-+|-+$/g, '');
	}

	private getReadingTime(content: string): number {
		const cleanText = content.replace(/<[^>]+>/g, '');
		const wordCount = cleanText.split(/\s+/).length;
		return Math.max(1, Math.round(wordCount / 225));
	}

	private getSummary(content: string, length: number = 160): string {
		const cleanText = content.replace(/<[^>]+>/g, '');
		if (cleanText.length <= length) return cleanText;
		return cleanText.substring(0, length).split(' ').slice(0, -1).join(' ') + '...';
	}

	private getFirstImage(content: string, baseUrl: string = 'https://ollayor.uz'): string | null {
		const imgPattern = /<img[^>]+src=["']([^"']+)["'][^>]*>/i;
		const match = content.match(imgPattern);

		if (!match) return null;

		const imgSrc = match[1];
		if (imgSrc.startsWith('/')) {
			return `${baseUrl}${imgSrc}`;
		} else if (imgSrc.startsWith('http')) {
			return imgSrc;
		} else {
			return `${baseUrl}/${imgSrc}`;
		}
	}

	async createArticle(title: string, content: string, isPublished: boolean = false): Promise<Article> {
		const slug = this.generateSlug(title);
		const datePublished = new Date().toISOString();

		const result = await this.db
			.prepare(
				`
        INSERT INTO articles (title, content, date_published, is_published, slug)
        VALUES (?, ?, ?, ?, ?)
        RETURNING *
      `,
			)
			.bind(title, content, datePublished, isPublished ? 1 : 0, slug)
			.first<Article>();

		if (!result) {
			throw new Error('Failed to create article');
		}

		return result;
	}

	async updateArticle(slug: string, updates: Partial<Article>): Promise<Article> {
		const dateUpdated = new Date().toISOString();
		const article = await this.getBySlug(slug);

		if (!article) {
			throw new Error('Article not found');
		}

		const title = updates.title ?? article.title;
		const content = updates.content ?? article.content;
		const isPublished = updates.is_published ?? article.is_published;

		const result = await this.db
			.prepare(
				`
        UPDATE articles
        SET title = ?, content = ?, is_published = ?, date_updated = ?
        WHERE slug = ?
        RETURNING *
      `,
			)
			.bind(title, content, isPublished ? 1 : 0, dateUpdated, slug)
			.first<Article>();

		if (!result) {
			throw new Error('Failed to update article');
		}

		return result;
	}

	async getBySlug(slug: string): Promise<Article | null> {
		const result = await this.db.prepare('SELECT * FROM articles WHERE slug = ?').bind(slug).first<Article>();

		return result || null;
	}

	async getById(id: number): Promise<Article | null> {
		const result = await this.db.prepare('SELECT * FROM articles WHERE id = ?').bind(id).first<Article>();

		return result || null;
	}

	async getPublishedArticlesPaginated(
		page: number = 1,
		perPage: number = ARTICLES_PER_PAGE,
	): Promise<{ articles: Article[]; total: number }> {
		const offset = (page - 1) * perPage;

		const articles = await this.db
			.prepare(
				`
        SELECT * FROM articles
        WHERE is_published = 1
        ORDER BY date_published DESC
        LIMIT ? OFFSET ?
      `,
			)
			.bind(perPage, offset)
			.all<Article>();

		const countResult = await this.db
			.prepare('SELECT COUNT(*) as count FROM articles WHERE is_published = 1')
			.first<{ count: number }>();

		return {
			articles: articles.results || [],
			total: countResult?.count || 0,
		};
	}

	async getAllArticles(): Promise<Article[]> {
		const result = await this.db.prepare('SELECT * FROM articles ORDER BY date_published DESC').all<Article>();

		return result.results || [];
	}

	async deleteBySlug(slug: string): Promise<boolean> {
		const result = await this.db.prepare('DELETE FROM articles WHERE slug = ?').bind(slug).run();

		return result.success;
	}

	async trackView(slug: string, ipAddress: string, userAgent?: string): Promise<void> {
		try {
			await this.db
				.prepare(
					`
          INSERT INTO article_views (article_slug, ip_address, user_agent)
          VALUES (?, ?, ?)
          ON CONFLICT(article_slug, ip_address) DO NOTHING
        `,
				)
				.bind(slug, ipAddress, userAgent || '')
				.run();
		} catch (error) {
			console.error('Error tracking view:', error);
		}
	}

	async getViewCount(slug: string): Promise<number> {
		const result = await this.db
			.prepare('SELECT COUNT(*) as count FROM article_views WHERE article_slug = ?')
			.bind(slug)
			.first<{ count: number }>();

		return result?.count || 0;
	}

	async getViewTotals(): Promise<{ daily: number; monthly: number }> {
		const now = new Date();
		const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000);
		const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

		const daily = await this.db
			.prepare('SELECT COUNT(*) as count FROM article_views WHERE viewed_at >= ?')
			.bind(oneDayAgo.toISOString())
			.first<{ count: number }>();

		const monthly = await this.db
			.prepare('SELECT COUNT(*) as count FROM article_views WHERE viewed_at >= ?')
			.bind(oneMonthAgo.toISOString())
			.first<{ count: number }>();

		return {
			daily: daily?.count || 0,
			monthly: monthly?.count || 0,
		};
	}

	formatArticleResponse(article: Article, baseUrl: string = 'https://ollayor.uz') {
		return {
			slug: article.slug,
			title: article.title,
			content: article.content,
			datePublished: article.date_published,
			dateUpdated: article.date_updated,
			isPublished: article.is_published,
			readingTime: this.getReadingTime(article.content),
			wordCount: article.content.replace(/<[^>]+>/g, '').split(/\s+/).length,
			summary: this.getSummary(article.content),
			firstImage: this.getFirstImage(article.content, baseUrl),
		};
	}
}
