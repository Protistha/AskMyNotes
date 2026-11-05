AskMyNotes
Created by:
Protistha Chowdhury (25LBCS3059)
Shaswat Tiwari (25LBCS3007)

Live Frontend URL: https://askmynotes-frontend.vercel.app
Backend API URL: https://askmynotes-a5rv.onrender.com

AskMyNotes is a full-stack web application that allows students to upload course documents (PDFs) and ask questions based on the content. The system uses a Retrieval-Augmented Generation (RAG) pipeline to generate grounded answers and provides exact page citations from the source document.

🧪 Test Credentials
Use the following account to test the application immediately:

Email: test@gmail.com

Password: test123

🛠 Tech Stack
Frontend: HTML, CSS, Vanilla JavaScript (Hosted on Vercel)

Backend: Python (Flask), Gunicorn (Hosted on Render)

Database: PostgreSQL + pgvector (Hosted on Neon)

AI Integration: Cloudflare Workers AI (Llama 3.1 for chat, BGE for embeddings)

Security: JWT (JSON Web Tokens) for session management, Bcrypt for password hashing.

✨ Core Features
Role-based authentication: Secure login and registration with hashed passwords and separate user roles.

Document upload & extraction: Upload PDFs, validate file types, and extract raw text.

Text chunking: Split extracted text into smaller passages while preserving actual page numbers.

Vector embedding & storage: Convert text chunks into vector embeddings and store them in PostgreSQL using pgvector.

Q&A with citations: A RAG pipeline that searches for relevant chunks, generates an AI answer, and cites the source page.

Usage analytics: A database view (most_queried_documents) that tracks and displays the most queried documents.

Audit logging: An automated trail (audit_logs table) that records user actions (logins, uploads, queries) for security monitoring.

💻 Local Setup Instructions
If you want to run this project locally, follow these steps:

1. Database Setup (Neon.tech)

Create a free PostgreSQL database on Neon.tech.

In the Neon SQL Editor, enable the vector extension by running: CREATE EXTENSION IF NOT EXISTS vector;

Run the contents of the backend/schema.sql file in the Neon SQL Editor to create the tables, views, indexes, and stored procedures.

2. Backend Setup

Navigate to the backend directory: cd backend

Install the required Python packages: pip install -r requirements.txt

Create a .env file in the backend/ folder and add your credentials:

DATABASE_URL = your_neon_postgres_url

SECRET_KEY = your_random_secret_string

CF_ACCOUNT_ID = your_cloudflare_account_id

CF_API_TOKEN = your_cloudflare_api_token

Start the Flask server: python app.py

3. Frontend Setup

Open frontend/script.js and ensure the API_BASE variable points to your local backend (e.g., http://127.0.0.1:5000/api).

Open frontend/index.html in your web browser.

☁️ Deployment Details
Backend: Deployed as a Web Service on Render using gunicorn.

Frontend: Deployed as a Static Site on Vercel.

Security (CORS): The backend strictly restricts origins to the live Vercel frontend URL.

📊 Analytics
The project includes a SQL view for analytics that can be queried via the Neon SQL editor:
SELECT * FROM most_queried_documents;
