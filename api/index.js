// Vercel serverless function wrapper for Express app
// Set VERCEL environment variable before requiring server
process.env.VERCEL = '1';
const app = require('../server');

// Export as Vercel serverless function handler
module.exports = (req, res) => {
    return app(req, res);
};
