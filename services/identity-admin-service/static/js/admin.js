/**
 * Identity Admin Service - Admin Dashboard JavaScript
 * Internal Use Only - Not for public-facing deployment
 */

(function() {
    'use strict';

    // ========================================
    // Utility Functions
    // ========================================
    
    /**
     * Copy text to clipboard
     * @param {string} text - Text to copy
     * @param {HTMLElement} button - Button element for visual feedback
     */
    function copyToClipboard(text, button) {
        navigator.clipboard.writeText(text).then(() => {
            if (button) {
                button.classList.add('copied');
                setTimeout(() => button.classList.remove('copied'), 2000);
            }
            showToast('Copied to clipboard', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
            showToast('Failed to copy', 'error');
        });
    }

    /**
     * Show toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: 'success', 'error', 'warning', 'info'
     */
    function showToast(message, type = 'info') {
        // Create toast container if doesn't exist
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = `
                position: fixed;
                top: 1rem;
                right: 1rem;
                z-index: 9999;
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            `;
            document.body.appendChild(container);
        }

        // Create toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.style.cssText = `
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            background-color: ${type === 'success' ? '#d1fae5' : type === 'error' ? '#fee2e2' : type === 'warning' ? '#fef3c7' : '#dbeafe'};
            color: ${type === 'success' ? '#065f46' : type === 'error' ? '#991b1b' : type === 'warning' ? '#92400e' : '#1e40af'};
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            font-size: 0.875rem;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
        `;
        toast.textContent = message;
        container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateX(0)';
        });

        // Remove after delay
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * Format date for display
     * @param {string|Date} date - Date to format
     * @returns {string} Formatted date string
     */
    function formatDate(date) {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Format time ago
     * @param {string|Date} date - Date to format
     * @returns {string} Relative time string
     */
    function timeAgo(date) {
        const seconds = Math.floor((new Date() - new Date(date)) / 1000);
        
        const intervals = [
            { label: 'year', seconds: 31536000 },
            { label: 'month', seconds: 2592000 },
            { label: 'day', seconds: 86400 },
            { label: 'hour', seconds: 3600 },
            { label: 'minute', seconds: 60 }
        ];

        for (const interval of intervals) {
            const count = Math.floor(seconds / interval.seconds);
            if (count >= 1) {
                return `${count} ${interval.label}${count > 1 ? 's' : ''} ago`;
            }
        }
        return 'just now';
    }

    /**
     * Debounce function
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     * @returns {Function} Debounced function
     */
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

    // ========================================
    // API Client
    // ========================================

    const api = {
        /**
         * Make API request
         * @param {string} endpoint - API endpoint
         * @param {object} options - Fetch options
         * @returns {Promise} Response data
         */
        async request(endpoint, options = {}) {
            const defaults = {
                headers: {
                    'Content-Type': 'application/json',
                },
            };

            const config = {
                ...defaults,
                ...options,
                headers: {
                    ...defaults.headers,
                    ...options.headers,
                },
            };

            try {
                const response = await fetch(endpoint, config);
                
                if (!response.ok) {
                    const error = await response.json().catch(() => ({}));
                    throw new Error(error.detail || `HTTP ${response.status}`);
                }

                // Handle 204 No Content
                if (response.status === 204) {
                    return null;
                }

                return await response.json();
            } catch (error) {
                console.error('API Error:', error);
                throw error;
            }
        },

        get(endpoint) {
            return this.request(endpoint, { method: 'GET' });
        },

        post(endpoint, data) {
            return this.request(endpoint, {
                method: 'POST',
                body: JSON.stringify(data),
            });
        },

        put(endpoint, data) {
            return this.request(endpoint, {
                method: 'PUT',
                body: JSON.stringify(data),
            });
        },

        patch(endpoint, data) {
            return this.request(endpoint, {
                method: 'PATCH',
                body: JSON.stringify(data),
            });
        },

        delete(endpoint) {
            return this.request(endpoint, { method: 'DELETE' });
        },
    };

    // ========================================
    // Modal Management
    // ========================================

    class ModalManager {
        constructor() {
            this.activeModal = null;
            this.init();
        }

        init() {
            // Close modal on escape key
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape' && this.activeModal) {
                    this.close();
                }
            });

            // Close modal on backdrop click
            document.addEventListener('click', (e) => {
                if (e.target.classList.contains('modal') && e.target.classList.contains('active')) {
                    this.close();
                }
            });
        }

        open(modalId) {
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.add('active');
                this.activeModal = modal;
                document.body.style.overflow = 'hidden';
            }
        }

        close() {
            if (this.activeModal) {
                this.activeModal.classList.remove('active');
                this.activeModal = null;
                document.body.style.overflow = '';
            }
        }
    }

    // ========================================
    // Form Validation
    // ========================================

    class FormValidator {
        constructor(form) {
            this.form = form;
            this.errors = {};
        }

        validate() {
            this.errors = {};
            const inputs = this.form.querySelectorAll('[data-validate]');

            inputs.forEach(input => {
                const rules = input.dataset.validate.split('|');
                const value = input.value.trim();

                rules.forEach(rule => {
                    const [ruleName, ruleParam] = rule.split(':');
                    const error = this.checkRule(ruleName, value, ruleParam, input);
                    if (error && !this.errors[input.name]) {
                        this.errors[input.name] = error;
                    }
                });
            });

            return Object.keys(this.errors).length === 0;
        }

        checkRule(rule, value, param, input) {
            switch (rule) {
                case 'required':
                    return value === '' ? 'This field is required' : null;
                case 'email':
                    return !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) && value !== '' 
                        ? 'Please enter a valid email' : null;
                case 'url':
                    try {
                        if (value !== '') new URL(value);
                        return null;
                    } catch {
                        return 'Please enter a valid URL';
                    }
                case 'min':
                    return value.length < parseInt(param) 
                        ? `Minimum ${param} characters required` : null;
                case 'max':
                    return value.length > parseInt(param) 
                        ? `Maximum ${param} characters allowed` : null;
                default:
                    return null;
            }
        }

        showErrors() {
            // Clear previous errors
            this.form.querySelectorAll('.form-error').forEach(el => el.remove());
            this.form.querySelectorAll('.input-error').forEach(el => el.classList.remove('input-error'));

            // Show new errors
            Object.entries(this.errors).forEach(([name, message]) => {
                const input = this.form.querySelector(`[name="${name}"]`);
                if (input) {
                    input.classList.add('input-error');
                    const error = document.createElement('span');
                    error.className = 'form-error';
                    error.textContent = message;
                    input.parentNode.appendChild(error);
                }
            });
        }
    }

    // ========================================
    // Initialization
    // ========================================

    function init() {
        // Initialize modal manager
        window.modalManager = new ModalManager();

        // Initialize copy buttons
        document.querySelectorAll('.copy-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                copyToClipboard(this.dataset.copy, this);
            });
        });

        // Initialize form validation
        document.querySelectorAll('form[data-validate]').forEach(form => {
            form.addEventListener('submit', function(e) {
                const validator = new FormValidator(this);
                if (!validator.validate()) {
                    e.preventDefault();
                    validator.showErrors();
                }
            });
        });

        // Initialize mobile sidebar toggle
        const sidebarToggle = document.querySelector('.sidebar-toggle');
        const sidebar = document.querySelector('.admin-sidebar');
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', () => {
                sidebar.classList.toggle('open');
            });
        }

        // Initialize search with debounce
        const searchInput = document.querySelector('.search-input-wrapper input');
        if (searchInput) {
            const debouncedSearch = debounce((value) => {
                // Could be used for live search
                console.log('Search:', value);
            }, 300);

            searchInput.addEventListener('input', (e) => {
                debouncedSearch(e.target.value);
            });
        }

        // Log initialization (development only)
        console.log('Identity Admin Service initialized');
        console.log('⚠️ INTERNAL USE ONLY - This admin interface is not for public access');
    }

    // ========================================
    // Export Public API
    // ========================================

    window.AdminApp = {
        api,
        showToast,
        copyToClipboard,
        formatDate,
        timeAgo,
        ModalManager,
        FormValidator,
    };

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
