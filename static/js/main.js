// static/js/main.js

document.addEventListener('DOMContentLoaded', function () {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        const sunIcon = themeToggle.querySelector('.theme-icon-sun');
        const moonIcon = themeToggle.querySelector('.theme-icon-moon');

        function updateIcons(theme) {
            if (theme === 'dark') {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'inline';
            } else {
                sunIcon.style.display = 'inline';
                moonIcon.style.display = 'none';
            }
        }

        const currentTheme = localStorage.getItem('theme') || 'light';
        updateIcons(currentTheme);

        themeToggle.addEventListener('click', function () {
            const theme = document.documentElement.getAttribute('data-theme');
            const newTheme = theme === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateIcons(newTheme);
        });
    }
});
