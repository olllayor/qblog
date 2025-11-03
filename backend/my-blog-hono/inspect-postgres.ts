import postgres from 'postgres';
import { config } from 'dotenv';

config({ path: '.dev.vars' });

const sql = postgres(process.env.POSTGRES_URL || '');

async function inspectSchema() {
	try {
		console.log('Connecting to PostgreSQL...');

		// Get articles table info
		const articlesInfo = await sql`
      SELECT column_name, data_type, is_nullable
      FROM information_schema.columns
      WHERE table_name = 'articles'
      ORDER BY ordinal_position;
    `;

		console.log('\n📋 Articles table columns:');
		console.log('================================');
		for (const col of articlesInfo) {
			console.log(`  - ${col.column_name}: ${col.data_type} (nullable: ${col.is_nullable})`);
		}

		// Check for sample data
		const sampleArticles = await sql`
      SELECT * FROM articles LIMIT 2;
    `;

		console.log('\n📊 Sample articles:');
		console.log('================================');
		if (sampleArticles.length > 0) {
			console.log(JSON.stringify(sampleArticles[0], null, 2));
		} else {
			console.log('No articles found');
		}

		console.log('\n✅ Schema inspection complete');
	} catch (error) {
		console.error('Error:', error);
	} finally {
		await sql.end();
	}
}

inspectSchema();
