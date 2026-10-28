// NOTE: Change this to your deployed backend URL if not running locally
const API_BASE = "http://localhost:5000/api";
let currentUserId = null;

// 1. Auth Functions
async function register() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    
    const res = await fetch(`${API_BASE}/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    document.getElementById('auth-msg').innerText = data.message || data.error;
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
        currentUserId = data.user_id;
        document.getElementById('auth-section').classList.add('hidden');
        document.getElementById('app-section').classList.remove('hidden');
    } else {
        document.getElementById('auth-msg').innerText = data.error;
    }
}

// 2. Upload Function
async function uploadFile() {
    const fileInput = document.getElementById('pdf-file');
    if (!fileInput.files[0]) return alert("Select a PDF first.");

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('user_id', currentUserId);

    document.getElementById('upload-msg').innerText = "Processing (embedding)... please wait.";
    
    const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
    });
    const data = await res.json();
    document.getElementById('upload-msg').innerText = data.message || data.error;
}

// 3. Ask Function
async function askQuestion() {
    const question = document.getElementById('question-input').value;
    const answerBox = document.getElementById('answer-box');
    const answerText = document.getElementById('answer-text');

    answerText.innerText = "Thinking...";
    answerBox.classList.remove('hidden');

    const res = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, user_id: currentUserId })
    });
    const data = await res.json();
    
    if (res.ok) {
        answerText.innerText = data.answer;
    } else {
        answerText.innerText = data.error;
    }
}