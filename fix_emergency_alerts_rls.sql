-- Fix Row-Level Security (RLS) Policy for emergency_alerts table
-- This allows authenticated users to insert their own emergency alerts
-- Run this in your Supabase SQL Editor

-- First, check if RLS is enabled (it should be)
ALTER TABLE public.emergency_alerts ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Users can insert their own emergency alerts" ON public.emergency_alerts;
DROP POLICY IF EXISTS "Users can view their own emergency alerts" ON public.emergency_alerts;
DROP POLICY IF EXISTS "Users can update their own emergency alerts" ON public.emergency_alerts;
DROP POLICY IF EXISTS "Admins can view all emergency alerts" ON public.emergency_alerts;

-- Policy 1: Allow authenticated users to INSERT their own emergency alerts
-- This checks that the user_id in the insert matches the authenticated user
CREATE POLICY "Users can insert their own emergency alerts"
ON public.emergency_alerts
FOR INSERT
TO authenticated
WITH CHECK (
    auth.uid() = user_id
);

-- Policy 2: Allow authenticated users to SELECT their own emergency alerts
CREATE POLICY "Users can view their own emergency alerts"
ON public.emergency_alerts
FOR SELECT
TO authenticated
USING (
    auth.uid() = user_id
);

-- Policy 3: Allow authenticated users to UPDATE their own emergency alerts
CREATE POLICY "Users can update their own emergency alerts"
ON public.emergency_alerts
FOR UPDATE
TO authenticated
USING (
    auth.uid() = user_id
)
WITH CHECK (
    auth.uid() = user_id
);

-- Policy 4: Allow service role (admin) to view all emergency alerts
-- This is useful for admin panel access
-- Note: service_role bypasses RLS by default, but this is here for completeness
CREATE POLICY "Service role can view all emergency alerts"
ON public.emergency_alerts
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Verify the policies were created
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE tablename = 'emergency_alerts';

-- Test query to verify RLS is working
-- This should return your emergency alerts if you're logged in
SELECT COUNT(*) as total_alerts FROM public.emergency_alerts;

