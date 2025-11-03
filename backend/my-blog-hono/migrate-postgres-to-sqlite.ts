#!/usr/bin/env bun
/**
 * PostgreSQL to SQLite Migration Script
 * Migrates data from Neon.tech PostgreSQL to local SQLite database
 *
 * Usage: bun migrate-postgres-to-sqlite.ts
 */

import { Database } from 'bun:sqlite';
import { join } from 'path';
import postgres from 'postgres';

// Configuration
const POSTGRES_URL =
	process.env.POSTGRES_URL ||
	'postgres://neondb_owner:j5PUbYCFIkX9@ep-wild-tooth-a2wfnvmi-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require';
const SQLITE_PATH = join(import.meta.dir, '.wrangler', 'state', 'v3', 'd1', 'miniflare-D1DatabaseObject', 'db.sqlite');

console.log('🚀 Starting PostgreSQL to SQLite migration...\n');
console.log('📊 Source: Neon.tech PostgreSQL');
console.log('📁 Target:', SQLITE_PATH);
console.log('');

try {
	// Connect to PostgreSQL
	console.log('🔗 Connecting to PostgreSQL...');
	const sql = postgres(POSTGRES_URL);

	// Connect to SQLite
	console.log('📂 Initializing SQLite database...');
	const sqlite = new Database(SQLITE_PATH);

	// Enable foreign keys
	sqlite.exec('PRAGMA foreign_keys = ON');

	// Create tables
	console.log('🏗️  Creating tables...');
	sqlite.exec(`
    CREATE TABLE IF NOT EXISTS articles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      date_published DATETIME NOT NULL,
      is_published BOOLEAN NOT NULL DEFAULT FALSE,
      slug TEXT UNIQUE NOT NULL
    )
  `);

	sqlite.exec(`
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
  `);

	sqlite.exec(`
    CREATE TABLE IF NOT EXISTS article_views (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      article_slug TEXT NOT NULL,
      ip_address TEXT NOT NULL,
      user_agent TEXT,
      viewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(article_slug, ip_address)
    )
  `);

	// Create indexes
	sqlite.exec(`
    CREATE INDEX IF NOT EXISTS idx_articles_published_date 
    ON articles (is_published, date_published DESC)
  `);

	sqlite.exec(`
    CREATE INDEX IF NOT EXISTS idx_article_views_slug 
    ON article_views (article_slug)
  `);

	// Migrate articles
	console.log('\n📄 Migrating articles...');
	const articles = await sql`SELECT * FROM articles`;
	console.log(`   Found ${articles.length} articles`);

	if (articles.length > 0) {
		const insertArticle = sqlite.prepare(`
      INSERT INTO articles (id, title, content, date_published, is_published, slug)
      VALUES (?, ?, ?, ?, ?, ?)
    `);

		let insertedCount = 0;
		for (const article of articles) {
			try {
				const id = Number(article.id);
				const title = String(article.title || '');
				const content = String(article.content || '');
				const datePublished = String(article.date_published || '');
				const isPublished = Boolean(article.is_published) ? 1 : 0;
				const slug = String(article.slug || '');

				insertArticle.run(id, title, content, datePublished, isPublished, slug);
				insertedCount++;
			} catch (error) {
				console.error(`   ⚠️  Error inserting article ${article.id}:`, error instanceof Error ? error.message : error);
			}
		}
		console.log(`   ✅ Inserted ${insertedCount}/${articles.length} articles`);
	}

	// Migrate projects
	console.log('\n🎯 Migrating projects...');
	const projects = await sql`SELECT * FROM projects`;
	console.log(`   Found ${projects.length} projects`);

	if (projects.length > 0) {
		const insertProject = sqlite.prepare(`
      INSERT INTO projects (id, title, description, image_url, technologies, github_link, live_demo_link, date_added)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);

		let insertedCount = 0;
		for (const project of projects) {
			try {
				const id = Number(project.id);
				const title = String(project.title || '');
				const description = String(project.description || '');
				const imageUrl = project.image_url ? String(project.image_url) : null;
				const technologies = project.technologies ? String(project.technologies) : null;
				const githubLink = project.github_link ? String(project.github_link) : null;
				const liveDemoLink = project.live_demo_link ? String(project.live_demo_link) : null;
				const dateAdded = String(project.date_added || '');

				insertProject.run(id, title, description, imageUrl, technologies, githubLink, liveDemoLink, dateAdded);
				insertedCount++;
			} catch (error) {
				console.error(`   ⚠️  Error inserting project ${project.id}:`, error instanceof Error ? error.message : error);
			}
		}
		console.log(`   ✅ Inserted ${insertedCount}/${projects.length} projects`);
	}

	// Migrate article views
	console.log('\n👁️  Migrating article views...');
	const views = await sql`SELECT * FROM article_views`;
	console.log(`   Found ${views.length} article views`);

	if (views.length > 0) {
		const insertView = sqlite.prepare(`
      INSERT INTO article_views (id, article_slug, ip_address, user_agent, viewed_at)
      VALUES (?, ?, ?, ?, ?)
    `);

		let insertedCount = 0;
		for (const view of views) {
			try {
				const id = Number(view.id);
				const articleSlug = String(view.article_slug || '');
				const ipAddress = String(view.ip_address || '');
				const userAgent = view.user_agent ? String(view.user_agent) : null;
				const viewedAt = String(view.viewed_at || '');

				insertView.run(id, articleSlug, ipAddress, userAgent, viewedAt);
				insertedCount++;
			} catch (error) {
				console.error(`   ⚠️  Error inserting view ${view.id}:`, error instanceof Error ? error.message : error);
			}
		}
		console.log(`   ✅ Inserted ${insertedCount}/${views.length} article views`);
	}

	// Verify migration
	console.log('\n📋 Verification:');
	const articleCount = sqlite.prepare('SELECT COUNT(*) as count FROM articles').get() as { count: number };
	const projectCount = sqlite.prepare('SELECT COUNT(*) as count FROM projects').get() as { count: number };
	const viewCount = sqlite.prepare('SELECT COUNT(*) as count FROM article_views').get() as { count: number };

	console.log(`   Articles: ${articleCount.count}`);
	console.log(`   Projects: ${projectCount.count}`);
	console.log(`   Article Views: ${viewCount.count}`);

	// Close connections
	sqlite.close();
	await sql.end();

	console.log('\n✅ Migration completed successfully!');
	console.log('\n💡 Next steps:');
	console.log('   1. Review the migrated data in your SQLite database');
	console.log('   2. Run: bun run dev');
	console.log('   3. Test your API endpoints');
	console.log('\n📖 For more info, see DEV_SERVER_SETUP.md');

	process.exit(0);
} catch (error) {
	console.error('\n❌ Migration failed:', error instanceof Error ? error.message : error);
	if (error instanceof Error && error.stack) {
		console.error('\nStack trace:', error.stack);
	}
	process.exit(1);
}
