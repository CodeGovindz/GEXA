/**
 * GEXA Dashboard JavaScript
 */

const API_BASE = '';

// State
let currentEndpoint = 'search';
let apiKey = localStorage.getItem('gexa_api_key') || '';
let accessToken = localStorage.getItem('gexa_access_token') || '';
let userEmail = localStorage.getItem('gexa_user_email') || '';

// DOM Elements
const apiKeyInput = document.getElementById('apiKeyInput');
const executeBtn = document.getElementById('executeBtn');
const responseOutput = document.getElementById('responseOutput');
const responseTime = document.getElementById('responseTime');
const apiStatus = document.getElementById('apiStatus');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is logged in
    if (!accessToken) {
        // Redirect to login page
        window.location.href = '/dashboard/login.html';
        return;
    }

    initNavigation();
    initEndpointSelector();
    initApiKeyInput();
    initExecuteButton();
    initKeyManagement();
    checkApiStatus();
    createKeyModal();
    initUserMenu();

    // Load saved API key
    if (apiKey) {
        apiKeyInput.value = apiKey;
    }
});

// Initialize user menu
function initUserMenu() {
    const userMenu = document.getElementById('userMenu');
    const userAvatar = document.getElementById('userAvatar');
    const userEmailEl = document.getElementById('userEmail');

    if (userEmail && userMenu) {
        userMenu.style.display = 'block';
        userEmailEl.textContent = userEmail;
        userAvatar.textContent = userEmail.charAt(0).toUpperCase();
    }
}

// Logout handler
async function handleLogout() {
    try {
        await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
    } catch (error) {
        console.error('Logout error:', error);
    }

    // Clear all auth data
    localStorage.removeItem('gexa_access_token');
    localStorage.removeItem('gexa_refresh_token');
    localStorage.removeItem('gexa_user_email');
    localStorage.removeItem('gexa_user_id');
    localStorage.removeItem('gexa_api_key');

    // Redirect to login
    window.location.href = '/dashboard/login.html';
}

// Create the API key modal
function createKeyModal() {
    const modal = document.createElement('div');
    modal.id = 'keyModal';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>🔑 API Key Created!</h3>
            </div>
            <div class="modal-body">
                <p>Your new API key has been created. Copy it now - it won't be shown again!</p>
                <div class="key-display">
                    <input type="text" id="newKeyDisplay" readonly>
                    <button id="copyKeyBtn" class="copy-btn">📋 Copy</button>
                </div>
                <p class="copy-status" id="copyStatus"></p>
            </div>
            <div class="modal-footer">
                <button id="closeModalBtn" class="close-modal-btn">Close</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    // Close modal
    document.getElementById('closeModalBtn').addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Copy key
    document.getElementById('copyKeyBtn').addEventListener('click', async () => {
        const keyDisplay = document.getElementById('newKeyDisplay');
        try {
            await navigator.clipboard.writeText(keyDisplay.value);
            document.getElementById('copyStatus').textContent = '✅ Copied to clipboard!';
            document.getElementById('copyStatus').style.color = '#22c55e';
        } catch (err) {
            // Fallback for older browsers
            keyDisplay.select();
            document.execCommand('copy');
            document.getElementById('copyStatus').textContent = '✅ Copied to clipboard!';
            document.getElementById('copyStatus').style.color = '#22c55e';
        }
    });

    // Close on outside click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Show the key modal
function showKeyModal(key) {
    const modal = document.getElementById('keyModal');
    document.getElementById('newKeyDisplay').value = key;
    document.getElementById('copyStatus').textContent = '';
    modal.style.display = 'flex';
}

// Navigation
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const page = item.dataset.page;

            // Update nav
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            // Update pages
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.getElementById(`${page}Page`).classList.add('active');

            // Load data for specific pages
            if (page === 'keys') {
                loadApiKeys();
            }
        });
    });
}

// Endpoint Selector
function initEndpointSelector() {
    const buttons = document.querySelectorAll('.endpoint-btn');

    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const endpoint = btn.dataset.endpoint;
            currentEndpoint = endpoint;

            // Update buttons
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update forms
            document.querySelectorAll('.form-section').forEach(form => {
                form.classList.remove('active');
            });
            document.getElementById(`${endpoint}Form`).classList.add('active');
        });
    });
}

// API Key Input
function initApiKeyInput() {
    apiKeyInput.addEventListener('change', () => {
        apiKey = apiKeyInput.value;
        localStorage.setItem('gexa_api_key', apiKey);
    });

    document.getElementById('toggleKeyVisibility').addEventListener('click', () => {
        const type = apiKeyInput.type === 'password' ? 'text' : 'password';
        apiKeyInput.type = type;
    });
}

// Execute Button
function initExecuteButton() {
    executeBtn.addEventListener('click', executeRequest);
}

async function executeRequest() {
    if (!apiKey) {
        showError('Please enter your API key');
        return;
    }

    executeBtn.disabled = true;
    executeBtn.querySelector('.btn-text').style.display = 'none';
    executeBtn.querySelector('.btn-loader').style.display = 'inline';
    responseOutput.textContent = 'Loading...';
    responseTime.textContent = '';

    const startTime = Date.now();

    try {
        const { endpoint, body } = buildRequest();

        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey,
            },
            body: JSON.stringify(body),
        });

        const data = await response.json();
        const elapsed = Date.now() - startTime;

        if (!response.ok) {
            throw new Error(data.detail || 'Request failed');
        }

        responseOutput.textContent = JSON.stringify(data, null, 2);
        responseTime.textContent = `${elapsed}ms`;

    } catch (error) {
        showError(error.message);
    } finally {
        executeBtn.disabled = false;
        executeBtn.querySelector('.btn-text').style.display = 'inline';
        executeBtn.querySelector('.btn-loader').style.display = 'none';
    }
}

function buildRequest() {
    switch (currentEndpoint) {
        case 'search':
            return {
                endpoint: '/search',
                body: {
                    query: document.getElementById('searchQuery').value,
                    num_results: parseInt(document.getElementById('searchNumResults').value),
                    include_content: document.getElementById('searchIncludeContent').checked,
                },
            };

        case 'contents':
            const urlsText = document.getElementById('contentsUrls').value;
            const urls = urlsText.split('\n').map(u => u.trim()).filter(u => u);
            return {
                endpoint: '/contents',
                body: {
                    urls: urls,
                    include_markdown: document.getElementById('contentsIncludeMarkdown').checked,
                },
            };

        case 'answer':
            return {
                endpoint: '/answer',
                body: {
                    query: document.getElementById('answerQuery').value,
                    num_sources: parseInt(document.getElementById('answerNumSources').value),
                    include_citations: true,
                },
            };

        case 'research':
            return {
                endpoint: '/research',
                body: {
                    topic: document.getElementById('researchTopic').value,
                    instructions: document.getElementById('researchInstructions').value || null,
                    depth: document.getElementById('researchDepth').value,
                    output_format: document.getElementById('researchFormat').value,
                },
            };

        case 'similar':
            return {
                endpoint: '/findsimilar',
                body: {
                    url: document.getElementById('similarUrl').value,
                    num_results: parseInt(document.getElementById('similarNumResults').value),
                },
            };

        default:
            throw new Error('Unknown endpoint');
    }
}

function showError(message) {
    responseOutput.textContent = `Error: ${message}`;
    responseOutput.style.color = '#ef4444';
    setTimeout(() => {
        responseOutput.style.color = '';
    }, 3000);
}

// API Status Check
async function checkApiStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            apiStatus.textContent = 'API Online';
            document.querySelector('.status-dot').style.background = '#22c55e';
        } else {
            throw new Error('API offline');
        }
    } catch (error) {
        apiStatus.textContent = 'API Offline';
        document.querySelector('.status-dot').style.background = '#ef4444';
    }
}

// Key Management
function initKeyManagement() {
    document.getElementById('createKeyBtn').addEventListener('click', createApiKey);
}

async function loadApiKeys() {
    const keysList = document.getElementById('keysList');
    keysList.innerHTML = '<p class="loading-text">Loading keys...</p>';

    try {
        const response = await fetch(`${API_BASE}/keys`);
        const keys = await response.json();

        if (keys.length === 0) {
            keysList.innerHTML = '<p class="loading-text">No API keys yet. Create one above!</p>';
            return;
        }

        keysList.innerHTML = '';
        keys.forEach(key => {
            const keyItem = document.createElement('div');
            keyItem.className = 'key-item';
            keyItem.innerHTML = `
                <div class="key-info">
                    <h4>${key.name}</h4>
                    <p>Prefix: <code>${key.key_prefix}...</code> | Created: ${new Date(key.created_at).toLocaleDateString()}</p>
                </div>
                <div class="key-meta">
                    <span class="key-quota">${key.quota_used} / ${key.quota_total} used</span>
                    <button class="delete-key-btn" data-key-id="${key.id}">Delete</button>
                </div>
            `;
            keysList.appendChild(keyItem);
        });

        // Add event listeners to delete buttons
        document.querySelectorAll('.delete-key-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const keyId = e.target.dataset.keyId;
                await deleteKey(keyId);
            });
        });

    } catch (error) {
        keysList.innerHTML = `<p class="loading-text">Error loading keys: ${error.message}</p>`;
    }
}

async function createApiKey() {
    const name = document.getElementById('newKeyName').value;
    const quota = parseInt(document.getElementById('newKeyQuota').value);

    if (!name) {
        alert('Please enter a key name');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/keys`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, quota_total: quota }),
        });

        const data = await response.json();

        // Show the new key in modal with copy option
        showKeyModal(data.key);

        // Clear form
        document.getElementById('newKeyName').value = '';

        // Reload list
        loadApiKeys();

    } catch (error) {
        alert(`Error creating key: ${error.message}`);
    }
}

async function deleteKey(keyId) {
    if (!confirm('Are you sure you want to delete this API key?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/keys/${keyId}`, { method: 'DELETE' });
        if (!response.ok) {
            throw new Error('Failed to delete key');
        }
        loadApiKeys();
    } catch (error) {
        alert(`Error deleting key: ${error.message}`);
    }
}
