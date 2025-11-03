import { Context } from 'hono';

export interface ApiResponse<T = unknown> {
	status: 'success' | 'error';
	data?: T;
	message?: string;
	error?: string;
}

export function successResponse<T>(c: Context, data: T, message?: string) {
	return c.json<ApiResponse<T>>(
		{
			status: 'success',
			data,
			message,
		},
		200,
	);
}

export function errorResponse(c: Context, error: string, message?: string) {
	return c.json<ApiResponse>(
		{
			status: 'error',
			error,
			message,
		},
		400,
	);
}

export function getClientIp(c: Context): string {
	return (
		c.req.header('cf-connecting-ip') ||
		c.req.header('x-forwarded-for')?.split(',')[0] ||
		c.req.header('x-real-ip') ||
		'unknown'
	);
}

export function getQueryInt(c: Context, key: string, defaultValue: number): number {
	const value = c.req.query(key);
	if (!value) return defaultValue;
	const parsed = parseInt(value, 10);
	return isNaN(parsed) ? defaultValue : Math.max(1, parsed);
}

export function clamp(value: number, min: number, max: number): number {
	return Math.min(Math.max(value, min), max);
}
