#!/usr/bin/env python3
"""
Simple script to add a sender email to the sender_pool table in Supabase.
Run this before using eMonitor to ensure at least one sender is available.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Get Supabase credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY")

if not url or not key:
    print("ERROR: SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env file")
    sys.exit(1)

# Create Supabase client
supabase: Client = create_client(url, key)

def add_sender():
    """Add a new sender to the sender_pool"""
    print("\n=== Add Sender to eMonitor ===\n")
    
    smtp_server = input("Enter SMTP Server (e.g., smtp.gmail.com): ").strip()
    if not smtp_server:
        print("ERROR: SMTP server cannot be empty")
        return False
    
    try:
        smtp_port = int(input("Enter SMTP Port (e.g., 587): ").strip())
    except ValueError:
        print("ERROR: SMTP port must be a number")
        return False
    
    smtp_email = input("Enter Sender Email (e.g., your-email@gmail.com): ").strip()
    if not smtp_email or "@" not in smtp_email:
        print("ERROR: Invalid email address")
        return False
    
    smtp_password = input("Enter Sender Password/App Password: ").strip()
    if not smtp_password:
        print("ERROR: Password cannot be empty")
        return False
    
    try:
        max_users = int(input("Max users for this sender (default 100): ").strip() or "100")
    except ValueError:
        print("ERROR: Max users must be a number")
        return False
    
    # Add to database
    try:
        print("\nAdding sender to database...")
        
        response = supabase.from_("sender_pool").insert({
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "smtp_email": smtp_email,
            "smtp_password": smtp_password,
            "max_users": max_users,
            "is_active": True,
            "assigned_count": 0
        }).execute()
        
        if response.data:
            sender_id = response.data[0]["id"] if response.data else "?"
            print(f"\n✅ SUCCESS! Sender added to pool:")
            print(f"   Email: {smtp_email}")
            print(f"   Server: {smtp_server}:{smtp_port}")
            print(f"   Max Users: {max_users}")
            print(f"   Status: ACTIVE (is_active=true)")
            print(f"   ID: {sender_id}")
            return True
        else:
            print(f"ERROR: Could not add sender: {response}")
            return False
            
    except Exception as e:
        print(f"\nERROR: Failed to add sender: {e}")
        return False

def list_senders():
    """List all senders in the pool"""
    print("\n=== Current Senders in Pool ===\n")
    
    try:
        response = supabase.from_("sender_pool").select("*").execute()
        
        if not response.data:
            print("No senders found in the pool.")
            return
        
        print(f"Found {len(response.data)} sender(s):\n")
        print(f"{'Email':<30} {'Server':<25} {'Port':<6} {'Active':<8} {'Users':<10} {'Max':<6}")
        print("-" * 85)
        
        for sender in response.data:
            email = sender.get("smtp_email", "N/A")
            server = sender.get("smtp_server", "N/A")
            port = sender.get("smtp_port", "N/A")
            is_active = "YES" if sender.get("is_active") else "NO"
            assigned = sender.get("assigned_count", 0)
            max_u = sender.get("max_users", 0)
            
            print(f"{email:<30} {server:<25} {port:<6} {is_active:<8} {assigned:<10} {max_u:<6}")
        
    except Exception as e:
        print(f"ERROR: Failed to list senders: {e}")

def activate_sender():
    """Activate an inactive sender"""
    print("\n=== Activate Sender ===\n")
    
    try:
        # Get all senders
        response = supabase.from_("sender_pool").select("id, smtp_email, is_active").execute()
        
        if not response.data:
            print("No senders found in the pool.")
            return
        
        print("Available senders:")
        for i, sender in enumerate(response.data):
            status = "ACTIVE" if sender.get("is_active") else "INACTIVE"
            print(f"{i+1}. {sender.get('smtp_email')} [{status}]")
        
        choice = input("\nEnter sender number to activate (or press Enter to skip): ").strip()
        if not choice:
            return
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(response.data):
                sender_id = response.data[idx]["id"]
                sender_email = response.data[idx]["smtp_email"]
                
                # Update to active
                update_response = supabase.from_("sender_pool").update({"is_active": True}).eq("id", sender_id).execute()
                
                if update_response.data:
                    print(f"\n✅ Activated sender: {sender_email}")
                else:
                    print(f"ERROR: Could not activate sender")
            else:
                print("Invalid selection")
        except ValueError:
            print("Invalid input")
            
    except Exception as e:
        print(f"ERROR: Failed to activate sender: {e}")

def main():
    """Main menu"""
    while True:
        print("\n=== eMonitor Sender Pool Manager ===")
        print("1. Add new sender to pool")
        print("2. List all senders")
        print("3. Activate a sender")
        print("4. Exit")
        
        choice = input("\nSelect an option (1-4): ").strip()
        
        if choice == "1":
            add_sender()
        elif choice == "2":
            list_senders()
        elif choice == "3":
            activate_sender()
        elif choice == "4":
            print("\nGoodbye!")
            break
        else:
            print("Invalid option. Please try again.")

if __name__ == "__main__":
    main()
