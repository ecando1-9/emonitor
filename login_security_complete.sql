-- ========================================
-- COMPLETE LOGIN SECURITY SETUP (One-Click Fix)
-- ========================================

-- 1. Create Table (if missing)
CREATE TABLE IF NOT EXISTS public.login_attempts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL,
  device_hash text,
  attempt_time timestamp with time zone DEFAULT now(),
  success boolean DEFAULT false,
  ip_address text,
  CONSTRAINT login_attempts_pkey PRIMARY KEY (id)
);

-- 2. Create Indexes
CREATE INDEX IF NOT EXISTS login_attempts_email_idx ON public.login_attempts(email);
CREATE INDEX IF NOT EXISTS login_attempts_time_idx ON public.login_attempts(attempt_time);

-- 3. Reset Permissions (Hard Reset)
ALTER TABLE public.login_attempts ENABLE ROW LEVEL SECURITY;

-- Drop all old policies to avoid conflicts
DROP POLICY IF EXISTS "Users can view their own login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Allow system to insert login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Anon insert" ON public.login_attempts;

-- Create correct policies
CREATE POLICY "Users can view their own login attempts"
  ON public.login_attempts FOR SELECT TO authenticated
  USING (email = (SELECT email FROM auth.users WHERE id = auth.uid()));

CREATE POLICY "Allow system to insert login attempts"
  ON public.login_attempts FOR INSERT TO anon, authenticated
  WITH CHECK (true);

GRANT SELECT, INSERT ON public.login_attempts TO anon, authenticated;

-- 4. Create WRITE Function (RPC) - Bypasses RLS for Logging
DROP FUNCTION IF EXISTS public.record_login_attempt(text, text, boolean);

CREATE OR REPLACE FUNCTION public.record_login_attempt(p_email text, p_device_hash text, p_success boolean)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.login_attempts (email, device_hash, success, attempt_time)
  VALUES (p_email, p_device_hash, p_success, NOW());
END;
$$;
GRANT EXECUTE ON FUNCTION public.record_login_attempt(text, text, boolean) TO anon, authenticated;

-- 5. Create READ Function (RPC) - Bypasses RLS to Check Block Status
DROP FUNCTION IF EXISTS public.check_is_blocked(text);

CREATE OR REPLACE FUNCTION public.check_is_blocked(p_email text)
RETURNS boolean LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  failed_count integer;
BEGIN
  SELECT COUNT(*) INTO failed_count
  FROM public.login_attempts
  WHERE email = p_email AND success = false AND attempt_time > (NOW() - INTERVAL '10 minutes');
  RETURN failed_count >= 5;
END;
$$;
GRANT EXECUTE ON FUNCTION public.check_is_blocked(text) TO anon, authenticated;

-- 6. Refresh Schema Cache
NOTIFY pgrst, 'reload schema';
