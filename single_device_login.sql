ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS active_device_hash text,
ADD COLUMN IF NOT EXISTS active_session_id text,
ADD COLUMN IF NOT EXISTS last_active timestamp with time zone DEFAULT now();

CREATE INDEX IF NOT EXISTS users_active_device_idx ON public.users(active_device_hash);
CREATE INDEX IF NOT EXISTS users_last_active_idx ON public.users(last_active);
