CREATE TABLE IF NOT EXISTS public.login_attempts (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  email text NOT NULL,
  device_hash text,
  attempt_time timestamp with time zone DEFAULT now(),
  success boolean DEFAULT false,
  ip_address text,
  CONSTRAINT login_attempts_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS login_attempts_email_idx ON public.login_attempts(email);
CREATE INDEX IF NOT EXISTS login_attempts_device_hash_idx ON public.login_attempts(device_hash);
CREATE INDEX IF NOT EXISTS login_attempts_time_idx ON public.login_attempts(attempt_time);

ALTER TABLE public.login_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own login attempts"
  ON public.login_attempts
  FOR SELECT
  TO authenticated
  USING (email = (SELECT email FROM auth.users WHERE id = auth.uid()));

CREATE POLICY "Allow insert for login tracking"
  ON public.login_attempts
  FOR INSERT
  TO anon, authenticated
  WITH CHECK (true);

GRANT SELECT, INSERT ON public.login_attempts TO anon, authenticated;
