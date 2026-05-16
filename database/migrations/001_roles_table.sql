-- Migration: Normalize user roles into a dedicated roles table.
-- Applies to the legacy schema where `users.role` is a VARCHAR with a CHECK constraint.
--
-- Notes:
-- - This migration is designed to be safe to run once.
-- - It keeps API behavior unchanged: the backend still exposes role as a name (e.g., 'admin', 'user').
--
-- Recommended: take a DB backup before running.

BEGIN;

-- 1) Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2) Ensure default roles exist
INSERT INTO roles (name)
VALUES ('admin'), ('user')
ON CONFLICT (name) DO NOTHING;

-- 3) Add role_id column on users
ALTER TABLE users ADD COLUMN IF NOT EXISTS role_id INTEGER;

-- 4) Backfill role_id from legacy users.role (if it exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'role'
    ) THEN
        UPDATE users u
        SET role_id = r.id
        FROM roles r
        WHERE r.name = u.role
          AND (u.role_id IS NULL);
    END IF;
END $$;

-- 5) Any remaining NULLs become 'user'
UPDATE users
SET role_id = (SELECT id FROM roles WHERE name = 'user')
WHERE role_id IS NULL;

-- 6) Add FK constraint (idempotent)
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_role_id_fkey;
ALTER TABLE users
    ADD CONSTRAINT users_role_id_fkey
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE RESTRICT;

-- 7) Make role_id required
ALTER TABLE users ALTER COLUMN role_id SET NOT NULL;

-- 8) Set default role_id to the current 'user' role id
DO $$
DECLARE
    user_role_id INTEGER;
BEGIN
    SELECT id INTO user_role_id FROM roles WHERE name = 'user' LIMIT 1;
    IF user_role_id IS NOT NULL THEN
        EXECUTE format('ALTER TABLE users ALTER COLUMN role_id SET DEFAULT %s', user_role_id);
    END IF;
END $$;

-- 9) Drop legacy role column if present
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'role'
    ) THEN
        ALTER TABLE users DROP COLUMN role;
    END IF;
END $$;

-- 10) Index
DROP INDEX IF EXISTS idx_users_role;
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);

COMMIT;
