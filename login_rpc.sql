-- ========================================
-- RPC: RECORD LOGIN ATTEMPT (Bypass RLS)
-- ========================================

-- Drop existing function if any
DROP FUNCTION IF EXISTS public.record_login_attempt(text, text, boolean);

-- Create secure function
CREATE OR REPLACE FUNCTION public.record_login_attempt(
  p_email text,
  p_device_hash text,
  p_success boolean
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER -- Runs as database owner (Bypasses RLS)
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.login_attempts (
    email,
    device_hash,
    success,
    attempt_time,
    ip_address
  ) VALUES (
    p_email,
    p_device_hash,
    p_success,
    NOW(),
    NULL -- IP address optional/not captured
  );
END;
$$;

-- Grant execute permission to everyone (anon + authenticated)
GRANT EXECUTE ON FUNCTION public.record_login_attempt(text, text, boolean) TO anon, authenticated;
