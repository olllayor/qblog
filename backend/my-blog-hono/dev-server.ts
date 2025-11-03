import { serve } from 'bun';
import { Database } from 'bun:sqlite';
import app from './src/index';
import { readFileSync } from 'fs';
import { join } from 'path';

// Setup local SQLite database using Bun's built-in SQLite
const dbPath = join(import.meta.dir, '.wrangler', 'state', 'v3', 'd1', 'miniflare-D1DatabaseObject', 'db.sqlite');
const db = new Database(dbPath);

// Initialize database schema if needed
try {
	const schemaPath = join(import.meta.dir, 'src', 'db', 'schema.sql');
	const schema = readFileSync(schemaPath, 'utf-8');
	db.exec(schema);
	console.log('✅ Database schema initialized');
} catch (error) {
	console.log('ℹ️  Database already initialized or schema file not found');
}

// Create D1-compatible wrapper
const d1Wrapper = {
	prepare(query: string) {
		return {
			bind(...values: any[]) {
				const stmt = db.prepare(query);
				return {
					async all() {
						const results = stmt.all(...values);
						return { results, success: true };
					},
					async first() {
						return stmt.get(...values);
					},
					async run() {
						const info = stmt.run(...values);
						return {
							success: true,
							meta: {
								changes: info.changes,
								last_row_id: info.lastInsertRowid,
							},
						};
					},
				};
			},
			async all() {
				const stmt = db.prepare(query);
				const results = stmt.all();
				return { results, success: true };
			},
			async first() {
				const stmt = db.prepare(query);
				return stmt.get();
			},
			async run() {
				const stmt = db.prepare(query);
				const info = stmt.run();
				return {
					success: true,
					meta: {
						changes: info.changes,
						last_row_id: info.lastInsertRowid,
					},
				};
			},
		};
	},
	async batch(statements: any[]) {
		const transaction = db.transaction(() => {
			statements.forEach((stmt) => stmt.run());
		});
		transaction();
		return [];
	},
	async exec(query: string) {
		db.exec(query);
		return { count: 0, duration: 0 };
	},
};

// Mock Cloudflare environment for local development
const mockEnv = {
	DB: d1Wrapper as any,
	ADMIN_USERNAME: process.env.ADMIN_USERNAME || 'olllayor',
	ADMIN_PASSWORD: process.env.ADMIN_PASSWORD || 'olllayor2002',
};

console.log('🚀 Starting development server...');
console.log('📁 Database path:', dbPath);

serve({
	port: 8787,
	fetch: (req) => {
		return app.fetch(req, mockEnv);
	},
});

console.log('✅ Server running at http://localhost:8787');
