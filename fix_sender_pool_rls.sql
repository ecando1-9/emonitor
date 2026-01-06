-- Robust Fix for Database RLS and Sender Management
-- This script fixes permission errors for sender_pool and emergency_alerts tables
-- It introduces secure RPC functions for safe database operations

-- ============================================================================
-- PART 1: Secure Sender Management (RPC)
-- ============================================================================

-- Function to safely increment sender assigned_count
-- This function is SECURITY DEFINER, meaning it runs with the privileges of the creator (postgres)
-- This avoids the need for broad UPDATE permissions on the sender_pool table
DROP FUNCTION IF EXISTS public.increment_sender_assigned_count(UUID);
CREATE OR REPLACE FUNCTION public.increment_sender_assigned_count(sender_id_to_inc UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.sender_pool
    SET assigned_count = COALESCE(assigned_count, 0) + 1
    WHERE id = sender_id_to_inc;
END;
$$;

-- Allow authenticated users to call this function
REVOKE ALL ON FUNCTION public.increment_sender_assigned_count(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.increment_sender_assigned_count(UUID) TO authenticated;

-- ============================================================================
-- PART 2: Secure Emergency Contacts Update (RPC)
-- ============================================================================

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS public.update_emergency_contacts_notified(bigint, jsonb, integer);

-- Create secure function to update emergency_contacts_notified
-- This function runs with elevated privileges but checks ownership for security
CREATE FUNCTION public.update_emergency_contacts_notified(
    alert_id bigint,
    contacts jsonb,
    contacts_count integer
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Security check: Ensure the caller is the owner of the alert
    IF (SELECT user_id FROM public.emergency_alerts WHERE id = alert_id) IS DISTINCT FROM (SELECT auth.uid()) THEN
        RAISE EXCEPTION 'permission denied: you can only update your own emergency alerts';
    END IF;
    
    -- Update only the emergency contacts notification fields
    UPDATE public.emergency_alerts
    SET 
        emergency_contacts_notified = contacts,
        emergency_contacts_notified_count = contacts_count
    WHERE id = alert_id;
END;
$$;

-- Grant EXECUTE permission to authenticated users only
REVOKE ALL ON FUNCTION public.update_emergency_contacts_notified(bigint, jsonb, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_emergency_contacts_notified(bigint, jsonb, integer) TO authenticated;

-- ============================================================================
-- PART 3: Secure Email Status Update (RPC)
-- ============================================================================

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS public.update_emergency_email_status(bigint, jsonb);

-- Create secure function to update email status flags
-- This function runs with elevated privileges but checks ownership for security
CREATE FUNCTION public.update_emergency_email_status(
    alert_id bigint,
    email_status jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Security check: Ensure the caller is the owner of the alert
    IF (SELECT user_id FROM public.emergency_alerts WHERE id = alert_id) IS DISTINCT FROM (SELECT auth.uid()) THEN
        RAISE EXCEPTION 'permission denied: you can only update your own emergency alerts';
    END IF;
    
    -- Update email status fields dynamically based on what's provided in the JSON
    UPDATE public.emergency_alerts
    SET 
        email_sent_to_user = COALESCE((email_status->>'email_sent_to_user')::boolean, email_sent_to_user),
        email_sent_to_admin = COALESCE((email_status->>'email_sent_to_admin')::boolean, email_sent_to_admin),
        email_sent_to_user_at = CASE 
            WHEN email_status->>'email_sent_to_user_at' IS NOT NULL 
            THEN (email_status->>'email_sent_to_user_at')::timestamptz 
            ELSE email_sent_to_user_at 
        END,
        email_sent_to_admin_at = CASE 
            WHEN email_status->>'email_sent_to_admin_at' IS NOT NULL 
            THEN (email_status->>'email_sent_to_admin_at')::timestamptz 
            ELSE email_sent_to_admin_at 
        END,
        email_details = COALESCE(email_status->'email_details', email_details),
        users_notified_count = COALESCE((email_status->>'users_notified_count')::integer, users_notified_count),
        admins_notified = COALESCE(email_status->'admins_notified', admins_notified)
    WHERE id = alert_id;
END;
$$;

-- Grant EXECUTE permission to authenticated users only
REVOKE ALL ON FUNCTION public.update_emergency_email_status(bigint, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_emergency_email_status(bigint, jsonb) TO authenticated;

-- ============================================================================
-- PART 4: Secure Periodic Alert Update (RPC)
-- ============================================================================

-- Drop existing function if it exists
DROP FUNCTION IF EXISTS public.update_emergency_alert_periodic(bigint, jsonb);

-- Create secure function to update emergency alert during active emergency
-- This handles the 30-second periodic updates with location, activity, etc.
CREATE FUNCTION public.update_emergency_alert_periodic(
    alert_id bigint,
    alert_data jsonb
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- Security check: Ensure the caller is the owner of the alert
    IF (SELECT user_id FROM public.emergency_alerts WHERE id = alert_id) IS DISTINCT FROM (SELECT auth.uid()) THEN
        RAISE EXCEPTION 'permission denied: you can only update your own emergency alerts';
    END IF;
    
    -- Update alert with periodic data
    UPDATE public.emergency_alerts
    SET 
        last_location = COALESCE(alert_data->'last_location', last_location),
        activity_summary = COALESCE(alert_data->>'activity_summary', activity_summary),
        user_phone = COALESCE(alert_data->>'user_phone', user_phone),
        emergency_contacts = COALESCE(alert_data->'emergency_contacts', emergency_contacts),
        user_email = COALESCE(alert_data->>'user_email', user_email),
        user_name = COALESCE(alert_data->>'user_name', user_name),
        device_name = COALESCE(alert_data->>'device_name', device_name),
        status = COALESCE(alert_data->>'status', status),
        email_details = COALESCE(alert_data->'email_details', email_details)
    WHERE id = alert_id;
END;
$$;

-- Grant EXECUTE permission to authenticated users only
REVOKE ALL ON FUNCTION public.update_emergency_alert_periodic(bigint, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.update_emergency_alert_periodic(bigint, jsonb) TO authenticated;

-- ============================================================================
-- PART 5: sender_pool Table Policies
-- ============================================================================

ALTER TABLE public.sender_pool ENABLE ROW LEVEL SECURITY;

-- Drop old broad update policy if it exists
DROP POLICY IF EXISTS "Authenticated users can update sender_pool assigned_count" ON public.sender_pool;
DROP POLICY IF EXISTS "Authenticated users can read sender_pool" ON public.sender_pool;

-- Policy: Allow authenticated users to SELECT from sender_pool
-- Robust check: ensures only active senders are visible (optional, but good for security)
CREATE POLICY "Authenticated users can read sender_pool"
ON public.sender_pool
FOR SELECT
TO authenticated
USING (is_active = true);

-- ============================================================================
-- PART 4: emergency_alerts Table Policies
-- ============================================================================

ALTER TABLE public.emergency_alerts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can insert their own emergency alerts" ON public.emergency_alerts;
DROP POLICY IF EXISTS "Users can view their own emergency alerts" ON public.emergency_alerts;
DROP POLICY IF EXISTS "Users can update their own emergency alerts" ON public.emergency_alerts;
DROP POLICY IF EXISTS "Service role can view all emergency alerts" ON public.emergency_alerts;

-- Policy: Allow users to INSERT their own alerts
CREATE POLICY "Users can insert their own emergency alerts"
ON public.emergency_alerts
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Policy: Allow users to SELECT their own alerts
CREATE POLICY "Users can view their own emergency alerts"
ON public.emergency_alerts
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy: Allow users to UPDATE their own alerts (essential for telemetry updates)
CREATE POLICY "Users can update their own emergency alerts"
ON public.emergency_alerts
FOR UPDATE
TO authenticated
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Policy: Allow service role (admin) to view all
CREATE POLICY "Service role can view all emergency alerts"
ON public.emergency_alerts
FOR SELECT
TO service_role
USING (true);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these to check status:
-- SELECT * FROM pg_policies WHERE tablename IN ('sender_pool', 'emergency_alerts');
-- SELECT has_function_privilege('authenticated', 'increment_sender_assigned_count(UUID)', 'execute');
-- SELECT has_function_privilege('authenticated', 'update_emergency_contacts_notified(bigint, jsonb, integer)', 'execute');
