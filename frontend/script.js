
const API_BASE = "https://askmynotes-a5rv.onrender.com/api";
let authToken = null;

// --- AUTH FUNCTIONS ---

async function register() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    
    if (res.ok) {
        authToken = data.token;
        showApp();
    } else {
        document.getElementById('auth-msg').innerText = data.error;
    }
}

async function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    
    if (res.ok) {
        authToken = data.token;
        showApp();
    } else {
        document.getElementById('auth-msg').innerText = data.error;
    }
}

function showApp() {
    document.getElementById('auth-section').classList.add('hidden');
    document.getElementById('app-section').classList.remove('hidden');
    document.getElementById('auth-msg').innerText = "";
}

// --- APP FUNCTIONS ---

async function uploadFile() {
    const fileInput = document.getElementById('pdf-file');
    if (!fileInput.files[0]) return alert("Please select a PDF file first.");

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    document.getElementById('upload-msg').innerText = "Processing... please wait.";
    
    const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        headers: { 
            // FIX: Send JWT token to prove authentication
            'Authorization': `Bearer ${authToken}` 
        },
        body: formData
    });
    const data = await res.json();
    document.getElementById('upload-msg').innerText = data.message || data.error;
}

async function askQuestion() {
    const question = document.getElementById('question-input').value;
    if (!question) return;

    const answerBox = document.getElementById('answer-box');
    const answerText = document.getElementById('answer-text');
    const citationText = document.getElementById('citation-text');

    answerText.innerText = "Thinking...";
    citationText.innerText = "";
    answerBox.classList.remove('hidden');

    try {
        const res = await fetch(`${API_BASE}/ask`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                // FIX: Send JWT token
                'Authorization': `Bearer ${authToken}` 
            },
            body: JSON.stringify({ question })
        });
        
        const data = await res.json();
        
        if (res.ok) {
            answerText.innerText = data.answer;
            // FIX: Display the citations
            if (data.citations && data.citations.length > 0) {
                const cites = data.citations.map(c => `${c.file} (Page ${c.page})`).join(', ');
                citationText.innerText = `Sources: ${cites}`;
            }
        } else {
            answerText.innerText = "Error: " + (data.error || "Something went wrong");
        }
    } catch (error) {
        answerText.innerText = "Network error. Please check if the backend is running.";
    }
}
