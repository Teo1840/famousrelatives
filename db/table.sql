CREATE DATABASE IF NOT EXISTS famousrelatives;
USE famousrelatives;

CREATE TABLE IF NOT EXISTS arboles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    persona_id VARCHAR(255),
    data_json LONGTEXT,
    found_relationship TINYINT(1) NULL DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    viewer_person_id VARCHAR(255),
    user_id INT NULL
);

CREATE INDEX IF NOT EXISTS idx_persona_viewer
ON arboles(persona_id, viewer_person_id);

CREATE INDEX IF NOT EXISTS idx_persona_user
ON arboles(persona_id, user_id);

-- Una sola fila por persona y usuario (guardar_arbol hace upsert).
CREATE UNIQUE INDEX IF NOT EXISTS uq_persona_user
ON arboles(persona_id, user_id);

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    familysearch_token VARCHAR(1024) NULL,
    token_updated_at TIMESTAMP NULL DEFAULT NULL,
    viewer_person_id VARCHAR(255) NULL,
    viewer_portrait_url VARCHAR(1024) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
