-- ========================================
-- ADMIN ROLES SETUP
-- ========================================
-- This table is required for admin-only features like fetching login history
-- and updating global app configuration.

-- 1. Create admin_roles table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.admin_roles (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'admin',
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT admin_roles_pkey PRIMARY KEY (id),
  CONSTRAINT admin_roles_user_id_key UNIQUE (user_id)
);

-- 2. Enable RLS
ALTER TABLE public.admin_roles ENABLE ROW LEVEL SECURITY;

-- 3. Policies for admin_roles
-- Only admins can view the roles table (circular, but standard pattern)
-- (Or better: users can view their own role)
DROP POLICY IF EXISTS "Users can view their own admin status" ON public.admin_roles;
CREATE POLICY "Users can view their own admin status"
  ON public.admin_roles
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- 4. Grant permissions
GRANT SELECT ON public.admin_roles TO authenticated;

-- ========================================
-- SECURE LOGIN HISTORY RPC
-- ========================================

DROP FUNCTION IF EXISTS public.get_login_history_secure(text);

CREATE OR REPLACE FUNCTION public.get_login_history_secure(
  target_email text
)
RETURNS SETOF public.login_attempts
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Verify admin access using the table created above
  IF NOT EXISTS (
    SELECT 1 FROM public.admin_roles
    WHERE user_id = auth.uid()
    AND is_active = true
  ) THEN
    RAISE EXCEPTION 'Access denied: Only admins can view login history';
  END IF;

  -- Return login attempts
  RETURN QUERY
  SELECT * FROM public.login_attempts
  WHERE email = target_email
  ORDER BY attempt_time DESC
  LIMIT 100;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION public.get_login_history_secure(text) TO authenticated;
