-- Migration: Add emergency features and contact management fields
-- This migration adds new fields to emergency_alerts and related tables for comprehensive emergency alert tracking

-- Update emergency_alerts table with new fields for user information and email tracking
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS user_name text;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS user_phone text;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS user_email text;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS device_name text;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS triggered_at timestamp with time zone;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS email_details jsonb DEFAULT '{}'::jsonb;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS emergency_contacts_notified jsonb DEFAULT '[]'::jsonb;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS emergency_contacts jsonb DEFAULT '[]'::jsonb;
ALTER TABLE public.emergency_alerts ADD COLUMN IF NOT EXISTS data_shared jsonb DEFAULT '{
  "screenshot": false,
  "device_info": false,
  "last_location": false,
  "activity_summary": false,
  "logs": false
}'::jsonb;

-- Update user profiles table (if using auth.users) or create a user_profiles table for extended info
-- Note: This assumes the table exists. If using a custom user table, adjust accordingly.
CREATE TABLE IF NOT EXISTS public.user_emergency_settings (
  user_id uuid NOT NULL PRIMARY KEY,
  emergency_contacts jsonb DEFAULT '[]'::jsonb,
  data_sharing_preferences jsonb DEFAULT '{
    "screenshot": false,
    "device_info": false,
    "last_location": false,
    "activity_summary": false,
    "logs": false
  }'::jsonb,
  phone text,
  user_name text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now(),
  CONSTRAINT user_emergency_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_user_id ON public.emergency_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_created_at ON public.emergency_alerts(created_at);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_status ON public.emergency_alerts(status);
CREATE INDEX IF NOT EXISTS idx_user_emergency_settings_user_id ON public.user_emergency_settings(user_id);

-- Add RLS policies if using Supabase (optional, enable if your schema uses RLS)
-- ALTER TABLE public.emergency_alerts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.user_emergency_settings ENABLE ROW LEVEL SECURITY;
