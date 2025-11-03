import { Hono } from 'hono';
import { createSession, destroySession, authenticateAdmin, requireAuth } from '../middleware/auth';
import { successResponse, errorResponse } from '../lib/utils';

export const authRoutes = new Hono();

authRoutes.post('/login', async (c) => {
	try {
		const body = await c.req.json<{ username: string; password: string }>();

		if (!body.username || !body.password) {
			return errorResponse(c, 'Username and password are required');
		}

		const isValid = await authenticateAdmin(c, body.username, body.password);
		if (!isValid) {
			return c.json({ status: 'error', error: 'Invalid credentials' }, 401);
		}

		await createSession(c);
		return successResponse(c, { message: 'Login successful' });
	} catch (error) {
		console.error('Error during login:', error);
		return errorResponse(c, 'Failed to login');
	}
});

authRoutes.post('/logout', async (c) => {
	if (!requireAuth(c)) {
		return c.json({ status: 'error', error: 'Unauthorized' }, 401);
	}

	destroySession(c);
	return successResponse(c, { message: 'Logout successful' });
});

authRoutes.get('/auth/check', async (c) => {
	const isAdmin = requireAuth(c);
	return successResponse(c, { isAdmin });
});
