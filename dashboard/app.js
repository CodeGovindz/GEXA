/**
 * GEXA Dashboard JavaScript
 */

const API_BASE = 'http://localhost:8000';

// State
let currentEndpoint = 'search';
let apiKey = localStorage.getItem('gexa_api_key') || '';

// DOM Elements
const apiKeyInput = document.getElementById('apiKeyInput');
const executeBtn = document.getElementById('executeBtn');
const responseOutput = document.getElementById('responseOutput');
const responseTime = document.getElementById('responseTime');
const apiStatus = document.getElementById('apiStatus');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initEndpointSelector();
    initApiKeyInput();
    initExecuteButton();
    initKeyManagement();
    checkApiStatus();

    // Load saved API key
    if (apiKey) {
        apiKeyInput.value = apiKey;
    }
});

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

        keysList.innerHTML = keys.map(key => `
            <div class="key-item">
                <div class="key-info">
                    <h4>${key.name}</h4>
                    <p>Prefix: <code>${key.key_prefix}...</code> | Created: ${new Date(key.created_at).toLocaleDateString()}</p>
                </div>
                <div class="key-meta">
                    <span class="key-quota">${key.quota_used} / ${key.quota_total} used</span>
                    <button class="delete-key-btn" onclick="deleteKey('${key.id}')">Delete</button>
                </div>
            </div>
        `).join('');

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

        // Show the new key
        alert(`API Key Created!\n\nKey: ${data.key}\n\n⚠️ Copy this key now - it won't be shown again!`);

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
        await fetch(`${API_BASE}/keys/${keyId}`, { method: 'DELETE' });
        loadApiKeys();
    } catch (error) {
        alert(`Error deleting key: ${error.message}`);
    }
}
