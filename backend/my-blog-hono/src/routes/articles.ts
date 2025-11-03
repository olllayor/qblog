import { Hono } from 'hono';
import { ArticleService } from '../db/articles';
import { requireAuth } from '../middleware/auth';
import { successResponse, errorResponse, getClientIp, getQueryInt, clamp } from '../lib/utils';

export type ArticleRoutes = {
	Variables: {
		articleService: ArticleService;
	};
};

export const articleRoutes = new Hono<ArticleRoutes>();

const ARTICLES_PER_PAGE = 6;
const MAX_PER_PAGE = 24;

articleRoutes.get('/api/articles', async (c) => {
	try {
		const articleService = c.get('articleService');
		const page = getQueryInt(c, 'page', 1);
		const perPage = clamp(getQueryInt(c, 'per_page', ARTICLES_PER_PAGE), 1, MAX_PER_PAGE);

		const { articles, total } = await articleService.getPublishedArticlesPaginated(page, perPage);

		const payload = articles.map((article) => ({
			slug: article.slug,
			title: article.title,
			summary: articleService['getSummary'](article.content, 200),
			published_on: new Date(article.date_published).toLocaleDateString('en-US', {
				day: 'numeric',
				month: 'long',
				year: 'numeric',
			}),
			reading_time: articleService['getReadingTime'](article.content),
		}));

		return successResponse(c, {
			articles: payload,
			has_more: page * perPage < total,
			total,
		});
	} catch (error) {
		console.error('Error fetching articles:', error);
		return errorResponse(c, 'Failed to fetch articles');
	}
});

articleRoutes.get('/blog/:slug', async (c) => {
	try {
		const slug = c.req.param('slug');
		if (!slug) return c.notFound();

		const articleService = c.get('articleService');

		const article = await articleService.getBySlug(slug);
		if (!article) {
			return c.notFound();
		}

		if (!article.is_published) {
			return c.notFound();
		}

		const ipAddress = getClientIp(c);
		const userAgent = c.req.header('user-agent') || '';

		await articleService.trackView(slug, ipAddress, userAgent);

		const viewCount = await articleService.getViewCount(slug);
		const baseUrl = c.req.header('x-forwarded-proto') + '://' + c.req.header('host');

		return successResponse(c, {
			...articleService.formatArticleResponse(article, baseUrl),
			viewCount,
		});
	} catch (error) {
		console.error('Error fetching article:', error);
		return errorResponse(c, 'Failed to fetch article');
	}
});

articleRoutes.post('/api/articles', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const articleService = c.get('articleService');
		const body = await c.req.json<{ title: string; content: string; is_published?: boolean }>();

		if (!body.title?.trim() || !body.content?.trim()) {
			return errorResponse(c, 'Missing required fields');
		}

		const article = await articleService.createArticle(body.title, body.content, body.is_published ?? false);

		return c.json({ status: 'success', data: articleService.formatArticleResponse(article) }, 201);
	} catch (error) {
		console.error('Error creating article:', error);
		return errorResponse(c, 'Failed to create article');
	}
});

articleRoutes.put('/blog/:slug', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const slug = c.req.param('slug');
		if (!slug) return c.notFound();

		const articleService = c.get('articleService');
		const body = await c.req.json<Partial<{ title: string; content: string; is_published: boolean }>>();

		const updated = await articleService.updateArticle(slug, {
			title: body.title,
			content: body.content,
			is_published: body.is_published,
		});

		return successResponse(c, articleService.formatArticleResponse(updated));
	} catch (error) {
		console.error('Error updating article:', error);
		return errorResponse(c, 'Failed to update article');
	}
});

articleRoutes.delete('/blog/:slug', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const slug = c.req.param('slug');
		if (!slug) return c.notFound();

		const articleService = c.get('articleService');

		const success = await articleService.deleteBySlug(slug);
		if (!success) {
			return errorResponse(c, 'Article not found');
		}

		return successResponse(c, { slug });
	} catch (error) {
		console.error('Error deleting article:', error);
		return errorResponse(c, 'Failed to delete article');
	}
});

articleRoutes.post('/api/auto-save', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const articleService = c.get('articleService');
		const body = await c.req.json<{ title?: string; content?: string; slug?: string }>();

		if (!body.title?.trim()) {
			return errorResponse(c, 'Title is required');
		}

		if (body.slug) {
			const article = await articleService.updateArticle(body.slug, {
				title: body.title,
				content: body.content,
			});
			return successResponse(c, { slug: article.slug });
		} else {
			const article = await articleService.createArticle(body.title, body.content || '', false);
			return successResponse(c, { slug: article.slug });
		}
	} catch (error) {
		console.error('Error auto-saving:', error);
		return errorResponse(c, 'Failed to auto-save');
	}
});
