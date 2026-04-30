/* ========================================
   ADMIN DASHBOARD JAVASCRIPT
   Theme Switching, Sidebar Toggle, Analytics
   ======================================== */

document.addEventListener('DOMContentLoaded', function() {
    initializeThemeSwitcher();
    initializeSidebarToggle();
    initializeSearchFunctionality();
});

// ============ THEME SWITCHER ============
function initializeThemeSwitcher() {
    const themeSwitcher = document.getElementById('themeSwitcher');
    const body = document.querySelector('.admin-body');
    
    if (!themeSwitcher) return;
    
    // Load saved theme from localStorage
    const savedTheme = localStorage.getItem('adminTheme') || 'pink-theme';
    setTheme(savedTheme);
    
    // Theme buttons
    const themeButtons = themeSwitcher.querySelectorAll('.theme-btn');
    themeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.getAttribute('data-theme');
            setTheme(theme);
        });
    });
    
    function setTheme(theme) {
        // Update body data attribute
        body.setAttribute('data-theme', theme);
        
        // Update active button
        const activeBtn = themeSwitcher.querySelector('[data-theme="' + theme + '"]');
        themeButtons.forEach(btn => btn.classList.remove('active'));
        if (activeBtn) activeBtn.classList.add('active');
        
        // Save to localStorage
        localStorage.setItem('adminTheme', theme);
        
        // Apply theme styles
        applyThemeStyles(theme);
    }
    
    function applyThemeStyles(theme) {
        // Theme-specific colors
        const themes = {
            'pink-theme': {
                primary: '#ec3b7f',
                accent: '#f5a3c3'
            },
            'light-theme': {
                primary: '#006dd8',
                accent: '#4da3ff'
            },
            'dark-theme': {
                primary: '#ff5fa3',
                accent: '#ff8fc9'
            }
        };
        
        const themeColors = themes[theme] || themes['pink-theme'];
        
        // Update CSS variables (optional - can be done via data attribute)
        document.documentElement.style.setProperty('--theme-primary', themeColors.primary);
        document.documentElement.style.setProperty('--theme-accent', themeColors.accent);
    }
}

// ============ SIDEBAR TOGGLE ============
function initializeSidebarToggle() {
    const toggleBtn = document.querySelector('.sidebar-toggle');
    const sidebar = document.querySelector('.admin-sidebar');
    
    if (!toggleBtn || !sidebar) return;
    
    toggleBtn.addEventListener('click', function() {
        sidebar.classList.toggle('active');
    });
    
    // Close sidebar when a link is clicked (mobile)
    const navLinks = sidebar.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
            }
        });
    });
    
    // Close sidebar when clicking outside (mobile)
    document.addEventListener('click', function(event) {
        if (window.innerWidth <= 768) {
            if (!sidebar.contains(event.target) && !toggleBtn.contains(event.target)) {
                sidebar.classList.remove('active');
            }
        }
    });
}

// ============ SEARCH FUNCTIONALITY ============
function initializeSearchFunctionality() {
    const searchInput = document.querySelector('.search-input');
    if (!searchInput) return;
    
    searchInput.addEventListener('input', debounce(function(e) {
        const query = e.target.value.toLowerCase();
        // Implement search logic here
        console.log('Searching for:', query);
    }, 300));
}

// ============ UTILITY FUNCTIONS ============
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============ CHART UTILITIES ============
function getChartColors(theme = 'pink') {
    const colors = {
        pink: {
            primary: '#ec3b7f',
            light: '#f5a3c3',
            dark: '#c92356'
        },
        light: {
            primary: '#006dd8',
            light: '#4da3ff',
            dark: '#004c99'
        },
        dark: {
            primary: '#ff5fa3',
            light: '#ff8fc9',
            dark: '#e53d7f'
        }
    };
    return colors[theme] || colors.pink;
}

// ============ SMOOTH SCROLL ============
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
        }
    });
});

// ============ ACTIVE NAV LINK ============
function setActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (currentPath === href || currentPath.startsWith(href + '/')) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Initialize active nav link
setActiveNavLink();

// ============ TABLE INTERACTIONS ============
document.addEventListener('DOMContentLoaded', function() {
    // Add hover effects to table rows
    const tableRows = document.querySelectorAll('.admin-table tbody tr');
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = 'rgba(236, 59, 127, 0.02)';
        });
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
});

// ============ FORM VALIDATION ============
function validateForm(form) {
    const inputs = form.querySelectorAll('[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('error');
            isValid = false;
        } else {
            input.classList.remove('error');
        }
    });
    
    return isValid;
}

// ============ DELETE CONFIRMATION ============
document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('.btn-delete');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
});

// ============ COPY TO CLIPBOARD ============
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        showNotification('Copied to clipboard!', 'success');
    });
}

// ============ NOTIFICATIONS ============
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 90px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        background: ${type === 'success' ? '#22c55e' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ============ ANIMATIONS ============
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
    
    @keyframes bounce {
        0%, 100% {
            transform: translateY(0);
        }
        50% {
            transform: translateY(-10px);
        }
    }
    
    .metric-card {
        animation: fadeInUp 0.5s ease;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);

// ============ WINDOW RESIZE HANDLER ============
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        const sidebar = document.querySelector('.admin-sidebar');
        if (sidebar) sidebar.classList.remove('active');
    }
});

// ============ EXPORT FUNCTIONS ============
// Make functions available globally
window.copyToClipboard = copyToClipboard;
window.showNotification = showNotification;
window.validateForm = validateForm;
window.setTheme = setTheme;
