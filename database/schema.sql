-- =============================================================================
-- CHO Marketwatch System — Database Schema
-- =============================================================================


-- 1. BRANDS
CREATE TABLE brands (
    id         SERIAL PRIMARY KEY,
    brand_name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. CATEGORIES
CREATE TABLE categories (
    id            SERIAL PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. RANGES
CREATE TABLE ranges (
    id           SERIAL PRIMARY KEY,
    range_name   VARCHAR(100) NOT NULL UNIQUE,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. WEBSITES
CREATE TABLE websites (
    id         SERIAL PRIMARY KEY,
    site_name  VARCHAR(100) NOT NULL UNIQUE,
    base_url   VARCHAR(500) NOT NULL CHECK (BTRIM(base_url) <> ''),
    country    VARCHAR(50) NOT NULL CHECK (BTRIM(country) <> ''),
    scraper_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (scraper_status IN ('pending', 'active')),
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

-- 6. PRODUCTS
CREATE TABLE products (
    id              SERIAL PRIMARY KEY,
    brand_id        INTEGER NOT NULL REFERENCES brands(id)         ON DELETE CASCADE,
    category_id     INTEGER NOT NULL REFERENCES categories(id)     ON DELETE CASCADE,
    range_id        INTEGER NOT NULL REFERENCES ranges(id)         ON DELETE CASCADE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(brand_id, category_id, range_id)
);

-- 7. FORMATS
CREATE TABLE formats (
    id           SERIAL PRIMARY KEY,
    format_name  VARCHAR(50) NOT NULL UNIQUE,
    volume_value NUMERIC(10, 3) NOT NULL CHECK (volume_value > 0),
    volume_unit  VARCHAR(10) NOT NULL CHECK (volume_unit IN ('ML', 'L')),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. PACKAGINGS
CREATE TABLE packagings (
    id             SERIAL PRIMARY KEY,
    packaging_name VARCHAR(50) NOT NULL UNIQUE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. PRODUCT VARIANTS (product + format + packaging)
CREATE TABLE product_variants (
    id         SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    format_id  INTEGER NOT NULL REFERENCES formats(id) ON DELETE RESTRICT,
    packaging_id INTEGER NOT NULL REFERENCES packagings(id) ON DELETE RESTRICT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, format_id, packaging_id)
);

-- 10. PRODUCT URLS (URL per website/variant)
CREATE TABLE product_urls (
    id                SERIAL PRIMARY KEY,
    website_id        INTEGER       NOT NULL REFERENCES websites(id)         ON DELETE CASCADE,
    store_id          INTEGER                REFERENCES stores(id)           ON DELETE CASCADE,
    product_variant_id INTEGER      NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    url               VARCHAR(1000) NOT NULL,
    is_active         BOOLEAN DEFAULT TRUE,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(website_id, product_variant_id, store_id)
);

-- 11. RAW STAGING (raw scraped HTML)
CREATE TABLE raw_staging (
    id               SERIAL PRIMARY KEY,
    product_url_id   INTEGER     NOT NULL REFERENCES product_urls(id) ON DELETE CASCADE,
    payload          TEXT        NOT NULL,
    status           VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processed', 'failed')),
    http_status_code INTEGER,
    error_message    TEXT,
    screenshot_path  TEXT,
    scraped_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at     TIMESTAMP
);

-- 12. SCRAPED PRICES (parsed observations per scraping run)
CREATE TABLE scraped_prices (
    id                SERIAL PRIMARY KEY,
    -- One parsed observation per raw payload keeps ETL idempotent with ON CONFLICT(raw_staging_id).
    raw_staging_id    INTEGER UNIQUE REFERENCES raw_staging(id) ON DELETE SET NULL,
    product_variant_id INTEGER       NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    website_id        INTEGER        NOT NULL REFERENCES websites(id)         ON DELETE CASCADE,
    store_id          INTEGER                 REFERENCES stores(id)           ON DELETE CASCADE,
    current_price     DECIMAL(10, 2) NOT NULL CHECK (current_price > 0),
    base_price        DECIMAL(10, 2) NOT NULL CHECK (base_price > 0),
    is_discounted     BOOLEAN        NOT NULL DEFAULT FALSE,
    currency          VARCHAR(10)    NOT NULL,
    screenshot_path   TEXT,
    observed_at       TIMESTAMP      NOT NULL,
    created_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

-- 13. WEEKLY PRICE SUMMARY (weekly aggregates for analytics)
CREATE TABLE weekly_price_summary (
    id                SERIAL PRIMARY KEY,
    product_variant_id INTEGER       NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    website_id        INTEGER        NOT NULL REFERENCES websites(id)         ON DELETE CASCADE,
    store_id          INTEGER                 REFERENCES stores(id)           ON DELETE CASCADE,
    week_start        DATE           NOT NULL,
    avg_price         DECIMAL(10, 2),
    sample_count      INTEGER        NOT NULL DEFAULT 0,
    currency          VARCHAR(10)    NOT NULL,
    data_status       VARCHAR(20)    NOT NULL DEFAULT 'OK' CHECK (data_status IN ('OK', 'MISSING', 'PARTIAL')),
    created_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        (
            data_status = 'MISSING'
            AND avg_price IS NULL
            AND sample_count = 0
        )
        OR
        (
            data_status IN ('OK', 'PARTIAL')
            AND avg_price IS NOT NULL
            AND avg_price > 0
            AND sample_count > 0
        )
    )
);

-- 14. EXCHANGE RATES
CREATE TABLE exchange_rates (
    id          SERIAL PRIMARY KEY,
    currency    VARCHAR(10) NOT NULL,
    date        DATE        NOT NULL,
    rate_to_eur FLOAT       NOT NULL,
    UNIQUE(currency, date)
);

-- 15. USERS
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

CREATE INDEX idx_scraped_prices_variant_observed ON scraped_prices(product_variant_id, observed_at DESC);
CREATE INDEX idx_scraped_prices_website         ON scraped_prices(website_id);
CREATE INDEX idx_scraped_prices_store           ON scraped_prices(store_id);
CREATE INDEX idx_scraped_prices_observed        ON scraped_prices(observed_at DESC);

CREATE INDEX idx_weekly_summary_variant_start ON weekly_price_summary(product_variant_id, week_start DESC);
CREATE INDEX idx_weekly_summary_website      ON weekly_price_summary(website_id);
CREATE INDEX idx_weekly_summary_store        ON weekly_price_summary(store_id);
CREATE UNIQUE INDEX idx_weekly_summary_unique
    ON weekly_price_summary(product_variant_id, website_id, COALESCE(store_id, 0), week_start);

CREATE INDEX idx_product_urls_website     ON product_urls(website_id, product_variant_id);
CREATE INDEX idx_product_urls_store       ON product_urls(store_id);
CREATE INDEX idx_product_urls_active      ON product_urls(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_stores_website_code      ON stores(website_id, store_code);
CREATE INDEX idx_products_brand           ON products(brand_id);
CREATE INDEX idx_variants_product         ON product_variants(product_id);
CREATE INDEX idx_variants_format          ON product_variants(format_id);
CREATE INDEX idx_variants_packaging       ON product_variants(packaging_id);
CREATE INDEX idx_categories               ON categories(category_name);

CREATE INDEX idx_users_username           ON users(username);
CREATE INDEX idx_users_role               ON users(role);

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================