/** @type {import('next').NextConfig} */
const nextConfig = {
  // Permite que GHL embeba esta app en un iframe.
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "Content-Security-Policy", value: "frame-ancestors 'self' https://*.gohighlevel.com https://*.leadconnectorhq.com" },
        ],
      },
    ];
  },
};

export default nextConfig;
