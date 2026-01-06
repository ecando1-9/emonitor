-- ========================================
-- RPC: CHECK LOGIN ATTEMPTS (Secure Read)
-- ========================================

DROP FUNCTION IF EXISTS public.check_is_blocked(text);

-- Create secure function to check if user is blocked
CREATE OR REPLACE FUNCTION public.check_is_blocked(
  p_email text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER -- Runs as admin
SET search_path = public
AS $$
DECLARE
  failed_count integer;
BEGIN
  -- Count failed attempts in last 10 minutes
  SELECT COUNT(*) INTO failed_count
  FROM public.login_attempts
  WHERE email = p_email
  AND success = false
  AND attempt_time > (NOW() - INTERVAL '10 minutes');

  -- Return true if blocked (>= 5 attempts)
  RETURN failed_count >= 5;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.check_is_blocked(text) TO anon, authenticated;
