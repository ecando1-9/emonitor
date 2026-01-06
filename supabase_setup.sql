ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can insert their own data" ON public.users;
DROP POLICY IF EXISTS "Users can view their own data" ON public.users;
DROP POLICY IF EXISTS "Users can update their own data" ON public.users;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.users;
DROP POLICY IF EXISTS "Enable read access for users" ON public.users;
DROP POLICY IF EXISTS "Enable update for users" ON public.users;

CREATE POLICY "Enable insert for authenticated users only"
  ON public.users
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Enable read access for users"
  ON public.users
  FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Enable update for users"
  ON public.users
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON public.users TO authenticated;

CREATE INDEX IF NOT EXISTS users_email_idx ON public.users(email);
CREATE INDEX IF NOT EXISTS users_device_hash_idx ON public.users(device_hash);

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can insert their own subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "Users can view their own subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "Users can update their own subscription" ON public.subscriptions;

CREATE POLICY "Users can insert their own subscription"
  ON public.subscriptions
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own subscription"
  ON public.subscriptions
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own subscription"
  ON public.subscriptions
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE ON public.subscriptions TO authenticated;

INSERT INTO public.plans (id, name, price, price_original, features)
VALUES (
  'free',
  'Free Trial',
  0,
  0,
  ARRAY[
    'TELEMETRY',
    'ACTIVITY_SUMMARY',
    'SCREENSHOT',
    'REPORT_SCHEDULE',
    'SCREEN_RECORD',
    'CAMERA',
    'MICROPHONE',
    'ADVANCED_ACTIVITY',
    'TYPING_INTENSITY'
  ]
)
ON CONFLICT (id) DO UPDATE
SET features = EXCLUDED.features;

ALTER TABLE public.app_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Anyone can read app config" ON public.app_config;
DROP POLICY IF EXISTS "Only admins can update config" ON public.app_config;

CREATE POLICY "Anyone can read app config"
  ON public.app_config
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "Only admins can update config"
  ON public.app_config
  FOR ALL
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.admin_roles
      WHERE user_id = auth.uid()
      AND is_active = true
    )
  );

INSERT INTO public.app_config (key, value, description)
VALUES 
  ('free_trial_days', '7', 'Number of days for free trial'),
  ('auto_create_trial', 'true', 'Automatically create trial on signup')
ON CONFLICT (key) DO NOTHING;

GRANT SELECT ON public.app_config TO authenticated;
