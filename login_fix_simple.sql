-- ========================================
-- FIX LOGIN TRACKING (Simplified)
-- ========================================

-- 1. Drop the specific policy causing issues (to be safe)
DROP POLICY IF EXISTS "Users can view their own login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Allow insert for login tracking" ON public.login_attempts;
DROP POLICY IF EXISTS "Allow system to insert login attempts" ON public.login_attempts;
DROP POLICY IF EXISTS "Anon insert" ON public.login_attempts;

-- 2. Re-create the SELECT policy
CREATE POLICY "Users can view their own login attempts"
  ON public.login_attempts
  FOR SELECT
  TO authenticated
  USING (email = (SELECT email FROM auth.users WHERE id = auth.uid()));

-- 3. Create the INSERT policy (THIS IS THE CRITICAL FIX)
CREATE POLICY "Allow system to insert login attempts"
  ON public.login_attempts
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

-- 4. Ensure permissions are granted
GRANT SELECT, INSERT ON public.login_attempts TO anon, authenticated;
