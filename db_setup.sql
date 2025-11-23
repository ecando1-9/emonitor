-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.audit_logs (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  timestamp timestamp with time zone DEFAULT now(),
  user_id uuid,
  device_hash text,
  action text NOT NULL,
  details jsonb,
  CONSTRAINT audit_logs_pkey PRIMARY KEY (id),
  CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.devices (
  device_hash text NOT NULL,
  trial_count integer NOT NULL DEFAULT 0,
  last_user_id uuid,
  first_seen timestamp with time zone DEFAULT now(),
  last_seen timestamp with time zone DEFAULT now(),
  is_blocked boolean DEFAULT false,
  CONSTRAINT devices_pkey PRIMARY KEY (device_hash),
  CONSTRAINT devices_last_user_id_fkey FOREIGN KEY (last_user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.emergency_alerts (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  user_id uuid,
  device_hash text,
  last_location jsonb,
  activity_summary text,
  status text NOT NULL DEFAULT 'new'::text,
  acknowledged_by uuid,
  acknowledged_at timestamp with time zone,
  notes text,
  CONSTRAINT emergency_alerts_pkey PRIMARY KEY (id),
  CONSTRAINT emergency_alerts_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
  CONSTRAINT emergency_alerts_device_hash_fkey FOREIGN KEY (device_hash) REFERENCES public.devices(device_hash),
  CONSTRAINT emergency_alerts_acknowledged_by_fkey FOREIGN KEY (acknowledged_by) REFERENCES auth.users(id)
);
CREATE TABLE public.sender_assignments (
  user_id uuid NOT NULL,
  smtp_server text NOT NULL,
  smtp_port text NOT NULL,
  smtp_email text NOT NULL,
  smtp_password text NOT NULL,
  assigned_at timestamp with time zone DEFAULT now(),
  CONSTRAINT sender_assignments_pkey PRIMARY KEY (user_id),
  CONSTRAINT sender_assignments_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id)
);
CREATE TABLE public.sender_pool (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  smtp_server text NOT NULL,
  smtp_port text NOT NULL,
  smtp_email text NOT NULL UNIQUE,
  smtp_password text NOT NULL,
  max_users integer NOT NULL DEFAULT 10,
  assigned_count integer NOT NULL DEFAULT 0,
  CONSTRAINT sender_pool_pkey PRIMARY KEY (id)
);
CREATE TABLE public.subscriptions (
  user_id uuid NOT NULL,
  status text NOT NULL DEFAULT 'trialing'::text,
  plan_name text DEFAULT 'trial'::text,
  trial_ends_at timestamp with time zone,
  stripe_customer_id text UNIQUE,
  device_hash text,
  CONSTRAINT subscriptions_pkey PRIMARY KEY (user_id),
  CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id),
  CONSTRAINT subscriptions_device_hash_fkey FOREIGN KEY (device_hash) REFERENCES public.devices(device_hash)
);