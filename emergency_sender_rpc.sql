-- Function to get a random active sender for emergency alerts
-- This bypasses RLS to allow logged-out users (e.g. panic button) to send alerts
CREATE OR REPLACE FUNCTION get_emergency_sender_secure()
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER -- Runs with permissions of the function creator (admin), bypassing RLS
AS $$
DECLARE
    result json;
BEGIN
    SELECT json_build_object(
        'smtp_server', smtp_server,
        'smtp_port', smtp_port,
        'smtp_email', smtp_email,
        'smtp_password', smtp_password
    )
    INTO result
    FROM sender_pool
    WHERE is_active = true
    ORDER BY random() -- Pick a random one for load balancing
    LIMIT 1;
    
    RETURN result;
END;
$$;

-- Grant execute permission to everyone (anon and authenticated)
GRANT EXECUTE ON FUNCTION get_emergency_sender_secure() TO anon, authenticated, service_role;
