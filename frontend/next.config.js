/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
  // This is only for 'npm run dev' (port 3000)
  // It proxies /list_server_tags -> http://localhost:8000/list_server_tags
  /*
  async rewrites() {
    return [
      {
        source: '/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ]
  },
  */
}

module.exports = nextConfig
