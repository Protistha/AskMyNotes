import os
import hashlib
import secrets
import PyPDF2
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from db import execute_query

app = Flask(__name__)
CORS(app) # Allows your HTML frontend to talk to this Python backend

# --- AI Setup (Cloudflare Workers AI) ---
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")

# Only initialize AI client if keys exist
if CF_ACCOUNT_ID and CF_API_TOKEN:
    client = OpenAI(
        api_key=CF_API_TOKEN,
        base_url=f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1"
    )
else:
    client = None

# --- UTILITY: Security (Hashing) ---
def hash_password(password):
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return f"{salt}${hash_obj.hexdigest()}"

def verify_password(password, stored_hash):
    salt, hash_val = stored_hash.split('$')
    return hashlib.sha256((password + salt).encode()).hexdigest() == hash_val

# --- UTILITY: Audit Log ---
def log_action(user_id, action, details=""):
    try:
        query = "INSERT INTO audit_log (user_id, action_type, details) VALUES (%s, %s, %s)"
        execute_query(query, (user_id, action, details))
    except Exception as e:
        print(f"Failed to log action: {e}")

# ==========================================
# FEATURE 1: ROLE-BASED LOGIN
# ==========================================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing email or password"}), 400

    hashed = hash_password(data['password'])
    
    try:
        # FIX: Automatically create the default 'student' role if it doesn't exist
        execute_query("INSERT INTO roles (role_id, role_name) VALUES (1, 'student') ON CONFLICT (role_id) DO NOTHING")
        
        # Insert the new user
        execute_query("INSERT INTO users (email, password_hash, role_id) VALUES (%s, %s, 1)", 
                      (data['email'], hashed))
        return jsonify({"message": "User created successfully"}), 201
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ REGISTRATION ERROR: {error_msg}")
        if "unique constraint" in error_msg.lower():
            return jsonify({"error": "Email already exists"}), 400
        return jsonify({"error": "Database error occurred"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    user = execute_query("SELECT * FROM users WHERE email = %s", (data['email'],), fetch=True)
    
    if user and verify_password(data['password'], user[0]['password_hash']):
        log_action(user[0]['user_id'], "LOGIN", "User logged in")
        return jsonify({"user_id": user[0]['user_id'], "message": "Login successful"}), 200
    return jsonify({"error": "Invalid email or password"}), 401

# ==========================================
# FEATURES 2, 3 & 4: UPLOAD, CHUNK, EMBED
# ==========================================
@app.route('/api/upload', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    user_id = request.form.get('user_id')

    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF files allowed"}), 400

    try:
        # Read PDF
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        full_text = ""
        for page in pdf_reader.pages:
            full_text += page.extract_text() + "\n"

        file_url = f"https://dummy-storage.com/{file.filename}"

        # Save document record
        doc = execute_query(
            "INSERT INTO documents (user_id, filename, file_url) VALUES (%s, %s, %s) RETURNING doc_id",
            (user_id, file.filename, file_url), fetch=True
        )
        doc_id = doc[0]['doc_id']

        # Split into chunks
        chunks = [full_text[i:i+500] for i in range(0, len(full_text), 500)]
        
        for i, chunk_text in enumerate(chunks):
            if not chunk_text.strip(): continue
            
            # If AI is configured, embed. If not, use dummy vector so demo doesn't crash.
            if client:
                response = client.embeddings.create(
                    model="@cf/baai/bge-base-en-v1.5", 
                    input=chunk_text
                )
                embedding = response.data[0].embedding
            else:
                # Dummy vector of 768 zeros for tomorrow's demo if AI is missing
                embedding = [0.0] * 768 
            
            execute_query(
                "INSERT INTO chunks (doc_id, content, page_number, embedding) VALUES (%s, %s, %s, %s)",
                (doc_id, chunk_text, i+1, embedding)
            )

        log_action(user_id, "UPLOAD", f"Uploaded {file.filename}")
        return jsonify({"message": "File processed successfully"}), 200
        
    except Exception as e:
        print(f"❌ UPLOAD ERROR: {str(e)}")
        return jsonify({"error": "Failed to process document"}), 500

# ==========================================
# FEATURE 5: QUESTION ANSWERING WITH CITATIONS
# ==========================================
@app.route('/api/ask', methods=['POST'])
def ask_question():
    data = request.json
    question = data['question']
    user_id = data['user_id']

    if not client:
        return jsonify({"error": "AI is not configured. Check your .env file."}), 500

    try:
        # Embed the question
        emb_response = client.embeddings.create(
            model="@cf/baai/bge-base-en-v1.5",
            input=question
        )
        q_embedding = emb_response.data[0].embedding

        # Vector Search
        relevant_chunks = execute_query(
            "SELECT chunk_id, content FROM chunks ORDER BY embedding <=> %s LIMIT 2",
            (q_embedding,), fetch=True
        )

        if not relevant_chunks:
            return jsonify({"error": "No documents found to answer from."}), 404

        context = "\n\n".join([c['content'] for c in relevant_chunks])
        chunk_ids = [c['chunk_id'] for c in relevant_chunks]

        # Generate Answer
        prompt = f"Answer the question using ONLY this context:\n{context}\n\nQuestion: {question}"
        ai_response = client.chat.completions.create(
            model="@cf/meta/llama-3-8b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        answer_text = ai_response.choices[0].message.content

        # Save to DB using Stored Procedure
        execute_query(
            "CALL log_qa_transaction(%s, %s, %s, %s)",
            (user_id, question, answer_text, chunk_ids)
        )

        log_action(user_id, "QUERY", f"Asked: {question[:20]}...")
        return jsonify({
            "answer": answer_text,
            "cited_chunk_ids": chunk_ids
        }), 200
        
    except Exception as e:
        print(f"❌ AI ERROR: {str(e)}")
        return jsonify({"error": "Failed to generate answer"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)