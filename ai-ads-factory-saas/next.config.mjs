/** @type {import('next').NextConfig} */
const nextConfig = {
	serverExternalPackages: [
		"@remotion/bundler",
		"@remotion/renderer",
		"@remotion/cli",
		"@remotion/studio",
		"remotion"
	],
	turbopack: {
		root: process.cwd()
	}
};

export default nextConfig;