# AskMyNotes

**Created by:**  
Protistha Chowdhury (25LBCS3059)  
Shaswat Tiwari (25LBCS3007)

## 🔗 Live Links
* **Live Frontend:** [https://askmynotes-frontend.vercel.app](https://askmynotes-frontend.vercel.app)
* **Backend API:** [https://askmynotes-a5rv.onrender.com](https://askmynotes-a5rv.onrender.com)

## 🧪 Test Credentials
* **Email:** `test@gmail.com`
* **Password:** `test123`

## 📖 About the Project
AskMyNotes is a full-stack web application that allows students to upload course documents (PDFs) and ask questions based on the content. The system uses a Retrieval-Augmented Generation (RAG) pipeline to generate grounded answers and provides exact page citations from the source document.

## 🛠 Tech Stack
* **Frontend:** HTML, CSS, Vanilla JavaScript (Vercel)
* **Backend:** Python (Flask), Gunicorn (Render)
* **Database:** PostgreSQL + pgvector (Neon)
* **AI:** Cloudflare Workers AI (Llama 3.1)
* **Security:** JWT, Bcrypt password hashing

## ✨ Core Features
1. Role-based authentication
2. Document upload & extraction
3. Text chunking (preserving page numbers)
4. Vector embedding & storage (pgvector)
5. Q&A with exact page citations
6. Usage analytics (most queried documents)
7. Audit logging for security

## 💻 Local Setup (Brief)
* **Database:** Create Neon.tech DB, run `CREATE EXTENSION IF NOT EXISTS vector;`, then run `schema.sql`.
* **Backend:** `cd backend`, `pip install -r requirements.txt`, add keys to `.env`, `python app.py`.
* **Frontend:** Open `frontend/index.html`. Ensure `script.js` points to localhost.
