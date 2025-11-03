#!/usr/bin/env bun
/**
 * Quick PostgreSQL Table Schema Inspector
 */

import postgres from 'postgres';

const POSTGRES_URL =
	process.env.POSTGRES_URL ||
	'postgres://neondb_owner:j5PUbYCFIkX9@ep-wild-tooth-a2wfnvmi-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require';

try {
	const sql = postgres(POSTGRES_URL);

	console.log('📋 Tables in database:');
	const tables = await sql`
    SELECT table_name FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
  `;

	console.log(
		'Tables:',
		tables.map((t) => t.table_name),
	);

	// Get actual columns from articles table
	console.log('\n📄 Articles table columns:');
	const articlesInfo = await sql`
    SELECT * FROM information_schema.columns
    WHERE table_name = 'articles'
    ORDER BY ordinal_position
  `;

	articlesInfo.forEach((col) => {
		console.log(`  ${col.column_name}: ${col.data_type}`);
	});

	// Sample data
	console.log('\n📝 First 2 articles:');
	const articles = await sql`SELECT * FROM articles LIMIT 2`;
	articles.forEach((a) => {
		console.log(JSON.stringify(a, null, 2));
	});

	await sql.end();
} catch (error) {
	console.error('❌ Error:', error instanceof Error ? error.message : error);
	process.exit(1);
}
