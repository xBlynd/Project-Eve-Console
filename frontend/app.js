// EVE Project Console - Frontend JavaScript

const API_BASE = '/api';
let currentLibraryId = null;
let currentRole = 'construction';
let conversationHistory = []; // Track conversation history

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    loadLibraries();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Add library modal
    document.getElementById('add-library-btn').addEventListener('click', openAddLibraryModal);
    document.getElementById('close-modal').addEventListener('click', closeAddLibraryModal);
    document.getElementById('cancel-btn').addEventListener('click', closeAddLibraryModal);
    document.getElementById('add-library-form').addEventListener('submit', handleAddLibrary);
    
    // Role selection
    document.querySelectorAll('.role-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentRole = btn.dataset.role;
            // Clear conversation history when switching roles
            conversationHistory = [];
        });
    });
    
    // Ask EVE
    document.getElementById('ask-btn').addEventListener('click', handleAskEve);
    document.getElementById('question-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            handleAskEve();
        }
    });
    
    // Library selection
    document.getElementById('library-select').addEventListener('change', (e) => {
        currentLibraryId = e.target.value;
        // Clear conversation history when switching libraries
        conversationHistory = [];
    });
}

// Load libraries from API
async function loadLibraries() {
    try {
        const response = await fetch(`${API_BASE}/libraries`);
        const libraries = await response.json();
        
        renderLibraryList(libraries);
        populateLibrarySelect(libraries);
    } catch (error) {
        console.error('Failed to load libraries:', error);
        showError('Failed to load libraries');
    }
}

// Render library list in sidebar
function renderLibraryList(libraries) {
    const listEl = document.getElementById('library-list');
    
    if (libraries.length === 0) {
        listEl.innerHTML = '<p class="loading">No libraries yet. Click "Add Library" to get started.</p>';
        return;
    }
    
    listEl.innerHTML = libraries.map(lib => `
        <div class="library-item" data-id="${lib.id}">
            <h3>${lib.name}</h3>
            <div class="library-meta">
                <div>Files: ${lib.file_count || 0}</div>
                <div>Last indexed: ${lib.last_indexed ? new Date(lib.last_indexed).toLocaleDateString() : 'Never'}</div>
            </div>
            <div class="library-actions">
                <button class="btn-primary btn-small" onclick="indexLibrary('${lib.id}')">Index</button>
                <button class="btn-secondary btn-small" onclick="deleteLibrary('${lib.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

// Populate library dropdown
function populateLibrarySelect(libraries) {
    const selectEl = document.getElementById('library-select');
    selectEl.innerHTML = '<option value="">-- Select a Library --</option>' +
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

// Handle add library form submission
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
        showSuccess('Library created successfully');
    } catch (error) {
        console.error('Failed to create library:', error);
        alert(error.message);
    }
}

// Index library
async function indexLibrary(libraryId) {
    try {
        showInfo('Indexing library... This may take a moment.');
        
        const response = await fetch(`${API_BASE}/libraries/${libraryId}/index`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Failed to index library');
        }
        
        const result = await response.json();
        showSuccess(`Indexed ${result.file_count} files`);
        loadLibraries();
    } catch (error) {
        console.error('Failed to index library:', error);
        showError('Failed to index library');
    }
}

// Delete library
async function deleteLibrary(libraryId) {
    if (!confirm('Are you sure you want to delete this library? This will remove the library and all indexed files.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/libraries/${libraryId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete library');
        }
        
        showSuccess('Library deleted');
        loadLibraries();
        
        if (currentLibraryId === libraryId) {
            currentLibraryId = null;
            document.getElementById('library-select').value = '';
            conversationHistory = [];
        }
    } catch (error) {
        console.error('Failed to delete library:', error);
        showError('Failed to delete library');
    }
}

// Handle Ask EVE
async function handleAskEve() {
    const question = document.getElementById('question-input').value.trim();
    
    if (!question) {
        alert('Please enter a question');
        return;
    }
    
    if (!currentLibraryId) {
        alert('Please select a library first');
        return;
    }
    
    // Add user message to chat
    addMessageToChat('user', question);
    
    // Add to conversation history
    conversationHistory.push({
        role: 'user',
        content: question
    });
    
    // Clear input
    document.getElementById('question-input').value = '';
    
    // Show loading
    const loadingId = addMessageToChat('assistant', 'EVE is thinking...');
    
    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                library_id: currentLibraryId,
                role: currentRole,
                question: question,
                keywords: [],
                max_files: 10,
                conversation_history: conversationHistory.slice(0, -1) // Send history without current question
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Query failed');
        }
        
        const result = await response.json();
        
        // Remove loading message
        removeMessageFromChat(loadingId);
        
        // Add EVE's response
        addMessageToChat('assistant', result.answer, result.used_files);
        
        // Add to conversation history
        conversationHistory.push({
            role: 'assistant',
            content: result.answer
        });
        
    } catch (error) {
        console.error('Query failed:', error);
        removeMessageFromChat(loadingId);
        addMessageToChat('assistant', `Error: ${error.message}`);
    }
}

// Add message to chat
function addMessageToChat(role, content, usedFiles = []) {
    const chatHistory = document.getElementById('chat-history');
    
    // Remove welcome message if it exists
    const welcomeMsg = chatHistory.querySelector('.welcome-message');
    if (welcomeMsg) {
        welcomeMsg.remove();
    }
    
    const messageId = `msg-${Date.now()}`;
    const messageEl = document.createElement('div');
    messageEl.className = `message message-${role}`;
    messageEl.id = messageId;
    
    let html = `
        <div class="message-label">${role === 'user' ? 'You' : 'EVE'}</div>
        <div class="message-content">${content}</div>
    `;
    
    if (usedFiles && usedFiles.length > 0) {
        html += `
            <div class="used-files">
                <div class="used-files-label">Referenced files:</div>
                ${usedFiles.map(f => `<span class="file-tag">${f.rel_path}</span>`).join('')}
            </div>
        `;
    }
    
    messageEl.innerHTML = html;
    chatHistory.appendChild(messageEl);
    
    // Scroll to bottom
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return messageId;
}

// Remove message from chat
function removeMessageFromChat(messageId) {
    const messageEl = document.getElementById(messageId);
    if (messageEl) {
        messageEl.remove();
    }
}

// Notification functions
function showSuccess(message) {
    console.log('SUCCESS:', message);
    // You can implement a toast notification here
}

function showError(message) {
    console.error('ERROR:', message);
    // You can implement a toast notification here
}

function showInfo(message) {
    console.log('INFO:', message);
    // You can implement a toast notification here
}
