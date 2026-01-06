# Supabase Setup - Final SQL

Run this SQL in **Supabase Dashboard → SQL Editor**:

```sql
-- 1. Enable RLS on users table
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- 2. Drop all existing policies
DROP POLICY IF EXISTS "Users can insert their own data" ON public.users;
DROP POLICY IF EXISTS "Users can view their own data" ON public.users;
DROP POLICY IF EXISTS "Users can update their own data" ON public.users;
DROP POLICY IF EXISTS "Enable insert for authenticated users only" ON public.users;
DROP POLICY IF EXISTS "Enable read access for users" ON public.users;
DROP POLICY IF EXISTS "Enable update for users" ON public.users;

-- 3. Create new policies that allow user self-registration
CREATE POLICY "Allow users to insert their own record"
  ON public.users
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Allow users to read their own record"
  ON public.users
  FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Allow users to update their own record"
  ON public.users
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- 4. Grant permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT, INSERT, UPDATE ON public.users TO authenticated;

-- 5. Create indexes for performance
CREATE INDEX IF NOT EXISTS users_email_idx ON public.users(email);
CREATE INDEX IF NOT EXISTS users_device_hash_idx ON public.users(device_hash);
```

## What This Does

1. **Enables RLS** - Secures the users table
2. **Creates policies** - Allows authenticated users to:
   - Insert their own record (when `auth.uid() = id`)
   - Read their own record
   - Update their own record
3. **Grants permissions** - Gives authenticated role access to the table
4. **Creates indexes** - Improves query performance

## After Running SQL

1. Restart the app: `python main.py`
2. Try creating a new account
3. Should work now!

The app will:
1. Create auth user in Supabase Auth
2. Create user record in `public.users` table (via app code, not trigger)
3. Sign in and return session

**No triggers needed!** Everything is done in the application code.
