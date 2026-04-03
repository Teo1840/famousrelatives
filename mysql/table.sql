CREATE DATABASE IF NOT EXISTS famousrelatives;
USE famousrelatives;

CREATE TABLE IF NOT EXISTS arboles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    persona_id VARCHAR(255),
    data_json LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    viewer_person_id VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_persona_viewer
ON arboles(persona_id, viewer_person_id);