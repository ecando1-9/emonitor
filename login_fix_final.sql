-- ========================================
-- FIX LOGIN TRACKING (GUARANTEED CLEANUP)
-- ========================================

-- 1. Drop ALL possible variations of policies to ensure a clean slate
DROP POLICY IF EXISTS "Users can view their own login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Allow insert for login tracking" ON public.login_attempts;
DROP POLICY IF EXISTS "Allow system to insert login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Anon insert" ON public.login_attempts;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.login_attempts;

-- 2. NOW create the policies (No "already exists" error possible)

-- Select policy
CREATE POLICY "Users can view their own login attempts"
  ON public.login_attempts
  FOR SELECT
  TO authenticated
  USING (email = (SELECT email FROM auth.users WHERE id = auth.uid()));

-- Insert policy (Critical for 'Invalid Password' tracking)
CREATE POLICY "Allow system to insert login attempts"
  ON public.login_attempts
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- 3. Grant Permissions
GRANT SELECT, INSERT ON public.login_attempts TO anon, authenticated;
