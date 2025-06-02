
Back
all the cool stuff my astro MDX component can do: MDX blog features
February 27, 2025

6 min read

okay, so this isn’t really a blog—it’s a flex. haha! but i built these astro components for mdx blogs, and here’s everything it can do. if you’re writing here, check this out. let’s gooo.

feel free to use it for your own stuff! check it out here: github.com/devansh1401/meee

The Ultimate Blog Styling and Features Guide
This comprehensive guide documents all styling options, formatting features, and components available in my blog. Use it as a reference when writing new blog posts to ensure consistent, beautiful, and feature-rich content.

Embedding External Content
You can embed tweets, YouTube videos, and Vimeo videos directly in your Markdown using the astro-embed components

Tweet Embedding
Hey look! I can embed a tweet in Markdown!


Video Embedding
Vimeo and YouTube videos work too :-)

Play
Table of Contents
Basic Typography
Text Formatting
Lists
Links
Blockquotes
Code Formatting
Images
Tables
Special Components
Styling Customization
Basic Typography
The blog uses Geist Mono as its primary font for a clean, technical look.

Text and Paragraphs
Regular paragraphs have comfortable spacing and a max-width for optimal readability. The font size is set to 1.1rem with a line height of 1.7.

This is a second paragraph to demonstrate spacing between paragraphs. The bottom margin is set to 1.5rem, creating clear separation between content blocks while maintaining visual cohesion.

Headings
The blog supports all six levels of headings, with Geist Mono font and appropriate spacing.

H1 Heading (for titles)
H2 Heading (major sections)
H3 Heading (subsections)
H4 Heading (minor sections)
H5 Heading (rarely used)
H6 Heading (rarely used)
Text Formatting
Various text formatting options are available:

Bold text is created with double asterisks or double underscores.

Italic text is created with single asterisks or single underscores.

Strikethrough is created with double tildes.

Combined bold and italic formatting is also supported.

Lists
Unordered Lists
Unordered lists use disc markers and have appropriate indentation:

This is the first item in an unordered list
This is the second item in an unordered list
This is the third item with a link inside it
Ordered Lists
Ordered lists use decimal numbering:

First item in an ordered list
Second item in an ordered list
Third item with bold text inside it
Nested Lists
Lists can be nested for more complex hierarchies:

Main item 1
Sub-item 1.1
Sub-item 1.2
Sub-sub-item 1.2.1
Main item 2
Sub-item 2.1
Task Lists
 Completed task
 Incomplete task
 Another completed task with italic text
Links
Regular links have an indigo color (#818cf8) with underline.

Links with hover change to a lighter indigo (#a5b4fc) when hovered.

Internal Links
You can link to other sections within the same document.

Blockquotes
Blockquotes are styled with a left border and subtle background:

This is a blockquote. It has a left indigo border and a slightly darker background.

It can contain multiple paragraphs, lists, and other formatting.

Item 1
Item 2
Nested blockquotes are also supported:

Outer blockquote

Nested blockquote

Multiple lines

Back to the outer blockquote

Code Formatting
Inline Code
Inline code like const greeting = "Hello World"; is displayed with a dark background, yellowish text, and Geist Mono font.

Basic Code Blocks
Code blocks support syntax highlighting:

// This is a JavaScript code block
function greet(name) {
  return `Hello, ${name}!`
}

const message = greet("Developer")
console.log(message)

# This is a Python code block
def greet(name):
    return f"Hello, {name}!"

message = greet("Developer")
print(message)

/* This is a CSS code block */
.container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

Advanced Code Block Features
File Names
You can add a file name to your code block:

greeting.js
function greet(name) {
  return `Hello, ${name}!`
}

Line Numbers
You can display line numbers:

// Line 1
function greet(name) {
  // Line 3
  return `Hello, ${name}!`
}

Line Highlighting
You can highlight specific lines:

highlighted-lines.js
function greet(name) {
  // This line is highlighted
  const greeting = "Hello"
  return `${greeting}, ${name}!` // This line is also highlighted
}

You can also use special comments for highlighting:

function complexCalculation() {
  let result = 0
  // highlight-start
  for (let i = 0; i < 1000; i++) {
    result += calculateImportantValue(i)
  }
  // highlight-end
  return result
}

Word Highlighting
Highlight specific words or phrases:

function greet(name) {
  return `Hello, ${name}!`
}

Line Annotations
Add annotations to specific lines:

function process(data) {
  // [!code focus]
  const result = transform(data)

  if (!isValid(result)) {
    // [!code error]
    throw new Error("Invalid result")
  }

  // [!code warning]
  console.log("Data processed")

  return result
}

Diff Blocks
Show code changes:

function greet(name) {
  return "Hello " + name;
  return `Hello, ${name}!`;
}

Terminal Commands
For terminal commands, use the special terminal styling:

npm install astro-expressive-code cd my-project npm run dev

File Paths
For file paths, use the path styling:

/src/layouts/LayoutBlogPost.astro
Images
Images have rounded corners, a subtle border, and responsive sizing:

Example Image Description

HTML can be used for more control:

A smaller image
Tables
Tables have styled headers and borders:

Name	Type	Default	Description
size	string	’medium’	The size of the component
color	string	’primary’	The color scheme
enabled	boolean	true	Whether the feature is enabled
items	array	[]	Collection of items to display
Horizontal Rules
Horizontal rules create visual separation between sections:

They have a subtle gray color and good spacing above and below.

Special Components
Notes, Warnings, and Errors
The blog supports special callout components:

Note: This is a note callout. Use it for additional information or tips.

Warning: This is a warning callout. Use it to highlight potential issues.

Error: This is an error callout. Use it to highlight critical problems.

Styling Customization
Image Size Control
To control image sizes globally, you can adjust the CSS:

/* Make all images 90% of their container width */
.content img {
  max-width: 90%;
}

For per-image control, add utility classes:

/* Image size utility classes */
.content .img-small {
  max-width: 50%;
  display: block;
  margin-left: auto;
  margin-right: auto;
}

.content .img-medium {
  max-width: 75%;
  display: block;
  margin-left: auto;
  margin-right: auto;
}

.content .img-full {
  max-width: 100%;
}

Adjusting Zoom Level
To adjust the overall “zoom” level of your blog:

/* Content zoom - adjust font size to zoom in/out */
.content {
  /* Smaller values = zoomed out, larger = zoomed in */
  font-size: 1rem; /* Current: 1.1rem */
  line-height: 1.7;
  letter-spacing: -0.01em;
}

/* Adjust heading sizes proportionally */
.content h1 {
  font-size: 2rem;
}
.content h2 {
  font-size: 1.7rem;
}
.content h3 {
  font-size: 1.4rem;
}
.content h4 {
  font-size: 1.2rem;
}

Link Color Customization
To change link colors:

/* Normal link color */
.content a {
  color: #6366f1; /* Indigo-500 - current is #818cf8 (Indigo-400) */
}

/* Hover state */
.content a:hover {
  color: #a5b4fc; /* Indigo-300 */
}

Common color options:

Blue: #3b82f6 (primary), #60a5fa (hover)
Green: #10b981 (primary), #34d399 (hover)
Purple: #8b5cf6 (primary), #a78bfa (hover)
Pink: #ec4899 (primary), #f472b6 (hover)
Using CSS Variables
For easier customization, consider using CSS variables:

:root {
  --blog-font-size: 1.1rem;
  --blog-link-color: #818cf8;
  --blog-link-hover: #a5b4fc;
}

.content {
  font-size: var(--blog-font-size);
}

.content a {
  color: var(--blog-link-color);
}

.content a:hover {
  color: var(--blog-link-hover);
}

Conclusion
This guide covers all styling and formatting features available in the blog. Reference it whenever you’re writing new content to ensure consistent and attractive presentation.

Remember that you can combine all these features to create rich, interactive, and visually appealing blog posts that engage your readers.

Last updated: February 27, 2025

Thanks for reading! If you enjoyed this post, consider sharing it.