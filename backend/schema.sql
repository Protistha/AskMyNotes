-- 1. Create the tables (Third Normal Form)
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL
);

CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INT REFERENCES roles(role_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    doc_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_url TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Requires pgvector extension for the embedding column
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    chunk_id SERIAL PRIMARY KEY,
    doc_id INT REFERENCES documents(doc_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    page_number INT NOT NULL,
    embedding vector(768) -- 768 dimensions for standard embedding models
);

CREATE TABLE questions (
    question_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE answers (
    answer_id SERIAL PRIMARY KEY,
    question_id INT REFERENCES questions(question_id) ON DELETE CASCADE,
    answer_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE citations (
    citation_id SERIAL PRIMARY KEY,
    answer_id INT REFERENCES answers(answer_id) ON DELETE CASCADE,
    chunk_id INT REFERENCES chunks(chunk_id) ON DELETE CASCADE
);

CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(user_id),
    action_type VARCHAR(50) NOT NULL,
    details TEXT,
    action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Create a View (RDBMS Requirement)
CREATE VIEW most_queried_documents AS
SELECT d.filename, COUNT(q.question_id) AS query_count
FROM documents d
JOIN chunks c ON d.doc_id = c.doc_id
JOIN citations ci ON c.chunk_id = ci.chunk_id
JOIN answers a ON ci.answer_id = a.answer_id
JOIN questions q ON a.question_id = q.question_id
GROUP BY d.filename
ORDER BY query_count DESC;

-- 3. Create Indexes on searched columns (RDBMS Requirement)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_chunks_doc ON chunks(doc_id);
-- Index for vector similarity search (Cosine distance)
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);

-- 4. Stored Procedure & Transaction (RDBMS Requirement)
-- This procedure inserts a question, an answer, and citations in ONE transaction.
CREATE OR REPLACE PROCEDURE log_qa_transaction(
    p_user_id INT,
    p_question TEXT,
    p_answer TEXT,
    p_chunk_ids INT[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_question_id INT;
    v_answer_id INT;
    v_chunk_id INT;
BEGIN
    -- Transaction starts implicitly here
    INSERT INTO questions (user_id, question_text) VALUES (p_user_id, p_question) RETURNING question_id INTO v_question_id;
    INSERT INTO answers (question_id, answer_text) VALUES (v_question_id, p_answer) RETURNING answer_id INTO v_answer_id;
    
    -- Loop through array of chunk IDs to insert citations
    FOREACH v_chunk_id IN ARRAY p_chunk_ids
    LOOP
        INSERT INTO citations (answer_id, chunk_id) VALUES (v_answer_id, v_chunk_id);
    END LOOP;
    -- Transaction commits successfully
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Transaction failed: %', SQLERRM;
END;
$$;