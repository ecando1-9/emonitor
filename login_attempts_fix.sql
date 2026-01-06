-- ========================================
-- LOGIN ATTEMPTS TABLE & SECURITY (FIXED)
-- ========================================

-- 1. Create table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.login_attempts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL,
  device_hash text,
  attempt_time timestamp with time zone DEFAULT now(),
  success boolean DEFAULT false,
  ip_address text,
  CONSTRAINT login_attempts_pkey PRIMARY KEY (id)
);

-- 2. Create indexes for performance
CREATE INDEX IF NOT EXISTS login_attempts_email_idx ON public.login_attempts(email);
CREATE INDEX IF NOT EXISTS login_attempts_device_hash_idx ON public.login_attempts(device_hash);
CREATE INDEX IF NOT EXISTS login_attempts_time_idx ON public.login_attempts(attempt_time);

-- 3. Enable RLS
ALTER TABLE public.login_attempts ENABLE ROW LEVEL SECURITY;

-- 4. DROP EXISTING POLICIES (Important to avoid conflicts)
DROP POLICY IF EXISTS "Users can view their own login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Allow insert for login tracking" ON public.login_attempts;
DROP POLICY IF EXISTS "Anon insert" ON public.login_attempts;

-- 5. CREATE POLICIES

-- Policy: Authenticated users can see their own logs
CREATE POLICY "Users can view their own login attempts"
  ON public.login_attempts
  FOR SELECT
  TO authenticated
  USING (email = (SELECT email FROM auth.users WHERE id = auth.uid()));

-- Policy: EVERYONE (Anonymous + User) can INSERT logs
-- This is critical for tracking failed logins
CREATE POLICY "Allow system to insert login attempts"
  ON public.login_attempts
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- 6. GRANT PERMISSIONS
GRANT SELECT, INSERT ON public.login_attempts TO anon, authenticated;
GRANT USAGE ON SEQUENCE login_attempts_id_seq TO anon, authenticated; -- If serial (not needed for uuid but good practice)
