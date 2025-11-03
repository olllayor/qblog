# 🚀 Hono Backend - Getting Started Index

Welcome to your migrated Hono backend! This file helps you navigate the documentation and get started.

## 📖 Documentation Map

### 🎯 **Start Here** (Choose based on your needs)

**I want to get up and running immediately:**
→ Read: [`QUICK_REFERENCE.md`](./QUICK_REFERENCE.md) (5 min read)
- Commands cheat sheet
- Endpoint reference
- Common issues

**I want step-by-step instructions:**
→ Read: [`SETUP_COMPLETE.md`](./SETUP_COMPLETE.md) (20 min read)
- Detailed setup guide
- Database configuration
- Testing instructions
- Deployment steps

**I want to understand what was migrated:**
→ Read: [`MIGRATION_COMPLETE.md`](./MIGRATION_COMPLETE.md) (15 min read)
- Flask → Hono mapping
- Before/after comparison
- Architecture overview

**I want complete technical details:**
→ Read: [`MIGRATION_GUIDE.md`](./MIGRATION_GUIDE.md) (30 min read)
- Full API documentation
- Database schema
- Advanced configuration

**I want to know about the API:**
→ Read: [`README.md`](./README.md) (10 min read)
- API endpoints
- Response formats
- Security features

---

## ⚡ Quick Start (Copy & Paste)

```bash
cd backend/my-blog-hono

# 1. Install dependencies
bun install

# 2. Create environment file
cat > .env.local << 'ENV'
ADMIN_USERNAME=olloyor
ADMIN_PASSWORD=your_password
ENV

# 3. Create Cloudflare database
bun wrangler d1 create qblog

# 4. Update wrangler.jsonc with returned database ID

# 5. Run local dev server
bun run dev

# Visit http://localhost:8787 ✨
```

---

## 📁 File Organization

```
src/
├── index.ts                # Main app - routes & middleware setup
├── db/
│   ├── schema.ts          # Database schema & types
│   ├── articles.ts        # Article business logic
│   └── projects.ts        # Project business logic
├── middleware/
│   └── auth.ts            # Authentication & sessions
├── routes/
│   ├── auth.ts            # Login/logout endpoints
│   ├── articles.ts        # Article API endpoints
│   └── projects.ts        # Project API endpoints
└── lib/
    └── utils.ts           # Helper functions

Config:
├── package.json           # Dependencies (use bun!)
├── wrangler.jsonc         # Cloudflare Workers config
└── tsconfig.json          # TypeScript settings
```

---

## 🎯 Common Tasks

### Deploy to Cloudflare
```bash
bun run deploy
```

### Test Locally
```bash
bun run dev
# Visit http://localhost:8787
```

### Check Types
```bash
bun tsc --noEmit
```

### Build for Production
```bash
bun run build
```

### Generate Types
```bash
bun run cf-typegen
```

---

## 📊 API Overview

### Authentication Required
```
POST   /login                    Login
POST   /logout                   Logout
GET    /auth/check               Check auth status
```

### Articles (Public)
```
GET    /api/articles?page=1&per_page=6    List articles
GET    /blog/:slug                         Get single article
```

### Articles (Admin)
```
POST   /api/articles                      Create
PUT    /blog/:slug                        Update
DELETE /blog/:slug                        Delete
POST   /api/auto-save                     Auto-save draft
```

### Projects
```
GET    /projects                          List all
GET    /admin/projects                    Admin view
POST   /admin/projects                    Create
PUT    /admin/projects/:id                Update
DELETE /admin/projects/:id                Delete
```

---

## 🔧 Development Workflow

1. **Make changes** to TypeScript files
2. **Dev server auto-reloads** (bun run dev)
3. **Test in browser** or with curl
4. **Check types** (bun tsc --noEmit)
5. **Deploy** (bun run deploy)

---

## ⚙️ Configuration

### Environment Variables (.env.local)
```env
ADMIN_USERNAME=your_username
ADMIN_PASSWORD=your_password
```

### Cloudflare Settings (wrangler.jsonc)
- Update D1 database ID
- Update KV namespace IDs
- Set environment variables

---

## 🧪 Testing API

### Login
```bash
curl -X POST http://localhost:8787/login \
  -H "Content-Type: application/json" \
  -d '{"username":"olloyor","password":"password"}'
```

### Get Articles
```bash
curl http://localhost:8787/api/articles
```

### Create Article (after login)
```bash
curl -X POST http://localhost:8787/api/articles \
  -H "Content-Type: application/json" \
  -H "Cookie: session_id=YOUR_SESSION_ID" \
  -d '{"title":"Test","content":"<p>Content</p>","is_published":false}'
```

See [`QUICK_REFERENCE.md`](./QUICK_REFERENCE.md) for more examples.

---

## 📚 Database

### Create Database
```bash
bun wrangler d1 create qblog
```

### Schema
- **articles** - Blog articles with publish status
- **projects** - Portfolio projects  
- **article_views** - View tracking per IP

### Query Examples
```bash
# List articles
bun wrangler d1 execute qblog --local --command \
  "SELECT * FROM articles LIMIT 10"

# Count projects
bun wrangler d1 execute qblog --local --command \
  "SELECT COUNT(*) FROM projects"
```

---

## 🚀 Deployment Checklist

- [ ] Environment variables set
- [ ] D1 database created
- [ ] All tests pass locally
- [ ] No TypeScript errors
- [ ] Ready for production

Then:
```bash
bun run deploy
```

---

## 🆘 Need Help?

### Troubleshooting
- See [`QUICK_REFERENCE.md`](./QUICK_REFERENCE.md) - Troubleshooting section

### 401 Unauthorized
- Check username/password in `.env.local`
- Try login endpoint directly
- Verify cookies are stored

### 404 Not Found
- Check article slug exists
- Verify article is published
- Check route path is correct

### Database Errors
- Run `bun wrangler d1 list`
- Check database ID in `wrangler.jsonc`
- Verify D1 database was created

### "Module not found" Errors
- Run `bun install` again
- Clear node_modules: `rm -rf node_modules`
- Run `bun install` fresh

---

## 📖 Reading Order

For a complete understanding, read in this order:

1. **This file** (index) - 5 min
2. **QUICK_REFERENCE.md** - 10 min (commands & endpoints)
3. **SETUP_COMPLETE.md** - 20 min (how to deploy)
4. **MIGRATION_COMPLETE.md** - 15 min (what changed)
5. **README.md** - 10 min (API details)
6. **MIGRATION_GUIDE.md** - 30 min (complete reference)

**Total reading time: ~90 minutes** for full understanding

---

## 🎓 Key Concepts

### Routes
- Use `app.get()`, `app.post()`, etc.
- Parameters: `c.req.param('id')`
- Query strings: `c.req.query('page')`
- Body: `await c.req.json()`

### Database
- Use D1 (SQLite) instead of PostgreSQL
- Each service manages its table
- No connection pooling needed

### Authentication
- Cookie-based sessions
- HttpOnly, Secure flags
- Middleware validates all requests

### Response Format
```json
{
  "status": "success|error",
  "data": {...},
  "message": "optional"
}
```

---

## 🔐 Security

- ✅ Admin credentials from environment
- ✅ HttpOnly cookies prevent XSS
- ✅ Secure flag requires HTTPS
- ✅ SameSite=Strict prevents CSRF
- ⚠️ Consider adding rate limiting
- ⚠️ Add CORS for production

---

## 🌍 Deployment

### Local Development
```bash
bun run dev
```

### Production
```bash
bun run deploy
```

### With Environment
```bash
bun run deploy --env production
```

---

## 📝 Frontend Integration

Your frontend needs to:

1. **Call login endpoint** first
2. **Include credentials** (cookies) in requests
3. **Handle JSON responses**
4. **Render UI based on response data**

Example:
```javascript
// Login
await fetch('/login', {
  method: 'POST',
  credentials: 'include',
  body: JSON.stringify({...})
})

// Fetch articles
const res = await fetch('/api/articles');
const { status, data } = await res.json();
```

---

## ✨ What's Next

1. ✅ **Backend Migration** - DONE! You're reading the docs for it
2. ⏳ **Setup & Test** - Run locally (next)
3. ⏳ **Deploy** - Push to Cloudflare (soon)
4. ⏳ **Build Frontend** - Create UI (parallel)
5. ⏳ **Data Migration** - Move from PostgreSQL (ongoing)

---

## 💡 Pro Tips

1. Use **Bun** not npm
   ```bash
   bun install    # not: npm install
   bun run dev    # not: npm run dev
   ```

2. **Keep .env.local private**
   - Add to .gitignore
   - Never commit secrets

3. **Test before deploying**
   ```bash
   bun run dev
   bun tsc --noEmit
   ```

4. **Monitor production**
   - Check Cloudflare dashboard
   - View request metrics
   - Monitor error rates

5. **Update regularly**
   ```bash
   bun upgrade
   bun update
   ```

---

## 📞 Get Support

- **Hono Docs**: https://hono.dev
- **Cloudflare**: https://developers.cloudflare.com/workers
- **Bun**: https://bun.sh
- **TypeScript**: https://www.typescriptlang.org

---

## 🎯 Next Action

**→ Run this command:**
```bash
cd backend/my-blog-hono
bun install
```

**Then read:**
```bash
cat SETUP_COMPLETE.md
```

**Then deploy:**
```bash
bun run dev
```

---

**Happy coding! 🚀**
