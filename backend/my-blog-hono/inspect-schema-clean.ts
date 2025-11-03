#!/usr/bin/env bun
/**
 * Clean schema inspection - shows actual PostgreSQL columns
 */

import postgres from 'postgres';
import { config } from 'dotenv';

config({ path: '.dev.vars' });
const sql = postgres(process.env.POSTGRES_URL || '');

try {
	console.log('📊 PostgreSQL Schema Inspection\n');

	// Get articles columns
	console.log('📄 ARTICLES table columns:');
	const articlesColumns = await sql`
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'articles'
    ORDER BY ordinal_position;
  `;
	console.table(articlesColumns);

	// Get projects columns
	console.log('\n🎯 PROJECTS table columns:');
	const projectsColumns = await sql`
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'projects'
    ORDER BY ordinal_position;
  `;
	console.table(projectsColumns);

	// Get article_views columns
	console.log('\n👁️  ARTICLE_VIEWS table columns:');
	const viewsColumns = await sql`
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'article_views'
    ORDER BY ordinal_position;
  `;
	console.table(viewsColumns);

	// Get row counts
	console.log('\n📈 Row counts:');
	const [{ count: articleCount }, { count: projectCount }, { count: viewCount }] = await Promise.all([
		sql`SELECT COUNT(*) as count FROM articles`,
		sql`SELECT COUNT(*) as count FROM projects`,
		sql`SELECT COUNT(*) as count FROM article_views`,
	]);

	console.log(`   Articles: ${articleCount}`);
	console.log(`   Projects: ${projectCount}`);
	console.log(`   Article Views: ${viewCount}`);

	// Sample article
	console.log('\n📋 Sample article:');
	const [sample] = await sql`SELECT * FROM articles LIMIT 1`;
	if (sample) {
		console.log(JSON.stringify(sample, null, 2));
	}

	await sql.end();
} catch (error) {
	console.error('❌ Error:', error instanceof Error ? error.message : error);
	process.exit(1);
}
