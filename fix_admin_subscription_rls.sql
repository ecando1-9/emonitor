-- FIX: Allow Admin to Updates Subscriptions (RLS Policy)

-- 1. Create a policy allowing Admins to UPDATE any subscription
DROP POLICY IF EXISTS "Admins can update any subscription" ON public.subscriptions;

CREATE POLICY "Admins can update any subscription"
  ON public.subscriptions
  FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.admin_roles
      WHERE user_id = auth.uid()
      AND is_active = true
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.admin_roles
      WHERE user_id = auth.uid()
      AND is_active = true
    )
  );

-- 2. Allow Admins to INSERT subscriptions (for manual assignment)
DROP POLICY IF EXISTS "Admins can insert any subscription" ON public.subscriptions;

CREATE POLICY "Admins can insert any subscription"
  ON public.subscriptions
  FOR INSERT
  TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM public.admin_roles
      WHERE user_id = auth.uid()
      AND is_active = true
    )
  );

-- 3. Allow Admins to VIEW all subscriptions
DROP POLICY IF EXISTS "Admins can view all subscriptions" ON public.subscriptions;

CREATE POLICY "Admins can view all subscriptions"
  ON public.subscriptions
  FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.admin_roles
      WHERE user_id = auth.uid()
      AND is_active = true
    )
  );

-- 4. Ensure admin_roles is readable by admins
ALTER TABLE public.admin_roles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Admins can read admin_roles" ON public.admin_roles;

CREATE POLICY "Admins can read admin_roles"
  ON public.admin_roles
  FOR SELECT
  TO authenticated
  USING (
     user_id = auth.uid()  -- User can see their own role
     OR EXISTS (           -- OR existing admins can check other roles
        SELECT 1 FROM public.admin_roles a 
        WHERE a.user_id = auth.uid() 
        AND a.is_active = true
     )
  );

GRANT ALL ON public.subscriptions TO authenticated;
