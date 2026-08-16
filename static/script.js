function toggleTheme() {
  const body = document.body;
  const button = document.getElementById('theme-toggle');
  
  body.classList.toggle('dark-mode');
  
  if (body.classList.contains('dark-mode')) {
    localStorage.setItem('theme', 'dark');
    if (button) button.textContent = '☀️ Light Mode';
  } else {
    localStorage.setItem('theme', 'light');
    if (button) button.textContent = '🌙 Dark Mode';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const savedTheme = localStorage.getItem('theme');
  const button = document.getElementById('theme-toggle');
  
  if (savedTheme === 'dark') {
    document.body.classList.add('dark-mode');
    if (button) button.textContent = '☀️ Light Mode';
  }
});