DROP TRIGGER IF EXISTS protect_user_inserts ON users;
DROP TRIGGER IF EXISTS protect_user_updates ON users;
DROP TRIGGER IF EXISTS protect_user_deletes ON users;
DROP FUNCTION IF EXISTS enforce_user_permissions();

CREATE OR REPLACE FUNCTION enforce_user_permissions()
RETURNS trigger AS $$
DECLARE
    current_user_id INT;
    current_user_role TEXT;
    current_user_is_super BOOLEAN;
BEGIN
    -- Get the actor's ID from the PostgreSQL session
    BEGIN
        current_user_id := current_setting('app.current_user_id')::INT;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE EXCEPTION 'app.current_user_id must be set';
    END;

    -- Get actor's role and superuser status
    SELECT role, is_superuser INTO current_user_role, current_user_is_super
    FROM users WHERE id = current_user_id;

    -- ─────────────────────────────────────────────────────
    -- Handle INSERT
    -- ─────────────────────────────────────────────────────
    IF TG_OP = 'INSERT' THEN
        -- Prevent inserting superusers unless you're a superuser
        IF NEW.is_superuser AND NOT current_user_is_super THEN
            RAISE EXCEPTION 'Only a superuser can create another superuser';
        END IF;
        RETURN NEW;
    END IF;

    -- ─────────────────────────────────────────────────────
    -- Handle UPDATE
    -- ─────────────────────────────────────────────────────
    IF TG_OP = 'UPDATE' THEN
        -- Prevent modifying superusers unless you're a superuser
        IF OLD.is_superuser AND NOT current_user_is_super THEN
            RAISE EXCEPTION 'Only superusers can modify superuser accounts';
        END IF;

        -- Prevent changing is_superuser unless you're a superuser
        IF NEW.is_superuser IS DISTINCT FROM OLD.is_superuser AND NOT current_user_is_super THEN
            RAISE EXCEPTION 'Only superusers can modify is_superuser field';
        END IF;

        -- Prevent admin from modifying other admins
        IF OLD.role = 'admin' AND current_user_role = 'admin' AND current_user_id != OLD.id THEN
            RAISE EXCEPTION 'Admins cannot modify other admins';
        END IF;

        -- Prevent others from modifying anyone but themselves
        IF current_user_id != OLD.id AND NOT current_user_is_super AND current_user_role != 'admin' THEN
            RAISE EXCEPTION 'You are not authorized to modify this user';
        END IF;

        RETURN NEW;
    END IF;

    -- ─────────────────────────────────────────────────────
    -- Handle DELETE
    -- ─────────────────────────────────────────────────────
    IF TG_OP = 'DELETE' THEN
        -- Prevent deleting superusers unless you're a superuser
        IF OLD.is_superuser AND NOT current_user_is_super THEN
            RAISE EXCEPTION 'Only superusers can delete superuser accounts';
        END IF;

        -- Admins cannot delete other admins or superusers
        IF current_user_role = 'admin' THEN
            IF OLD.role = 'admin' AND current_user_id != OLD.id THEN
                RAISE EXCEPTION 'Admins cannot delete other admins';
            ELSIF OLD.is_superuser THEN
                RAISE EXCEPTION 'Admins cannot delete superusers';
            END IF;
        END IF;

        -- Regular users can only delete themselves
        IF current_user_role NOT IN ('admin') AND NOT current_user_is_super THEN
            RAISE EXCEPTION 'Regular users cannot delete accounts';
        END IF;

        RETURN OLD;
    END IF;
    
    RAISE EXCEPTION 'Unsupported operation %', TG_OP;
END;
$$ LANGUAGE plpgsql;

-- INSERT trigger
CREATE TRIGGER protect_user_inserts
BEFORE INSERT ON users
FOR EACH ROW
EXECUTE FUNCTION enforce_user_permissions();

-- UPDATE trigger
CREATE TRIGGER protect_user_updates
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION enforce_user_permissions();

-- DELETE trigger
CREATE TRIGGER protect_user_deletes
BEFORE DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION enforce_user_permissions();
-- ─────────────────────────────────────────────────────