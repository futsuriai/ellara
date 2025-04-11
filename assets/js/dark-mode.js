document.addEventListener('DOMContentLoaded', function() {
  // Check if dark mode is already enabled
  const isDarkMode = true; // This matches your _config.yml setting
  
  // Add a toggle button to the header
  const header = document.querySelector('.site-header');
  if (header) {
    const toggle = document.createElement('button');
    toggle.innerHTML = '☀️';
    toggle.className = 'theme-toggle';
    toggle.setAttribute('title', 'Toggle light/dark mode');
    toggle.style.cssText = 'background:none;border:none;font-size:1.5rem;cursor:pointer;margin-left:1rem;position:absolute;right:1rem;top:1rem;';
    
    toggle.addEventListener('click', function() {
      document.body.classList.toggle('light-mode');
      if (document.body.classList.contains('light-mode')) {
        toggle.innerHTML = '🌙';  
        localStorage.setItem('theme', 'light');
      } else {
        toggle.innerHTML = '☀️';
        localStorage.setItem('theme', 'dark');
      }
    });
    
    // Check if user previously selected a theme preference
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
      document.body.classList.add('light-mode');
      toggle.innerHTML = '🌙';
    }
    
    header.appendChild(toggle);
  }
});