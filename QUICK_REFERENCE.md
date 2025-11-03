# Quick Reference - Frontend to Backend Integration

## 🚀 Start Here (5 minutes)

### 1. Start the Backend
```bash
cd backend/my-blog-hono
bun run dev
# Runs on http://localhost:8787
```

### 2. Verify Backend is Working
```bash
curl http://localhost:8787/
# Should return: {"status":"ok","message":"QBlog Hono API running",...}
```

### 3. Update Flask .env
```bash
echo "API_BASE_URL=http://localhost:8787" >> .env
```

### 4. Install Python Dependency
```bash
uv add requests
```

### 5. Update Flask App (Pick ONE option)

**Option A - Quick (Single import)**
```python
from api_client import api_client

@app.route('/blog')
def articles():
    result = api_client.get_articles()
    if result['status'] == 'success':
        return render_template('blog.html', articles=result['data']['articles'])
    return render_template('500.html'), 500
```

**Option B - Complete (All routes at once)**
```python
from hono_routes import register_hono_routes

# After Flask app creation
register_hono_routes(app)
```

### 6. Start Flask
```bash
python app.py
# or
uv run python app.py
```

### 7. Test It
- Open http://localhost:5000/blog
- Should see articles from Hono backend
- No errors in terminal = success! ✅

---

## 📚 Key Files Reference

| File | What It Does | Use When |
|------|-------------|----------|
| `api_client.py` | HTTP client for API | Always - import and use |
| `hono_routes.py` | Ready-made Flask routes | Want everything auto-configured |
| `HONO_INTEGRATION.md` | Setup instructions | Need step-by-step guide |
| `INTEGRATION_SUMMARY.md` | Overview | Understanding architecture |
| `FRONTEND_INTEGRATION.md` | API docs | Building custom routes |

---

## 🔑 Authentication

### Login Credentials
```
Username: olllayor
Password: olllayor2002
```

### How It Works
1. POST `/login` with credentials
2. Server sets `session_id` cookie (HttpOnly, 24hr expiry)
3. Cookie automatically sent with future requests
4. POST `/logout` to clear session

### In Python
```python
# Login
result = api_client.login('olllayor', 'olllayor2002')

# Make authenticated calls - cookies handled automatically
result = api_client.create_article('Title', '<p>Content</p>')

# Logout
api_client.logout()
```

### In JavaScript (if needed)
```javascript
// Include credentials in fetch
fetch('http://localhost:8787/login', {
    method: 'POST',
    credentials: 'include',  // Important!
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'olllayor',
        password: 'olllayor2002'
    })
});
```

---

## 🛣️ All API Endpoints

### READ (Public)
```
GET  /api/articles?page=1&per_page=6
GET  /blog/:slug
GET  /api/projects
GET  /api/projects/:id
```

### WRITE (Admin Only)
```
POST /login
POST /logout
GET  /auth/check
POST /api/articles
PUT  /blog/:slug
DELETE /blog/:slug
POST /api/auto-save
POST /api/admin/projects
PUT  /api/admin/projects/:id
DELETE /api/admin/projects/:id
```

---

## 💡 Common Tasks

### Display Articles
```python
result = api_client.get_articles(page=1, per_page=6)
articles = result['data']['articles']
```

### Display Single Article
```python
result = api_client.get_article_by_slug('my-article')
article = result['data']
```

### Create Article (Admin)
```python
result = api_client.create_article(
    title='My Article',
    content='<p>Content</p>',
    is_published=False
)
new_slug = result['data']['slug']
```

### Update Article (Admin)
```python
result = api_client.update_article(
    slug='my-article',
    title='Updated Title',
    is_published=True
)
```

### Delete Article (Admin)
```python
result = api_client.delete_article('my-article')
```

### Display Projects
```python
result = api_client.get_projects()
projects = result['data']['projects']
```

### Create Project (Admin)
```python
result = api_client.create_project(
    title='My Project',
    description='Cool project',
    image_url='https://...',
    technologies=['React', 'Node.js'],
    github_link='https://github.com/...'
)
```

### Auto-Save Draft
```python
result = api_client.auto_save(
    title='Draft Title',
    content='<p>Work in progress</p>',
    slug='optional-slug'  # Omit for new article
)
```

---

## 🧪 Testing Endpoints

### Test All Public Endpoints
```bash
# List articles
curl http://localhost:8787/api/articles

# Single article (replace slug)
curl http://localhost:8787/blog/my-article

# List projects
curl http://localhost:8787/api/projects

# Single project
curl http://localhost:8787/api/projects/1
```

### Test Admin Endpoints
```bash
# Login
curl -X POST http://localhost:8787/login \
  -H "Content-Type: application/json" \
  -d '{"username":"olllayor","password":"olllayor2002"}'

# Check auth (with cookie from login)
curl -X GET http://localhost:8787/auth/check

# Create article (with cookie)
curl -X POST http://localhost:8787/api/articles \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","content":"<p>Test</p>","is_published":false}'
```

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Kill existing processes
pkill -9 -f "wrangler"

# Clear local state
rm -rf .wrangler

# Try again
bun run dev
```

### Connection refused (can't reach backend)
```bash
# Check if running
ps aux | grep wrangler

# Check port
lsof -i :8787

# Verify URL in .env
echo $API_BASE_URL
```

### 401 Unauthorized
```python
# Make sure you logged in first
api_client.login('olllayor', 'olllayor2002')

# Then try the admin call
api_client.create_article(...)
```

### 404 Not Found
```python
# Check article exists and is published
result = api_client.get_article_by_slug('my-slug')
# If 404, either slug is wrong or article not published
```

### CORS Error in browser
```typescript
// Add to src/index.ts in Hono backend
import { cors } from 'hono/cors';

app.use('*', cors({
  origin: 'http://localhost:5000',
  credentials: true
}));
```

---

## 📋 Response Format

Every endpoint returns:
```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": "message if failed"
}
```

Always check status:
```python
if result['status'] == 'success':
    data = result['data']
    # Use data
else:
    error = result['error']
    # Handle error
```

---

## 🔗 Useful Links

- Backend running: http://localhost:8787
- Swagger docs: http://localhost:8787/docs
- Flask app: http://localhost:5000
- API docs: `/backend/my-blog-hono/FRONTEND_INTEGRATION.md`

---

## 📱 Example Flask Route

```python
from flask import render_template
from api_client import api_client

@app.route('/blog')
def blog_index():
    """Display blog articles"""
    page = request.args.get('page', 1, type=int)
    
    # Get articles from Hono backend
    result = api_client.get_articles(page=page, per_page=6)
    
    # Check if successful
    if result['status'] != 'success':
        return render_template('500.html'), 500
    
    # Extract data
    data = result['data']
    articles = data['articles']
    has_more = data['has_more']
    
    # Render template
    return render_template(
        'blog.html',
        articles=articles,
        current_page=page,
        has_more=has_more
    )
```

---

## ⚡ Performance Tips

1. **Cache frequently accessed articles** (Redis or memcached)
2. **Lazy load images** in article lists
3. **Use pagination** (6 articles per page)
4. **Compress responses** (gzip)
5. **Monitor response times** - log slow queries

---

## 🔐 Security Checklist

- [ ] Use HTTPS in production
- [ ] Set secure cookie flags (done by Hono)
- [ ] Validate all input server-side
- [ ] Use environment variables for secrets
- [ ] Enable CORS only for trusted domains
- [ ] Rate limit admin endpoints

---

## 🚢 Deployment

### Backend (Cloudflare)
```bash
cd backend/my-blog-hono
bun run deploy
```

### Frontend (Your Hosting)
```bash
# Update .env
API_BASE_URL=https://api.yourdomain.com

# Deploy as normal
# (instructions depend on your host)
```

---

## 📞 Need Help?

1. Read the full docs: `HONO_INTEGRATION.md`
2. Check API reference: `FRONTEND_INTEGRATION.md`
3. Review examples: `hono_routes.py`
4. Test with curl (troubleshooting section)
5. Check terminal logs for error messages

**Happy coding! 🎉**
