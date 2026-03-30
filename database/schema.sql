-- =============================================================================
-- CHO Marketwatch System — Database Schema
-- =============================================================================


-- 1. BRANDS
CREATE TABLE brands (
    id         SERIAL PRIMARY KEY,
    brand_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. PRODUCT TYPES
CREATE TABLE product_types (
    id           SERIAL PRIMARY KEY,
    product_type VARCHAR(150) NOT NULL UNIQUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. CATEGORIES
CREATE TABLE categories (
    id            SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. RANGES
CREATE TABLE ranges (
    id           SERIAL PRIMARY KEY,
    range_name   VARCHAR(100) NOT NULL UNIQUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. WEBSITES
CREATE TABLE websites (
    id         SERIAL PRIMARY KEY,
    site_name  VARCHAR(100) NOT NULL UNIQUE,
    base_url   VARCHAR(500) NOT NULL,
    country    VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. STORES (optional branch per website)
CREATE TABLE stores (
    id         SERIAL PRIMARY KEY,
    website_id INTEGER NOT NULL REFERENCES websites(id) ON DELETE CASCADE,
    store_code VARCHAR(50) NOT NULL,
    store_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(website_id, store_code)
);

-- 7. PRODUCTS
CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    brand_id        INTEGER NOT NULL REFERENCES brands(id)         ON DELETE CASCADE,
    product_type_id INTEGER NOT NULL REFERENCES product_types(id)  ON DELETE CASCADE,
    category_id     INTEGER NOT NULL REFERENCES categories(id)     ON DELETE CASCADE,
    range_id        INTEGER NOT NULL REFERENCES ranges(id)         ON DELETE CASCADE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(brand_id, product_type_id, category_id, range_id)
);

-- 8. PRODUCT FORMATS (format + packaging = unique format per product)
CREATE TABLE product_formats (
    id         SERIAL PRIMARY KEY,
    product_id INTEGER     NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    format     VARCHAR(50) NOT NULL,
    packaging  VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, format, packaging)
);

-- 9. PRODUCT URLS (URL per website/format)
CREATE TABLE product_urls (
    id                SERIAL PRIMARY KEY,
    website_id        INTEGER       NOT NULL REFERENCES websites(id)         ON DELETE CASCADE,
    store_id          INTEGER                REFERENCES stores(id)           ON DELETE CASCADE,
    product_format_id INTEGER       NOT NULL REFERENCES product_formats(id)  ON DELETE CASCADE,
    url               VARCHAR(1000) NOT NULL,
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(website_id, product_format_id, store_id)
);

-- 10. RAW STAGING (raw scraped HTML)
CREATE TABLE raw_staging (
    id               SERIAL PRIMARY KEY,
    product_url_id   INTEGER     NOT NULL REFERENCES product_urls(id) ON DELETE CASCADE,
    payload          TEXT        NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'failed')),
    http_status_code INTEGER,
    error_message    TEXT,
    scraped_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at     TIMESTAMP
);

-- 11. PRICE HISTORY (clean extracted prices)
CREATE TABLE price_history (
    id                SERIAL PRIMARY KEY,
    product_format_id INTEGER        NOT NULL REFERENCES product_formats(id) ON DELETE CASCADE,
    website_id        INTEGER        NOT NULL REFERENCES websites(id)         ON DELETE CASCADE,
    store_id          INTEGER                 REFERENCES stores(id)           ON DELETE CASCADE,
    price             DECIMAL(10, 2) NOT NULL CHECK (price > 0),
    currency          VARCHAR(10) DEFAULT 'EUR',
    scraped_at        TIMESTAMP NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. EXCHANGE RATES
CREATE TABLE exchange_rates (
    id          SERIAL PRIMARY KEY,
    currency    VARCHAR(10) NOT NULL,
    date        DATE        NOT NULL,
    rate_to_eur FLOAT       NOT NULL,
    UNIQUE(currency, date)
);

-- 13. USERS
CREATE TABLE users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(200),
    role          VARCHAR(20)  NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login    TIMESTAMP
);

-- Default admin user (password: admin123 — change immediately after first login)
-- password_hash is bcrypt of 'admin123'
INSERT INTO users (username, password_hash, full_name, role)
VALUES (
    'admin',
    '$2b$12$kQGdQI8DBoVUyhj3JsZXCu5BubXPBv60bHb6cpoI/2A71GF.rhgyS',
    'System Administrator',
    'admin'
);


-- =============================================================================
-- INDEXES
-- =============================================================================

CREATE INDEX idx_raw_staging_product_url  ON raw_staging(product_url_id);
CREATE INDEX idx_raw_staging_status       ON raw_staging(status);
CREATE INDEX idx_raw_staging_date         ON raw_staging(scraped_at DESC);

CREATE INDEX idx_price_history_format     ON price_history(product_format_id, scraped_at DESC);
CREATE INDEX idx_price_history_website    ON price_history(website_id);
CREATE INDEX idx_price_history_store      ON price_history(store_id);

CREATE INDEX idx_product_urls_website     ON product_urls(website_id, product_format_id);
CREATE INDEX idx_product_urls_store       ON product_urls(store_id);
CREATE INDEX idx_product_urls_active      ON product_urls(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_stores_website_code      ON stores(website_id, store_code);
CREATE INDEX idx_products_brand           ON products(brand_id);
CREATE INDEX idx_formats_product          ON product_formats(product_id);

CREATE INDEX idx_product_types            ON product_types(product_type);
CREATE INDEX idx_categories               ON categories(category_name);

CREATE INDEX idx_users_username           ON users(username);
CREATE INDEX idx_users_role               ON users(role);

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================