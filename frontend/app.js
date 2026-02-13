// EVE Project Console - Frontend Application

const API_BASE = '/api';
let currentLibraryId = null;
let currentRole = 'construction';
let currentChatId = null;
let conversationHistory = [];

// Configure marked.js for markdown rendering
if (typeof marked !== 'undefined') {
    marked.setOptions({
        breaks: true,
        gfm: true,
        highlight: function(code, lang) {
            return code;
        }
    });
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('EVE Console initializing...');
    loadLibraries();
    setupEventListeners();
    startNewChat();
});

// Setup event listeners
function setupEventListeners() {
    // Library modal
    document.getElementById('add-library-btn').addEventListener('click', openAddLibraryModal);
    document.getElementById('close-modal').addEventListener('click', closeAddLibraryModal);
    document.getElementById('cancel-btn').addEventListener('click', closeAddLibraryModal);
    document.getElementById('add-library-form').addEventListener('submit', handleAddLibrary);
    
    // Settings modal
    document.getElementById('settings-btn').addEventListener('click', openSettingsModal);
    document.getElementById('close-settings-modal').addEventListener('click', closeSettingsModal);
    document.getElementById('cancel-settings-btn').addEventListener('click', closeSettingsModal);
    
    // New chat
    document.getElementById('new-chat-btn').addEventListener('click', startNewChat);
    
    // Role selection
    document.querySelectorAll('.role-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.role-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentRole = btn.dataset.role;
            conversationHistory = [];
        });
    });
    
    // Send message
    const sendBtn = document.getElementById('send-btn');
    const messageInput = document.getElementById('message-input');
    
    sendBtn.addEventListener('click', () => {
        console.log('Send button clicked');
        handleSendMessage();
    });
    
    messageInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleSendMessage();
        }
    });
    
    // Auto-resize textarea
    messageInput.addEventListener('input', () => {
        messageInput.style.height = 'auto';
        messageInput.style.height = messageInput.scrollHeight + 'px';
    });
    
    // Library selection
    document.getElementById('library-select').addEventListener('change', (e) => {
        currentLibraryId = e.target.value || null;
        conversationHistory = [];
    });
}

// Start new chat
function startNewChat() {
    currentChatId = `chat-${Date.now()}`;
    conversationHistory = [];
    
    const messagesContainer = document.getElementById('chat-messages');
    messagesContainer.innerHTML = `
        <div class="welcome-card">
            <div class="welcome-icon">🤖</div>
            <h2>Welcome to EVE</h2>
            <p class="welcome-subtitle">Your AI Operations Intelligence Layer</p>
            <div class="welcome-features">
                <div class="feature">
                    <span class="feature-icon">💬</span>
                    <span>Chat without a library - I can help with general questions</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">📁</span>
                    <span>Add libraries to give me context from your projects</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">🔄</span>
                    <span>Switch roles for specialized expertise</span>
                </div>
            </div>
        </div>
    `;
}

// Load libraries
async function loadLibraries() {
    try {
        const response = await fetch(`${API_BASE}/libraries`);
        const libraries = await response.json();
        
        renderLibraryList(libraries);
        populateLibrarySelect(libraries);
    } catch (error) {
        console.error('Failed to load libraries:', error);
    }
}

// Render library list
function renderLibraryList(libraries) {
    const listEl = document.getElementById('library-list');
    
    if (libraries.length === 0) {
        listEl.innerHTML = '<p class="loading">No libraries yet</p>';
        return;
    }
    
    listEl.innerHTML = libraries.map(lib => `
        <div class="library-item" data-id="${lib.id}">
            <h4>${lib.name}</h4>
            <div class="library-meta">
                📄 ${lib.file_count || 0} files<br>
                🕒 ${lib.last_indexed ? new Date(lib.last_indexed).toLocaleDateString() : 'Not indexed'}
            </div>
            <div class="library-actions">
                <button class="btn-primary btn-small" onclick="indexLibrary('${lib.id}')">Index</button>
                <button class="btn-secondary btn-small" onclick="deleteLibrary('${lib.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

// Populate library select
function populateLibrarySelect(libraries) {
    const selectEl = document.getElementById('library-select');
    selectEl.innerHTML = '<option value="">General (No Library)</option>' +
        libraries.map(lib => `<option value="${lib.id}">${lib.name}</option>`).join('');
}

// Modal functions
function openAddLibraryModal() {
    document.getElementById('add-library-modal').classList.add('active');
}

function closeAddLibraryModal() {
    document.getElementById('add-library-modal').classList.remove('active');
    document.getElementById('add-library-form').reset();
}

function openSettingsModal() {
    document.getElementById('settings-modal').classList.add('active');
}

function closeSettingsModal() {
    document.getElementById('settings-modal').classList.remove('active');
}

// Handle add library
async function handleAddLibrary(e) {
    e.preventDefault();
    
    const name = document.getElementById('library-name').value;
    const path = document.getElementById('library-path').value;
    const type = document.getElementById('library-type').value;
    
    try {
        const response = await fetch(`${API_BASE}/libraries`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, root_path: path, type, tags: [] })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create library');
        }
        
        closeAddLibraryModal();
        loadLibraries();
        alert('Library created successfully');
    } catch (error) {
        console.error('Failed to create library:', error);
        alert(error.message);
    }
}

// Index library
async function indexLibrary(libraryId) {
    try {
        const response = await fetch(`${API_BASE}/libraries/${libraryId}/index`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to index library');
        }
        
        const result = await response.json();
        alert(`Indexed ${result.file_count} files`);
        loadLibraries();
    } catch (error) {
        console.error('Failed to index library:', error);
        alert('Failed to index library');
    }
}

// Delete library
async function deleteLibrary(libraryId) {
    if (!confirm('Delete this library?')) return;
    
    try {
        const response = await fetch(`${API_BASE}/libraries/${libraryId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete library');
        }
        
        loadLibraries();
        
        if (currentLibraryId === libraryId) {
            currentLibraryId = null;
            document.getElementById('library-select').value = '';
            conversationHistory = [];
        }
    } catch (error) {
        console.error('Failed to delete library:', error);
        alert('Failed to delete library');
    }
}

// Handle send message
async function handleSendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();
    
    console.log('handleSendMessage called, message:', message);
    
    if (!message) {
        console.log('Empty message, returning');
        return;
    }
    
    // Add user message
    addMessage('user', message);
    conversationHistory.push({ role: 'user', content: message });
    
    // Clear input
    input.value = '';
    input.style.height = 'auto';
    
    // Show loading
    const loadingId = addMessage('assistant', 'EVE is thinking...');
    
    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                library_id: currentLibraryId,
                role: currentRole,
                question: message,
                keywords: extractKeywords(message),
                max_files: 15,
                conversation_history: conversationHistory.slice(0, -1)
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }
        
        const result = await response.json();
        
        // Remove loading
        removeMessage(loadingId);
        
        // Add EVE's response
        addMessage('assistant', result.answer, result.used_files);
        conversationHistory.push({ role: 'assistant', content: result.answer });
        
    } catch (error) {
        console.error('Query failed:', error);
        removeMessage(loadingId);
        addMessage('assistant', `Error: ${error.message}`);
    }
}

// Extract keywords
function extractKeywords(question) {
    const stopWords = ['what', 'how', 'where', 'when', 'why', 'is', 'are', 'the', 'a', 'an', 'do', 'does'];
    const words = question.toLowerCase().match(/\b\w+\b/g) || [];
    return words.filter(w => w.length > 3 && !stopWords.includes(w));
}

// Add message to chat
function addMessage(role, content, usedFiles = []) {
    const container = document.getElementById('chat-messages');
    
    // Remove welcome card
    const welcome = container.querySelector('.welcome-card');
    if (welcome) welcome.remove();
    
    const messageId = `msg-${Date.now()}`;
    const messageEl = document.createElement('div');
    messageEl.className = `message message-${role}`;
    messageEl.id = messageId;
    
    // Render markdown for assistant
    let renderedContent = content;
    if (role === 'assistant' && typeof marked !== 'undefined') {
        renderedContent = marked.parse(content);
    } else {
        renderedContent = content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
    
    let html = `
        <div class="message-label">${role === 'user' ? '👤 You' : '🤖 EVE'}</div>
        <div class="message-content">${renderedContent}</div>
    `;
    
    if (usedFiles && usedFiles.length > 0) {
        html += `
            <div class="used-files">
                <div class="used-files-label">📂 Referenced files:</div>
                ${usedFiles.map(f => `<span class="file-tag">${f.rel_path}</span>`).join('')}
            </div>
        `;
    }
    
    messageEl.innerHTML = html;
    container.appendChild(messageEl);
    container.scrollTop = container.scrollHeight;
    
    return messageId;
}

// Remove message
function removeMessage(messageId) {
    const el = document.getElementById(messageId);
    if (el) el.remove();
}
