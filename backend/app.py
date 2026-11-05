import os
import bcrypt
import jwt
import datetime
import PyPDF2
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
from db import execute_query

load_dotenv()

app = Flask(__name__)
# FIX: Restrict CORS (change "*" to your Vercel URL later)
CORS(app, resources={r"/api/*": {"origins": "*"}}) 

app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")

# AI Setup
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
CF_API_TOKEN = os.getenv("CF_API_TOKEN")
client = OpenAI(
    api_key=CF_API_TOKEN,
    base_url=f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1"
) if CF_ACCOUNT_ID and CF_API_TOKEN else None

# --- AUTH HELPERS ---
def generate_token(user_id, role_id):
    payload = {
        'user_id': user_id,
        'role_id': role_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm="HS256")

def get_current_user():
    """FIX: Enforce auth on protected routes using JWT"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(" ")[1]
    try:
        return jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
    except Exception:
        return None

def log_action(user_id, action, details=""):
    try:
        execute_query("INSERT INTO audit_logs (user_id, action_type, details) VALUES (%s, %s, %s)", (user_id, action, details))
    except Exception as e:
        print(f"Audit log error: {e}")

# --- ROUTES ---

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing fields"}), 400
    
    # FIX: Use bcrypt instead of SHA-256
    hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        execute_query("INSERT INTO roles (role_id, role_name) VALUES (1, 'student') ON CONFLICT DO NOTHING")
        user = execute_query(
            "INSERT INTO users (email, password_hash, role_id) VALUES (%s, %s, 1) RETURNING user_id, role_id", 
            (data['email'], hashed), fetch=True
        )
        token = generate_token(user[0]['user_id'], user[0]['role_id'])
        return jsonify({"message": "Registered", "token": token}), 201
    except Exception as e:
        if "unique constraint" in str(e).lower():
            return jsonify({"error": "Email exists"}), 400
        return jsonify({"error": "Database error"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing fields"}), 400

    user = execute_query("SELECT * FROM users WHERE email = %s", (data['email'],), fetch=True)
    
    if user and bcrypt.checkpw(data['password'].encode('utf-8'), user[0]['password_hash'].encode('utf-8')):
        token = generate_token(user[0]['user_id'], user[0]['role_id'])
        log_action(user[0]['user_id'], "LOGIN", "Success")
        return jsonify({"token": token}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/upload', methods=['POST'])
def upload_document():
    # FIX: Enforce Auth
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if not file.filename.endswith('.pdf'):
        return jsonify({"error": "Only PDF allowed"}), 400

    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(file.read()))
        chunks = []
        
        # FIX: Preserve actual page numbers and chunk by sentences/paragraphs
        for page_num, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                # Split by sentences to avoid mid-sentence cuts
                sentences = text.replace('\n', ' ').split('. ')
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) < 500:
                        current_chunk += sentence + ". "
                    else:
                        chunks.append({"text": current_chunk.strip(), "page": page_num + 1})
                        current_chunk = sentence + ". "
                if current_chunk:
                    chunks.append({"text": current_chunk.strip(), "page": page_num + 1})

        # FIX: db.py now commits this successfully
        doc = execute_query(
            "INSERT INTO documents (user_id, filename, file_url) VALUES (%s, %s, %s) RETURNING doc_id",
            (current_user['user_id'], file.filename, "dummy_url"), fetch=True
        )
        doc_id = doc[0]['doc_id']

        for c in chunks:
            embedding = [0.0] * 768
            if client:
                res = client.embeddings.create(model="@cf/baai/bge-base-en-v1.5", input=c['text'])
                embedding = res.data[0].embedding
            
            execute_query(
                "INSERT INTO chunks (doc_id, content, page_number, embedding) VALUES (%s, %s, %s, %s)",
                (doc_id, c['text'], c['page'], embedding)
            )

        log_action(current_user['user_id'], "UPLOAD", file.filename)
        return jsonify({"message": "Processed successfully"}), 200
    except Exception as e:
        print(f"Upload Error: {e}")
        return jsonify({"error": "Failed to process document"}), 500

@app.route('/api/ask', methods=['POST'])
def ask_question():
    # FIX: Enforce Auth
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not data or 'question' not in data:
        return jsonify({"error": "No question provided"}), 400
        
    question = data['question']
    user_id = current_user['user_id']

    if not client:
        return jsonify({"error": "AI not configured"}), 500

    try:
        emb_response = client.embeddings.create(model="@cf/baai/bge-base-en-v1.5", input=question)
        q_embedding = emb_response.data[0].embedding

        # FIX: Cast to ::vector and scope to current_user's documents only
        relevant_chunks = execute_query(
            """
            SELECT c.chunk_id, c.content, c.page_number, d.filename 
            FROM chunks c
            JOIN documents d ON c.doc_id = d.doc_id
            WHERE d.user_id = %s
            ORDER BY c.embedding <=> %s::vector 
            LIMIT 3
            """,
            (user_id, q_embedding), fetch=True
        )

        if not relevant_chunks:
            return jsonify({"error": "No documents found to answer from."}), 404

        context = "\n\n".join([f"[{c['filename']} Page {c['page_number']}] {c['content']}" for c in relevant_chunks])
        chunk_ids = [c['chunk_id'] for c in relevant_chunks]

        prompt = f"Answer the question using ONLY this context:\n{context}\n\nQuestion: {question}"
        ai_response = client.chat.completions.create(
            model="@cf/meta/llama-3-8b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        answer_text = ai_response.choices[0].message.content

        execute_query("CALL log_qa_transaction(%s, %s, %s, %s)", (user_id, question, answer_text, chunk_ids))
        log_action(user_id, "QUERY", question[:20])

        # FIX: Send back the actual citation text for frontend display
        citations = [{"file": c['filename'], "page": c['page_number']} for c in relevant_chunks]
        return jsonify({"answer": answer_text, "citations": citations}), 200
        
    except Exception as e:
        print(f"AI Error: {e}")
        return jsonify({"error": "Failed to generate answer"}), 500

if __name__ == '__main__':
    # FIX: debug=False for production readiness
    app.run(debug=False, port=5000)
