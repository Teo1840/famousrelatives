CREATE DATABASE IF NOT EXISTS famous;
USE famous;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(255) UNIQUE,
    token_expiration DATETIME
);

CREATE TABLE mini_arboles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    codigo VARCHAR(255),
    cercania INT,
    relationshipDescription VARCHAR(255),
    portraitUrl VARCHAR(500),
    coParentIsPathPerson BOOLEAN,
    parentescoPolitico BOOLEAN,
    camino_ascendente JSON,
    camino_descendente JSON,
    antepasado_comun JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);