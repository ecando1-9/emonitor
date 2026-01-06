# Free Trial Setup - Additional SQL

Run this SQL in **Supabase Dashboard → SQL Editor** to allow users to create their own trial subscriptions:

```sql
-- 1. Enable RLS on subscriptions table
ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

-- 2. Drop existing policies (if any)
DROP POLICY IF EXISTS "Users can insert their own subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "Users can view their own subscription" ON public.subscriptions;
DROP POLICY IF EXISTS "Users can update their own subscription" ON public.subscriptions;

-- 3. Create policies for self-service trial creation
CREATE POLICY "Users can insert their own subscription"
  ON public.subscriptions
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own subscription"
  ON public.subscriptions
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own subscription"
  ON public.subscriptions
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 4. Grant permissions
GRANT SELECT, INSERT, UPDATE ON public.subscriptions TO authenticated;

-- 5. Create a free trial plan (if it doesn't exist)
INSERT INTO public.plans (id, name, price, price_original, features)
VALUES (
  'free',
  'Free Trial',
  0,
  0,
  ARRAY[
    'TELEMETRY',
    'ACTIVITY_SUMMARY',
    'SCREENSHOT',
    'REPORT_SCHEDULE',
    'SCREEN_RECORD',
    'CAMERA',
    'MICROPHONE',
    'ADVANCED_ACTIVITY',
    'TYPING_INTENSITY'
  ]
)
ON CONFLICT (id) DO UPDATE
SET features = EXCLUDED.features;
```

## What This Does

1. **Enables RLS** on subscriptions table
2. **Creates policies** allowing users to:
   - Create their own trial subscription
   - View their own subscription
   - Update their own subscription
3. **Creates "free" plan** with all features enabled for trial

## After Running SQL

New users will automatically get:
- ✅ 7-day free trial
- ✅ All features enabled
- ✅ Full emergency functionality
- ✅ No credit card required

## Trial Details

- **Duration**: 7 days
- **Features**: All features included
- **Status**: "trialing"
- **After trial**: User can upgrade to paid plan

---

**Run this SQL, then test signup again!** New users will get automatic free trial.
