```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Journal — Personal Blog</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <a href="/" class="logo">Journal</a>
      <nav class="nav">
        <a href="#" class="nav-link">Essays</a>
        <a href="#" class="nav-link">Notes</a>
        <a href="#" class="nav-link">About</a>
      </nav>
    </header>

    <!-- Hero -->
    <section class="hero">
      <h1 class="hero-title">Thoughts on design,<br>technology & life.</h1>
      <p class="hero-subtitle">A collection of essays and observations on the things that matter.</p>
    </section>

    <!-- Articles -->
    <main class="articles" id="articles">
      <!-- Articles will be injected by JavaScript -->
    </main>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer-left">
        <span class="footer-logo">Journal</span>
        <span class="footer-copy">© 2025</span>
      </div>
      <div class="footer-right">
        <a href="#" class="footer-link">Twitter</a>
        <a href="#" class="footer-link">GitHub</a>
        <a href="#" class="footer-link">RSS</a>
      </div>
    </footer>
  </div>

  <script src="script.js"></script>
</body>
</html>
```

```css
/* styles.css */
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --color-bg: #faf9f7;
  --color-text: #1a1a1a;
  --color-text-muted: #6b6b6b;
  --color-accent: #c45d3a;
  --color-border: #e8e6e3;
  --font-serif: "Instrument Serif", Georgia, serif;
  --font-sans: "Inter", system-ui, sans-serif;
}

html {
  font-size: 16px;
  scroll-behavior: smooth;
}

body {
  font-family: var(--font-sans);
  background-color: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

.container {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Header */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px 0;
  border-bottom: 1px solid var(--color-border);
}

.logo {
  font-family: var(--font-serif);
  font-size: 1.5rem;
  color: var(--color-text);
  text-decoration: none;
  font-style: italic;
}

.nav {
  display: flex;
  gap: 32px;
}

.nav-link {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color 0.2s ease;
}

.nav-link:hover {
  color: var(--color-accent);
}

/* Hero */
.hero {
  padding: 80px 0 64px;
  border-bottom: 1px solid var(--color-border);
}

.hero-title {
  font-family: var(--font-serif);
  font-size: clamp(2.5rem, 6vw, 3.5rem);
  font-weight: 400;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin-bottom: 24px;
}

.hero-subtitle {
  font-size: 1.125rem;
  color: var(--color-text-muted);
  max-width: 480px;
}

/* Articles */
.articles {
  padding: 48px 0;
}

.article {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 24px;
  padding: 32px 0;
  border-bottom: 1px solid var(--color-border);
  text-decoration: none;
  color: inherit;
  transition: opacity 0.2s ease;
}

.article:first-child {
  padding-top: 0;
}

.article:hover {
  opacity: 1;
}

.article:hover .article-number {
  color: var(--color-accent);
}

.article:hover .article-title {
  color: var(--color-accent);
}

.article-number {
  font-family: var(--font-serif);
  font-size: 1rem;
  color: var(--color-text-muted);
  font-style: italic;
  transition: color 0.2s ease;
  padding-top: 4px;
}

.article-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.article-title {
  font-family: var(--font-serif);
  font-size: 1.75rem;
  font-weight: 400;
  line-height: 1.2;
  transition: color 0.2s ease;
}

.article-excerpt {
  font-size: 0.9375rem;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.article-meta {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.article-tag {
  padding: 4px 10px;
  background-color: var(--color-border);
  border-radius: 4px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Footer */
.footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px 0;
  margin-top: 48px;
  border-top: 1px solid var(--color-border);
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.footer-logo {
  font-family: var(--font-serif);
  font-style: italic;
  color: var(--color-text-muted);
}

.footer-copy {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}

.footer-right {
  display: flex;
  gap: 24px;
}

.footer-link {
  font-size: 0.875rem;
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color 0.2s ease;
}

.footer-link:hover {
  color: var(--color-accent);
}

/* Responsive */
@media (max-width: 640px) {
  .header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .nav {
    gap: 24px;
  }

  .hero {
    padding: 48px 0 40px;
    text-align: center;
  }

  .hero-subtitle {
    margin: 0 auto;
  }

  .article {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .article-number {
    font-size: 0.875rem;
  }

  .footer {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }
}
```

```javascript
// script.js
// Blog articles data
const articles = [
  {
    id: 1,
    title: "The Art of Slowing Down",
    excerpt:
      "In a world obsessed with speed, there's profound wisdom in doing less. Here's what I learned from a month of intentional slowness.",
    date: "Nov 20, 2025",
    readTime: "5 min read",
    tag: "Life",
  },
  {
    id: 2,
    title: "Designing for Emotion",
    excerpt:
      "Good design isn't just functional—it makes you feel something. A deep dive into the invisible layer of emotional design.",
    date: "Nov 12, 2025",
    readTime: "8 min read",
    tag: "Design",
  },
  {
    id: 3,
    title: "Tools Shape Thought",
    excerpt:
      "The software we use daily influences how we think. On the relationship between digital tools and creative cognition.",
    date: "Oct 28, 2025",
    readTime: "6 min read",
    tag: "Tech",
  },
  {
    id: 4,
    title: "Notes on Simplicity",
    excerpt:
      "Simplicity isn't the absence of complexity—it's the result of careful reduction. Reflections on minimalism in work and life.",
    date: "Oct 15, 2025",
    readTime: "4 min read",
    tag: "Essays",
  },
  {
    id: 5,
    title: "The Quiet Hours",
    excerpt:
      "Early mornings have become my sanctuary. On finding creativity in the stillness before the world wakes up.",
    date: "Sep 30, 2025",
    readTime: "3 min read",
    tag: "Life",
  },
]

// Render articles
function renderArticles() {
  const container = document.getElementById("articles")

  const articlesHTML = articles
    .map((article, index) => {
      const number = String(index + 1).padStart(2, "0")

      return `
      <a href="#" class="article">
        <span class="article-number">${number}</span>
        <div class="article-content">
          <h2 class="article-title">${article.title}</h2>
          <p class="article-excerpt">${article.excerpt}</p>
          <div class="article-meta">
            <span class="article-tag">${article.tag}</span>
            <span>${article.date}</span>
            <span>·</span>
            <span>${article.readTime}</span>
          </div>
        </div>
      </a>
    `
    })
    .join("")

  container.innerHTML = articlesHTML
}

// Initialize
document.addEventListener("DOMContentLoaded", renderArticles)
```