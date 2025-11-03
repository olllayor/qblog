import { D1Database } from '@cloudflare/workers-types';
import { Project } from './schema';

export class ProjectService {
	constructor(private db: D1Database) {}

	async createProject(
		title: string,
		description: string,
		options?: {
			imageUrl?: string;
			technologies?: string[];
			githubLink?: string;
			liveDemoLink?: string;
		},
	): Promise<Project> {
		const technologiesStr = options?.technologies?.join(',') || '';
		const dateAdded = new Date().toISOString();

		const result = await this.db
			.prepare(
				`
        INSERT INTO projects (title, description, image_url, technologies, github_link, live_demo_link, date_added)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        RETURNING *
      `,
			)
			.bind(
				title,
				description,
				options?.imageUrl || null,
				technologiesStr,
				options?.githubLink || null,
				options?.liveDemoLink || null,
				dateAdded,
			)
			.first<Project>();

		if (!result) {
			throw new Error('Failed to create project');
		}

		return result;
	}

	async updateProject(id: number, updates: Partial<Omit<Project, 'id' | 'date_added'>>): Promise<Project> {
		const project = await this.getById(id);
		if (!project) {
			throw new Error('Project not found');
		}

		const title = updates.title ?? project.title;
		const description = updates.description ?? project.description;
		const imageUrl = updates.image_url ?? project.image_url;
		const technologies = updates.technologies ?? project.technologies;
		const githubLink = updates.github_link ?? project.github_link;
		const liveDemoLink = updates.live_demo_link ?? project.live_demo_link;

		const result = await this.db
			.prepare(
				`
        UPDATE projects
        SET title = ?, description = ?, image_url = ?, technologies = ?, github_link = ?, live_demo_link = ?
        WHERE id = ?
        RETURNING *
      `,
			)
			.bind(title, description, imageUrl || null, technologies || null, githubLink || null, liveDemoLink || null, id)
			.first<Project>();

		if (!result) {
			throw new Error('Failed to update project');
		}

		return result;
	}

	async getById(id: number): Promise<Project | null> {
		const result = await this.db.prepare('SELECT * FROM projects WHERE id = ?').bind(id).first<Project>();

		return result || null;
	}

	async getAll(): Promise<Project[]> {
		const result = await this.db.prepare('SELECT * FROM projects ORDER BY date_added DESC').all<Project>();

		return result.results || [];
	}

	async deleteById(id: number): Promise<boolean> {
		const result = await this.db.prepare('DELETE FROM projects WHERE id = ?').bind(id).run();

		return result.success;
	}

	formatProjectResponse(project: Project) {
		return {
			id: project.id,
			title: project.title,
			description: project.description,
			imageUrl: project.image_url,
			technologies: project.technologies ? project.technologies.split(',') : [],
			githubLink: project.github_link,
			liveDemoLink: project.live_demo_link,
			dateAdded: project.date_added,
		};
	}
}
