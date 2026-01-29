// Vercel serverless function wrapper for Express app
const app = require('../server');

// Export as Vercel serverless function handler
module.exports = (req, res) => {
    return app(req, res);
};
