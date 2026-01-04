use image_project;

CREATE TABLE IF NOT EXISTS users (
    id INT NOT NULL AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL,
    email VARCHAR(120) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE INDEX username_UNIQUE (username ASC),
    UNIQUE INDEX email_UNIQUE (email ASC)
);

CREATE TABLE IF NOT EXISTS images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    thumbnail_path VARCHAR(255),
    file_size INT,
    width INT,          
    height INT,         
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    device VARCHAR(100),
    capture_date DATETIME,
    location VARCHAR(255),
    ai_tags JSON,
    clip_embedding JSON,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tags (
    id INT NOT NULL AUTO_INCREMENT,
    tag_name VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE INDEX tag_name_UNIQUE (tag_name ASC)
);

CREATE TABLE IF NOT EXISTS image_tags (
    id INT NOT NULL AUTO_INCREMENT,
    image_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE INDEX image_tag_unique (image_id ASC, tag_id ASC),
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);