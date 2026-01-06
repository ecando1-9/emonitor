-- Create user_feedback table to store feedback and issue reports
CREATE TABLE IF NOT EXISTS public.user_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    user_email TEXT NOT NULL,
    user_name TEXT,
    feedback_type TEXT NOT NULL CHECK (feedback_type IN ('feedback', 'issue', 'bug', 'feature_request', 'other')),
    subject TEXT NOT NULL,
    message TEXT NOT NULL,
    device_info JSONB,
    app_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'new' CHECK (status IN ('new', 'in_progress', 'resolved', 'closed')),
    admin_notes TEXT,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES auth.users(id)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id ON public.user_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at ON public.user_feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_feedback_status ON public.user_feedback(status);
CREATE INDEX IF NOT EXISTS idx_user_feedback_type ON public.user_feedback(feedback_type);

-- Enable Row Level Security
ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

-- Policy: Users can insert their own feedback
CREATE POLICY "Users can insert their own feedback"
ON public.user_feedback
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- Policy: Users can view their own feedback
CREATE POLICY "Users can view their own feedback"
ON public.user_feedback
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy: Admins can view all feedback (optional - configure admin role as needed)
-- CREATE POLICY "Admins can view all feedback"
-- ON public.user_feedback
-- FOR SELECT
-- TO authenticated
-- USING (
--     EXISTS (
--         SELECT 1 FROM auth.users
--         WHERE auth.users.id = auth.uid()
--         AND auth.users.raw_user_meta_data->>'role' = 'admin'
--     )
-- );

-- Policy: Admins can update feedback status (optional)
-- CREATE POLICY "Admins can update feedback"
-- ON public.user_feedback
-- FOR UPDATE
-- TO authenticated
-- USING (
--     EXISTS (
--         SELECT 1 FROM auth.users
--         WHERE auth.users.id = auth.uid()
--         AND auth.users.raw_user_meta_data->>'role' = 'admin'
--     )
-- );

-- Create a function to submit feedback (with RLS bypass for easier client usage)
CREATE OR REPLACE FUNCTION public.submit_user_feedback(
    p_user_email TEXT,
    p_user_name TEXT,
    p_feedback_type TEXT,
    p_subject TEXT,
    p_message TEXT,
    p_device_info JSONB DEFAULT NULL,
    p_app_version TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_feedback_id BIGINT;
    v_user_id UUID;
BEGIN
    -- Get user ID from auth.uid()
    v_user_id := auth.uid();
    
    -- Validate feedback type
    IF p_feedback_type NOT IN ('feedback', 'issue', 'bug', 'feature_request', 'other') THEN
        RAISE EXCEPTION 'Invalid feedback type';
    END IF;
    
    -- Insert feedback
    INSERT INTO public.user_feedback (
        user_id,
        user_email,
        user_name,
        feedback_type,
        subject,
        message,
        device_info,
        app_version
    ) VALUES (
        v_user_id,
        p_user_email,
        p_user_name,
        p_feedback_type,
        p_subject,
        p_message,
        p_device_info,
        p_app_version
    )
    RETURNING id INTO v_feedback_id;
    
    -- Return success with feedback ID
    RETURN jsonb_build_object(
        'success', true,
        'feedback_id', v_feedback_id,
        'message', 'Feedback submitted successfully'
    );
    
EXCEPTION
    WHEN OTHERS THEN
        RETURN jsonb_build_object(
            'success', false,
            'error', SQLERRM
        );
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.submit_user_feedback TO authenticated;

-- Add comment to table
COMMENT ON TABLE public.user_feedback IS 'Stores user feedback, issue reports, and feature requests';
COMMENT ON COLUMN public.user_feedback.feedback_type IS 'Type of feedback: feedback, issue, bug, feature_request, other';
COMMENT ON COLUMN public.user_feedback.status IS 'Status: new, in_progress, resolved, closed';
COMMENT ON COLUMN public.user_feedback.device_info IS 'JSON object containing device information (OS, version, etc.)';
