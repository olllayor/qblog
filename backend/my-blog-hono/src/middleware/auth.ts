import { Context } from 'hono';
import { getCookie, setCookie } from 'hono/cookie';

export interface AuthContext {
	isAdmin: boolean;
	sessionId?: string;
}

function generateSessionId(): string {
	return Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
}

export async function createSession(c: Context): Promise<string> {
	const sessionId = generateSessionId();

	setCookie(c, 'session_id', sessionId, {
		maxAge: 24 * 60 * 60,
		httpOnly: true,
		secure: true,
		sameSite: 'Strict',
	});

	return sessionId;
}

export function destroySession(c: Context): void {
	setCookie(c, 'session_id', '', {
		maxAge: 0,
		httpOnly: true,
		secure: true,
		sameSite: 'Strict',
	});
}

export function isValidSession(c: Context): boolean {
	const sessionId = getCookie(c, 'session_id');
	return sessionId !== undefined && sessionId !== '';
}

export async function authenticateAdmin(c: Context, username: string, password: string): Promise<boolean> {
	const adminUsername = c.env?.ADMIN_USERNAME;
	const adminPassword = c.env?.ADMIN_PASSWORD;

	if (!adminUsername || !adminPassword) {
		console.error('Admin credentials not configured');
		return false;
	}

	return username === adminUsername && password === adminPassword;
}

export function authMiddleware(c: Context, next: () => Promise<void>): Promise<void> {
	const isAdmin = isValidSession(c);
	c.set('isAdmin', isAdmin);
	return next();
}

export function requireAuth(c: Context): boolean {
	const isAdmin = c.get('isAdmin');
	return isAdmin === true;
}
