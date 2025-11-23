-- Migration script to add phone and emergency contacts columns to emergency_alerts table
-- Run this in your Supabase SQL editor

ALTER TABLE public.emergency_alerts
ADD COLUMN IF NOT EXISTS user_phone text,
ADD COLUMN IF NOT EXISTS emergency_contacts jsonb DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS user_email text,
ADD COLUMN IF NOT EXISTS user_name text,
ADD COLUMN IF NOT EXISTS device_name text;

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_user_phone ON public.emergency_alerts(user_phone);
CREATE INDEX IF NOT EXISTS idx_emergency_alerts_user_email ON public.emergency_alerts(user_email);

