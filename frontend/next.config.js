/** @type {import('next').NextConfig} */
const nextConfig = {
  output: process.env.NODE_ENV === 'development' ? undefined : 'export',
  images: {
    unoptimized: true,
  },
  async rewrites() {
    if (process.env.NODE_ENV === 'development') {
        return [
        {
            source: '/:path*',
            destination: 'http://localhost:8000/:path*',
        },
        ]
    }
    return []
  },
}

module.exports = nextConfig
