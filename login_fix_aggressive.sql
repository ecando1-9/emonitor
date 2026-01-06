-- ========================================
-- FIX LOGIN TRACKING (AGGRESSIVE PERMISSIONS)
-- ========================================

-- 1. Reset RLS (Disable temporarily to clear state)
ALTER TABLE public.login_attempts DISABLE ROW LEVEL SECURITY;

-- 2. Clean up policies
DROP POLICY IF EXISTS "Users can view their own login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Allow system to insert login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Anon insert" ON public.login_attempts;

-- 3. Re-Enable RLS
ALTER TABLE public.login_attempts ENABLE ROW LEVEL SECURITY;

-- 4. Create Policies (SELECT is restricted, INSERT is OPEN)
CREATE POLICY "Users can view their own login attempts"
  ON public.login_attempts
  FOR SELECT
  TO authenticated
  USING (email = (SELECT email FROM auth.users WHERE id = auth.uid()));

CREATE POLICY "Allow system to insert login attempts"
  ON public.login_attempts
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- 5. *** CRITICAL STEP: GRANT PERMISSIONS ***
-- This is likely the missing piece if it was failing before
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON public.login_attempts TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- 6. Verify (Optional comment)
-- If this fails, then 'anon' role is strictly locked down at project level.
