// Legacy entry point — redirects to the new News Intelligence page.
// All logic is now inline in index.html, chat.html, and persona.html.
if (window.location.pathname.endsWith('main.js')) {
  window.location.href = 'index.html';
}
