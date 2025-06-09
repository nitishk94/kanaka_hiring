CREATE OR REPLACE FUNCTION enforce_user_permissions()
RETURNS trigger AS $$
DECLARE
    current_user_id INT;
    current_user_role TEXT;
    current_user_is_super BOOLEAN;
BEGIN
    -- Get the actor's ID from the PostgreSQL session
    current_user_id := current_setting('app.current_user_id')::int;

    -- Get actor's role and superuser status
    SELECT role, is_superuser INTO current_user_role, current_user_is_super
    FROM users WHERE id = current_user_id;

    -- ─────────────────────────────────────────────────────
    -- Handle DELETE
    -- ─────────────────────────────────────────────────────
    IF TG_OP = 'DELETE' THEN
        -- Prevent deleting superuser unless you're also a superuser
        IF OLD.is_superuser AND NOT current_user_is_super THEN
            RAISE EXCEPTION 'Only a superuser can delete a superuser';
        END IF;

        -- Prevent admin from deleting other admins
        IF OLD.role = 'admin' AND current_user_role = 'admin' AND current_user_id != OLD.id THEN
            RAISE EXCEPTION 'Admins cannot delete other admins';
        END IF;

        -- Prevent others from deleting any user except themselves
        IF current_user_id != OLD.id AND NOT current_user_is_super AND current_user_role != 'admin' THEN
            RAISE EXCEPTION 'You are not authorized to delete this user';
        END IF;

        RETURN OLD;
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

    -- Fallback return (should never hit this)
    RAISE EXCEPTION 'Unsupported operation';
END;
$$ LANGUAGE plpgsql;

-- Trigger for UPDATE
CREATE TRIGGER protect_user_updates
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION enforce_user_permissions();

-- Trigger for DELETE
CREATE TRIGGER protect_user_deletes
BEFORE DELETE ON users
FOR EACH ROW
EXECUTE FUNCTION enforce_user_permissions();
-- ─────────────────────────────────────────────────────