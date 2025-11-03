import { Hono } from 'hono';
import { swaggerUI } from '@hono/swagger-ui';
import type { D1Database } from '@cloudflare/workers-types';
import { ArticleService } from './db/articles';
import { ProjectService } from './db/projects';
import { authMiddleware } from './middleware/auth';
import { articleRoutes } from './routes/articles';
import { projectRoutes } from './routes/projects';
import { authRoutes } from './routes/auth';

type Bindings = {
	DB: D1Database;
	ADMIN_USERNAME: string;
	ADMIN_PASSWORD: string;
};

type Variables = {
	articleService: ArticleService;
	projectService: ProjectService;
	isAdmin: boolean;
};

const app = new Hono<{ Bindings: Bindings; Variables: Variables }>();

app.get('/docs', swaggerUI({ url: '/openapi.json' }));

app.get('/openapi.json', (c) => {
	return c.json({
		openapi: '3.0.0',
		info: { title: 'QBlog API', version: '1.0.0' },
		servers: [{ url: 'http://localhost:8787' }],
		paths: {
			'/': {
				get: { summary: 'Health check', responses: { 200: { description: 'OK' } } },
			},
			'/api/articles': {
				get: { summary: 'List articles', responses: { 200: { description: 'Articles list' } } },
				post: { summary: 'Create article', responses: { 201: { description: 'Created' } } },
			},
			'/api/articles/{id}': {
				get: { summary: 'Get article', responses: { 200: { description: 'Article' } } },
				put: { summary: 'Update article', responses: { 200: { description: 'Updated' } } },
				delete: { summary: 'Delete article', responses: { 204: { description: 'Deleted' } } },
			},
			'/api/projects': {
				get: { summary: 'List projects', responses: { 200: { description: 'Projects list' } } },
				post: { summary: 'Create project', responses: { 201: { description: 'Created' } } },
			},
			'/api/projects/{id}': {
				get: { summary: 'Get project', responses: { 200: { description: 'Project' } } },
				put: { summary: 'Update project', responses: { 200: { description: 'Updated' } } },
				delete: { summary: 'Delete project', responses: { 204: { description: 'Deleted' } } },
			},
			'/login': {
				post: { summary: 'Login', responses: { 200: { description: 'Logged in' } } },
			},
			'/logout': {
				post: { summary: 'Logout', responses: { 200: { description: 'Logged out' } } },
			},
		},
	});
});

app.use('*', authMiddleware);

app.use('*', async (c, next) => {
	c.set('articleService', new ArticleService(c.env.DB));
	c.set('projectService', new ProjectService(c.env.DB));
	await next();
});

app.get('/', (c) => {
	return c.json({
		status: 'ok',
		message: 'QBlog Hono API running',
		version: '1.0.0',
	});
});

app.get('/health', (c) => {
	return c.json({
		status: 'healthy',
		timestamp: new Date().toISOString(),
	});
});

app.route('/', authRoutes);
app.route('/', articleRoutes);
app.route('/', projectRoutes);

app.get('*', (c) => {
	return c.json({ status: 'error', error: 'Not found' }, 404);
});

app.onError((err, c) => {
	console.error('Error:', err);
	return c.json(
		{
			status: 'error',
			error: 'Internal server error',
			message: err.message,
		},
		500,
	);
});

export default app;
