#!/usr/bin/env bun
/**
 * PostgreSQL Schema Inspector
 * Inspects the PostgreSQL database schema to understand data types
 */

import postgres from 'postgres';

const POSTGRES_URL =
	process.env.POSTGRES_URL ||
	'postgres://neondb_owner:j5PUbYCFIkX9@ep-wild-tooth-a2wfnvmi-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require';

console.log('🔍 Inspecting PostgreSQL database schema...\n');

try {
	const sql = postgres(POSTGRES_URL);

	// Get table information
	const tables = await sql`
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY table_name
  `;

	console.log('📋 Tables found:', tables.map((t) => t.table_name).join(', '));
	console.log('');

	// Inspect articles table
	console.log('📄 ARTICLES table schema:');
	const articlesColumns = await sql`
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'articles'
    ORDER BY ordinal_position
  `;

	articlesColumns.forEach((col) => {
		console.log(
			`  ${col.column_name}: ${col.data_type} (nullable: ${col.is_nullable}, default: ${col.column_default})`,
		);
	});

	// Sample article to see what kind of data is there
	console.log('\n📝 Sample article:');
	const sampleArticles = await sql`SELECT * FROM articles LIMIT 3`;
	console.log(JSON.stringify(sampleArticles, null, 2));

	// Check for problematic articles
	console.log('\n🔎 Checking article data types:');
	const articleCheck = await sql`
    SELECT 
      id,
      title,
      content,
      date_published,
      date_updated,
      is_published,
      slug,
      typeof(is_published) as bool_type
    FROM articles 
    LIMIT 5
  `;
	console.log(JSON.stringify(articleCheck, null, 2));

	// Inspect projects table
	console.log('\n🎯 PROJECTS table schema:');
	const projectsColumns = await sql`
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'projects'
    ORDER BY ordinal_position
  `;

	projectsColumns.forEach((col) => {
		console.log(
			`  ${col.column_name}: ${col.data_type} (nullable: ${col.is_nullable}, default: ${col.column_default})`,
		);
	});

	// Sample project
	console.log('\n🎯 Sample projects:');
	const sampleProjects = await sql`SELECT * FROM projects LIMIT 2`;
	console.log(JSON.stringify(sampleProjects, null, 2));

	// Inspect article_views table
	console.log('\n👁️  ARTICLE_VIEWS table schema:');
	const viewsColumns = await sql`
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'article_views'
    ORDER BY ordinal_position
  `;

	viewsColumns.forEach((col) => {
		console.log(
			`  ${col.column_name}: ${col.data_type} (nullable: ${col.is_nullable}, default: ${col.column_default})`,
		);
	});

	// Sample views
	console.log('\n👁️  Sample article views:');
	const sampleViews = await sql`SELECT * FROM article_views LIMIT 3`;
	console.log(JSON.stringify(sampleViews, null, 2));

	// Get total counts
	console.log('\n📊 Data Statistics:');
	const counts = await sql`
    SELECT 
      (SELECT COUNT(*) FROM articles) as article_count,
      (SELECT COUNT(*) FROM projects) as project_count,
      (SELECT COUNT(*) FROM article_views) as view_count
  `;
	console.log(JSON.stringify(counts[0], null, 2));

	await sql.end();
	console.log('\n✅ Schema inspection completed');
} catch (error) {
	console.error('❌ Error:', error instanceof Error ? error.message : error);
	process.exit(1);
}
