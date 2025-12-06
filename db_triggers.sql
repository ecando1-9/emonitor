-- Trigger: handle_new_user_setup
-- This function assigns an available SMTP sender from public.sender_pool to a newly created user
-- Run this in the Supabase SQL editor (SQL) to create the function and trigger on auth.users

BEGIN;

-- Create the function
CREATE OR REPLACE FUNCTION public.handle_new_user_setup()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_id bigint;
    v_smtp_server text;
    v_smtp_port text;
    v_smtp_email text;
    v_smtp_password text;
    v_max_users integer;
    v_assigned_count integer;
BEGIN
    -- Try to select one available sender with lowest assigned_count
    -- Use FOR UPDATE SKIP LOCKED to avoid race conditions when multiple users sign up concurrently
    SELECT id, smtp_server, smtp_port, smtp_email, smtp_password, max_users, assigned_count
    INTO v_id, v_smtp_server, v_smtp_port, v_smtp_email, v_smtp_password, v_max_users, v_assigned_count
    FROM public.sender_pool
    WHERE (COALESCE(is_active, true) = true)
      AND (v_max_users IS NULL OR assigned_count < max_users)
    ORDER BY assigned_count ASC NULLS FIRST
    FOR UPDATE SKIP LOCKED
    LIMIT 1;

    -- If no sender found, do nothing (client will fallback to config option)
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    -- Increment assigned_count for chosen sender
    UPDATE public.sender_pool
    SET assigned_count = COALESCE(assigned_count, 0) + 1
    WHERE id = v_id;

    -- Insert assignment record (if not exists) in sender_assignments
    -- sender_assignments primary key is user_id so this maps one-to-one
    BEGIN
        INSERT INTO public.sender_assignments (user_id, smtp_server, smtp_port, smtp_email, smtp_password, assigned_at)
        VALUES (NEW.id, v_smtp_server, v_smtp_port, v_smtp_email, v_smtp_password, now());
    EXCEPTION WHEN unique_violation THEN
        -- If assignment already exists, ignore
        NULL;
    END;

    RETURN NEW;
END;
$$;

-- Create trigger on auth.users to run AFTER INSERT
-- Note: Supabase uses schema `auth` for users table
DROP TRIGGER IF EXISTS trg_handle_new_user_setup ON auth.users;
CREATE TRIGGER trg_handle_new_user_setup
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.handle_new_user_setup();

COMMIT;

-- Notes:
-- 1) Ensure your `sender_pool` table contains an `is_active` boolean column and `assigned_count`/`max_users` columns.
-- 2) This function uses `COALESCE(is_active, true)` to treat NULL as active for backward compatibility.
-- 3) If you prefer to only use service-side assignment, run this SQL in the Supabase SQL editor using the SQL role.
