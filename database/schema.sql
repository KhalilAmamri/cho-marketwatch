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

-- 7. PRODUCT FORMATS (format + packaging = unique format per product)
CREATE TABLE product_formats (
    id         SERIAL PRIMARY KEY,
    product_id INTEGER     NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    format     VARCHAR(50) NOT NULL,
    packaging  VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, format, packaging)
);

-- 8. PRODUCT URLS (URL per website/format)
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

-- 9. RAW STAGING (raw scraped HTML)
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

-- 10. SCRAPED PRICES (parsed observations per scraping run)
CREATE TABLE scraped_prices (
    id                SERIAL PRIMARY KEY,
    -- One parsed observation per raw payload keeps ETL idempotent with ON CONFLICT(raw_staging_id).
    raw_staging_id    INTEGER UNIQUE REFERENCES raw_staging(id) ON DELETE SET NULL,
    product_format_id INTEGER        NOT NULL REFERENCES product_formats(id) ON DELETE CASCADE,
    website_id        INTEGER        NOT NULL REFERENCES websites(id)         ON DELETE CASCADE,
    store_id          INTEGER                 REFERENCES stores(id)           ON DELETE CASCADE,
    price             DECIMAL(10, 2) NOT NULL CHECK (price > 0),
    currency          VARCHAR(10)    NOT NULL,
    screenshot_path   TEXT,
    observed_at       TIMESTAMP      NOT NULL,
    created_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

-- 11. WEEKLY PRICE SUMMARY (weekly aggregates for analytics)
CREATE TABLE weekly_price_summary (
    id                SERIAL PRIMARY KEY,
    product_format_id INTEGER        NOT NULL REFERENCES product_formats(id) ON DELETE CASCADE,
    website_id        INTEGER        NOT NULL REFERENCES websites(id)         ON DELETE CASCADE,
    store_id          INTEGER                 REFERENCES stores(id)           ON DELETE CASCADE,
    week_start        DATE           NOT NULL,
    avg_price         DECIMAL(10, 2) NOT NULL CHECK (avg_price > 0),
    sample_count      INTEGER        NOT NULL CHECK (sample_count > 0),
    currency          VARCHAR(10)    NOT NULL,
    created_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

-- 12. EXCHANGE RATES
CREATE TABLE exchange_rates (
    id          SERIAL PRIMARY KEY,
    currency    VARCHAR(10) NOT NULL,
    date        DATE        NOT NULL,
    rate_to_eur FLOAT       NOT NULL,
    UNIQUE(currency, date)
);

-- 13. PRICE FORECASTS (persisted ML predictions)
CREATE TABLE price_forecasts (
    id                SERIAL PRIMARY KEY,
    product_format_id INTEGER        NOT NULL REFERENCES product_formats(id) ON DELETE CASCADE,
    website_id        INTEGER        NOT NULL REFERENCES websites(id)        ON DELETE CASCADE,
    store_id          INTEGER                 REFERENCES stores(id)          ON DELETE CASCADE,
    forecast_date     DATE           NOT NULL,
    predicted_price   DECIMAL(10, 2) NOT NULL CHECK (predicted_price >= 0),
    price_low         DECIMAL(10, 2)          CHECK (price_low >= 0),
    price_high        DECIMAL(10, 2)          CHECK (price_high >= 0),
    confidence_level  VARCHAR(20),
    training_points   INTEGER,
    created_at        TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- 14. USERS
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

CREATE INDEX idx_scraped_prices_format_observed ON scraped_prices(product_format_id, observed_at DESC);
CREATE INDEX idx_scraped_prices_website         ON scraped_prices(website_id);
CREATE INDEX idx_scraped_prices_store           ON scraped_prices(store_id);
CREATE INDEX idx_scraped_prices_observed        ON scraped_prices(observed_at DESC);

CREATE INDEX idx_weekly_summary_format_start ON weekly_price_summary(product_format_id, week_start DESC);
CREATE INDEX idx_weekly_summary_website      ON weekly_price_summary(website_id);
CREATE INDEX idx_weekly_summary_store        ON weekly_price_summary(store_id);
CREATE UNIQUE INDEX idx_weekly_summary_unique
    ON weekly_price_summary(product_format_id, website_id, COALESCE(store_id, 0), week_start);

CREATE INDEX idx_price_forecasts_product_store_date
    ON price_forecasts(product_format_id, website_id, store_id, forecast_date DESC);
CREATE UNIQUE INDEX idx_price_forecasts_unique
    ON price_forecasts(product_format_id, website_id, COALESCE(store_id, 0), forecast_date);

CREATE INDEX idx_product_urls_website     ON product_urls(website_id, product_format_id);
CREATE INDEX idx_product_urls_store       ON product_urls(store_id);
CREATE INDEX idx_product_urls_active      ON product_urls(is_active) WHERE is_active = TRUE;

CREATE INDEX idx_stores_website_code      ON stores(website_id, store_code);
CREATE INDEX idx_products_brand           ON products(brand_id);
CREATE INDEX idx_formats_product          ON product_formats(product_id);
CREATE INDEX idx_categories               ON categories(category_name);

CREATE INDEX idx_users_username           ON users(username);
CREATE INDEX idx_users_role               ON users(role);

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================