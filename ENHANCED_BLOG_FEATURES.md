# Enhanced Blog Features Guide

This guide covers all the new MDX-inspired styling features added to your Flask blog.

## 🎨 Enhanced Typography

The blog now uses improved typography with better spacing and readability:

- **Fonts**: Geist Mono for headings, JetBrains Mono for code
- **Enhanced line spacing** for better readability
- **Improved heading hierarchy** with better visual distinction
- **Optimized paragraph spacing** for comfortable reading

## 📊 Article Metadata

Each article now displays enhanced metadata:

- **Reading time calculation** (based on 225 words per minute)
- **Word count display**
- **Publication date** with improved formatting
- **Responsive metadata layout**

## 💻 Code Blocks with Filenames

Create code blocks with filename headers for better context:

```html
<div class="code-block-with-filename">
	<div class="code-filename">filename.py</div>
	<pre><code>
    # Your code here
    def example_function():
        return "Hello World"
    </code></pre>
</div>
```

## 🔔 Callout Components

Three types of callouts for different purposes:

### Note Callout

```html
<div class="callout callout-note">
	<div class="callout-title">Note</div>
	<p>Important information that's good to know.</p>
</div>
```

### Warning Callout

```html
<div class="callout callout-warning">
	<div class="callout-title">Warning</div>
	<p>Something to be careful about.</p>
</div>
```

### Error Callout

```html
<div class="callout callout-error">
	<div class="callout-title">Error</div>
	<p>Critical information or errors to avoid.</p>
</div>
```

## 💻 Terminal Styling

For command-line examples:

```html
<div class="terminal-block">uv add package_name</div>
```

This creates a terminal-styled block with proper coloring and the `$` prompt.

## 📝 Task Lists

Interactive-looking task lists:

```html
<div class="task-list">
	<div class="task-list-item"><input type="checkbox" checked disabled /> Completed task</div>
	<div class="task-list-item"><input type="checkbox" disabled /> Pending task</div>
</div>
```

## 🖼️ Image Utilities

Control image sizes with utility classes:

- `.img-small` - 50% width
- `.img-medium` - 75% width
- `.img-full` - 100% width (default)

```html
<img src="image.jpg" alt="Description" class="img-medium" />
```

## 📋 Enhanced Tables

Tables now have better styling with:

- Rounded corners
- Proper borders
- Header highlighting
- Responsive design

## 🎯 Best Practices

1. **Use semantic HTML** - The styles work best with proper HTML structure
2. **Add alt text** to images for accessibility
3. **Use callouts sparingly** - They're most effective when used for truly important information
4. **Include filenames** on code blocks when relevant
5. **Test in both light and dark modes**

## 🌗 Dark Mode Support

All enhanced features automatically adapt to dark mode:

- Color schemes adjust automatically
- Proper contrast maintained
- Consistent visual hierarchy

## 📱 Responsive Design

All features are mobile-friendly:

- Tables scroll horizontally on small screens
- Code blocks have proper overflow handling
- Callouts stack properly on mobile
- Metadata adjusts for small screens

## 🚀 Article Enhancement Methods

The Article class now includes helpful methods:

- `get_reading_time()` - Calculate reading time in minutes
- `get_word_count()` - Get total word count
- `get_summary(length)` - Generate article summary

These are automatically used in the blog listing and article pages.

## 📈 Performance Considerations

- Styles are optimized and minified
- CSS variables used for consistent theming
- Mobile-first responsive design
- Efficient dark mode implementation

Start using these features in your blog posts to create more engaging and professional content!
