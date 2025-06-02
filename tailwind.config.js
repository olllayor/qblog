/** @type {import('tailwindcss').Config} */
module.exports = {
	darkMode: 'class', // Use 'class' strategy for manual dark mode toggling
	content: ['./templates/**/*.html'], // Ensure Tailwind scans your templates
	theme: {
		extend: {},
	},
	plugins: [],
};
