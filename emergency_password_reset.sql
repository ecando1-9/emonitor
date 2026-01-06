-- ========================================
-- EMERGENCY PASSWORD RESET
-- ========================================

-- Replace 'your_email@example.com' with the email you need to reset
-- Replace 'new_secure_password' with the new password

UPDATE auth.users
SET encrypted_password = crypt('new_secure_password', gen_salt('bf')),
    updated_at = now()
WHERE email = 'your_email@example.com';

-- Verify the update
-- SELECT email, updated_at FROM auth.users WHERE email = 'your_email@example.com';
