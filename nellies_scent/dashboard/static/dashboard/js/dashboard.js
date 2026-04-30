const themeToggle = document.getElementById('theme-toggle');
const themeIcon = themeToggle ? themeToggle.querySelector('.theme-icon') : null;

const getSavedTheme = () => {
    return localStorage.getItem('dashboardTheme') || getCookie('dashboardTheme') || 'pink';
};

const saveTheme = (theme) => {
    localStorage.setItem('dashboardTheme', theme);
    document.cookie = `dashboardTheme=${theme};path=/;max-age=${60*60*24*365}`;
};

const getCookie = (name) => {
    const cookieValue = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return cookieValue ? cookieValue.pop() : '';
};

const applyTheme = (theme) => {
    const body = document.body;
    body.classList.remove('theme-pink', 'theme-light', 'theme-dark');
    body.classList.add(`theme-${theme}`);
    if (themeIcon) {
        themeIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
    }
};

const toggleTheme = () => {
    const current = getSavedTheme();
    const next = current === 'pink' ? 'light' : current === 'light' ? 'dark' : 'pink';
    saveTheme(next);
    applyTheme(next);
};

if (themeToggle) {
    const initialTheme = getSavedTheme();
    applyTheme(initialTheme);
    themeToggle.addEventListener('click', toggleTheme);
}

window.addEventListener('DOMContentLoaded', () => {
    const initialTheme = getSavedTheme();
    applyTheme(initialTheme);
});
