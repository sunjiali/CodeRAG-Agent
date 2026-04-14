// API路由模块
const http = require('http');
const url = require('url');

const HttpMethod = { GET: 'GET', POST: 'POST', PUT: 'PUT', DELETE: 'DELETE' };

class Router {
    constructor() {
        this.routes = [];
        this.middlewares = [];
    }
    
    get(path, handler) {
        this.routes.push({ method: HttpMethod.GET, path, handler });
        return this;
    }
    
    post(path, handler) {
        this.routes.push({ method: HttpMethod.POST, path, handler });
        return this;
    }
    
    use(middleware) {
        this.middlewares.push(middleware);
        return this;
    }
    
    match(method, pathname) {
        for (const route of this.routes) {
            if (route.method !== method) continue;
            const pattern = route.path.replace(/:(\w+)/g, '([^/]+)');
            const regex = new RegExp(`^${pattern}$`);
            const match = pathname.match(regex);
            if (match) {
                const params = {};
                const paramNames = route.path.match(/:(\w+)/g) || [];
                paramNames.forEach((name, i) => params[name.slice(1)] = match[i + 1]);
                return { handler: route.handler, params };
            }
        }
        return null;
    }
    
    async handleRequest(req, res) {
        const parsedUrl = url.parse(req.url, true);
        const pathname = parsedUrl.pathname;
        
        for (const mw of this.middlewares) {
            await mw(req, res);
        }
        
        const matched = this.match(req.method, pathname);
        if (!matched) {
            res.writeHead(404, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Not found' }));
            return;
        }
        
        try {
            await matched.handler(req, res, matched.params);
        } catch (error) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: error.message }));
        }
    }
}

// 示例
const router = new Router();
router.get('/api/users', async (req, res) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify([{ id: 1, name: 'Alice' }]));
});
router.get('/api/users/:id', async (req, res, params) => {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ id: params.id, name: 'Alice' }));
});

module.exports = { Router };
