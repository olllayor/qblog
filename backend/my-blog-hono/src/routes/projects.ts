import { Hono } from 'hono';
import { ProjectService } from '../db/projects';
import { requireAuth } from '../middleware/auth';
import { successResponse, errorResponse } from '../lib/utils';

export type ProjectRoutes = {
	Variables: {
		projectService: ProjectService;
	};
};

export const projectRoutes = new Hono<ProjectRoutes>();

projectRoutes.get('/api/projects', async (c) => {
	try {
		const projectService = c.get('projectService');
		const projects = await projectService.getAll();

		return successResponse(c, {
			projects: projects.map((p) => projectService.formatProjectResponse(p)),
		});
	} catch (error) {
		console.error('Error fetching projects:', error);
		return errorResponse(c, 'Failed to fetch projects');
	}
});

projectRoutes.get('/api/projects/:id', async (c) => {
	try {
		const id = parseInt(c.req.param('id'), 10);
		if (isNaN(id)) return c.notFound();

		const projectService = c.get('projectService');
		const project = await projectService.getById(id);

		if (!project) {
			return c.notFound();
		}

		return successResponse(c, projectService.formatProjectResponse(project));
	} catch (error) {
		console.error('Error fetching project:', error);
		return errorResponse(c, 'Failed to fetch project');
	}
});

projectRoutes.get('/api/admin/projects', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const projectService = c.get('projectService');
		const projects = await projectService.getAll();

		return successResponse(c, {
			projects: projects.map((p) => projectService.formatProjectResponse(p)),
		});
	} catch (error) {
		console.error('Error fetching projects:', error);
		return errorResponse(c, 'Failed to fetch projects');
	}
});

projectRoutes.post('/api/admin/projects', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const projectService = c.get('projectService');
		const body = await c.req.json<{
			title: string;
			description: string;
			imageUrl?: string;
			technologies?: string[];
			githubLink?: string;
			liveDemoLink?: string;
		}>();

		if (!body.title?.trim() || !body.description?.trim()) {
			return errorResponse(c, 'Title and description are required');
		}

		const project = await projectService.createProject(body.title, body.description, {
			imageUrl: body.imageUrl,
			technologies: body.technologies,
			githubLink: body.githubLink,
			liveDemoLink: body.liveDemoLink,
		});

		return c.json(
			{
				status: 'success',
				data: projectService.formatProjectResponse(project),
			},
			201,
		);
	} catch (error) {
		console.error('Error creating project:', error);
		return errorResponse(c, 'Failed to create project');
	}
});

projectRoutes.put('/api/admin/projects/:id', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const id = parseInt(c.req.param('id'), 10);
		if (isNaN(id)) return c.notFound();

		const projectService = c.get('projectService');
		const body = await c.req.json<{
			title?: string;
			description?: string;
			imageUrl?: string;
			technologies?: string[];
			githubLink?: string;
			liveDemoLink?: string;
		}>();

		const updated = await projectService.updateProject(id, {
			title: body.title,
			description: body.description,
			image_url: body.imageUrl,
			technologies: body.technologies?.join(','),
			github_link: body.githubLink,
			live_demo_link: body.liveDemoLink,
		});

		return successResponse(c, projectService.formatProjectResponse(updated));
	} catch (error) {
		console.error('Error updating project:', error);
		return errorResponse(c, 'Failed to update project');
	}
});

projectRoutes.delete('/api/admin/projects/:id', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	try {
		const id = parseInt(c.req.param('id'), 10);
		if (isNaN(id)) return c.notFound();

		const projectService = c.get('projectService');
		const success = await projectService.deleteById(id);

		if (!success) {
			return errorResponse(c, 'Project not found');
		}

		return successResponse(c, { id });
	} catch (error) {
		console.error('Error deleting project:', error);
		return errorResponse(c, 'Failed to delete project');
	}
});
