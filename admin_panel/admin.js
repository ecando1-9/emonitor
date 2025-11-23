import { createClient } from '@supabase/supabase-js';
import 'dotenv/config';
import * as readline from 'readline/promises';
import { stdin as input, stdout as output } from 'process';

// --- Supabase & Admin Setup ---
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;
const adminPassword = process.env.ADMIN_PASSWORD;

if (!supabaseUrl || !supabaseServiceKey || !adminPassword) {
    console.error('Error: Missing environment variables. Please check your admin_panel/.env file.');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey, {
    auth: {
        autoRefreshToken: false,
        persistSession: false
    }
});

const rl = readline.createInterface({ input, output });

// --- Helper Functions ---
async function prompt(question) {
    return await rl.question(question);
}

async function login() {
    const password = await prompt('Enter Admin Password: ');
    if (password === adminPassword) {
        console.log('Admin login successful.\n');
        return true;
    } else {
        console.error('Login failed. Incorrect password.');
        return false;
    }
}

// --- Menu Functions ---

async function uploadEmailPool() {
    console.log('\n--- Upload New Sender Email ---');
    
    const smtp_server = await prompt('Enter SMTP Server (e.g., smtp.gmail.com): ');
    const smtp_port = await prompt('Enter SMTP Port (e.g., 587): ');
    const smtp_email = await prompt('Enter Sender Email (e.g., sender1@gmail.com): ');
    const smtp_password = await prompt('Enter Sender App Password: ');
    const max_users_input = await prompt('Max users for this sender (default 10): ');
    const max_users = max_users_input ? parseInt(max_users_input, 10) : 10;

    const { data, error } = await supabase
        .from('sender_pool')
        .insert({
            smtp_server,
            smtp_port,
            smtp_email,
            smtp_password,
            max_users,
            is_active: true  // Set to active by default
        });

    if (error) {
        console.error('Error uploading email:', error.message);
    } else {
        console.log(`Successfully added '${smtp_email}' (Max ${max_users} users) to the pool.`);
    }
}

async function listUsers() {
    console.log('\n--- Listing All Users ---');
    const { data: { users }, error } = await supabase.auth.admin.listUsers();
    
    if (error) {
        console.error('Error listing users:', error.message);
        return;
    }
    
    if (users.length === 0) {
        console.log('No users found.');
        return;
    }

    console.log('ID\t\t\t\t\tEmail\t\t\tCreated At');
    console.log('-----------------------------------------------------------------------------------');
    users.forEach(user => {
        console.log(`${user.id}\t${user.email}\t${user.created_at}`);
    });
}

async function listSenderPool() {
    console.log('\n--- Listing Sender Pool Status ---');
    const { data, error } = await supabase
        .from('sender_pool')
        .select('*')
        .order('created_at', { ascending: false });
    
    if (error) {
        console.error('Error listing sender pool:', error.message);
        return;
    }
    
    if (data.length === 0) {
        console.log('Sender pool is empty.');
        return;
    }

    console.log('ID\tEmail\t\t\t\tAssigned\tMax Users\tActive');
    console.log('---------------------------------------------------------------------------------------------------');
    data.forEach(sender => {
        const activeStatus = sender.is_active === true ? 'Yes' : 'No';
        console.log(`${sender.id}\t${sender.smtp_email}\t\t${sender.assigned_count}\t\t${sender.max_users}\t\t${activeStatus}`);
    });
}

async function toggleSenderStatus() {
    console.log('\n--- Activate/Deactivate Sender ---');
    
    // First list all senders
    const { data: senders, error: listError } = await supabase
        .from('sender_pool')
        .select('id, smtp_email, is_active')
        .order('created_at', { ascending: false });
    
    if (listError) {
        console.error('Error listing senders:', listError.message);
        return;
    }
    
    if (senders.length === 0) {
        console.log('No senders found in pool.');
        return;
    }
    
    console.log('\nAvailable Senders:');
    console.log('ID\tEmail\t\t\t\tActive');
    console.log('-------------------------------------------------------------------');
    senders.forEach(sender => {
        const activeStatus = sender.is_active === true ? 'Yes' : 'No';
        console.log(`${sender.id}\t${sender.smtp_email}\t\t${activeStatus}`);
    });
    
    const senderId = await prompt('\nEnter Sender ID to toggle status: ');
    if (!senderId) {
        console.log('No sender ID provided.');
        return;
    }
    
    // Get current status
    const sender = senders.find(s => s.id == senderId);
    if (!sender) {
        console.error('Sender not found.');
        return;
    }
    
    const newStatus = !sender.is_active;
    const { data, error } = await supabase
        .from('sender_pool')
        .update({ is_active: newStatus })
        .eq('id', senderId);
    
    if (error) {
        console.error('Error updating sender status:', error.message);
    } else {
        console.log(`Successfully ${newStatus ? 'activated' : 'deactivated'} sender: ${sender.smtp_email}`);
    }
}

async function listEmergencyAlerts() {
    console.log('\n--- Emergency Alerts ---');
    const { data, error } = await supabase
        .from('emergency_alerts')
        .select('*, user_id, device_hash')
        .order('created_at', { ascending: false })
        .limit(50);
    
    if (error) {
        console.error('Error listing emergency alerts:', error.message);
        return;
    }
    
    if (data.length === 0) {
        console.log('No emergency alerts found.');
        return;
    }

    console.log('\nID\tStatus\t\tCreated At\t\t\tDevice Hash\t\t\tUser ID');
    console.log('-----------------------------------------------------------------------------------------------------------------------------------');
    data.forEach(alert => {
        const created = new Date(alert.created_at).toLocaleString();
        const status = alert.status || 'new';
        const deviceHash = (alert.device_hash || 'N/A').substring(0, 20) + '...';
        const userId = (alert.user_id || 'N/A').substring(0, 20) + '...';
        console.log(`${alert.id}\t${status}\t\t${created}\t${deviceHash}\t${userId}`);
    });
    
    // Show details for a specific alert
    const alertId = await prompt('\nEnter Alert ID to view details (or press Enter to skip): ');
    if (alertId) {
        const { data: alertData, error: alertError } = await supabase
            .from('emergency_alerts')
            .select('*')
            .eq('id', alertId)
            .single();
        
        if (alertError) {
            console.error('Error fetching alert details:', alertError.message);
        } else if (alertData) {
            console.log('\n--- Alert Details ---');
            console.log(`ID: ${alertData.id}`);
            console.log(`Status: ${alertData.status}`);
            console.log(`Created At: ${new Date(alertData.created_at).toLocaleString()}`);
            console.log(`Device Hash: ${alertData.device_hash || 'N/A'}`);
            console.log(`User ID: ${alertData.user_id || 'N/A'}`);
            console.log(`Location: ${JSON.stringify(alertData.last_location, null, 2)}`);
            console.log(`Activity Summary: ${alertData.activity_summary || 'N/A'}`);
            console.log(`Acknowledged By: ${alertData.acknowledged_by || 'Not acknowledged'}`);
            console.log(`Notes: ${alertData.notes || 'No notes'}`);
        }
    }
}

async function acknowledgeEmergencyAlert() {
    console.log('\n--- Acknowledge Emergency Alert ---');
    const alertId = await prompt('Enter Alert ID to acknowledge: ');
    if (!alertId) {
        console.log('Operation canceled.');
        return;
    }
    
    const notes = await prompt('Enter notes (optional): ');
    const adminId = await prompt('Enter your Admin User ID (optional): ');
    
    const updateData = {
        status: 'acknowledged',
        acknowledged_at: new Date().toISOString()
    };
    
    if (notes) {
        updateData.notes = notes;
    }
    if (adminId) {
        updateData.acknowledged_by = adminId;
    }
    
    const { data, error } = await supabase
        .from('emergency_alerts')
        .update(updateData)
        .eq('id', alertId)
        .select();
    
    if (error) {
        console.error('Error acknowledging alert:', error.message);
    } else {
        console.log('Emergency alert acknowledged successfully.');
    }
}

async function deleteUser() {
    console.log('\n--- Delete a User ---');
    console.warn('WARNING: This is permanent and cannot be undone.');
    
    const userId = await prompt('Enter the User ID of the user you want to delete: ');
    if (!userId) {
        console.log('Deletion canceled.');
        return;
    }
    
    const confirm = await prompt(`Are you sure you want to delete user ${userId}? (y/n): `);
    if (confirm.toLowerCase() !== 'y') {
        console.log('Deletion canceled.');
        return;
    }

    const { data, error } = await supabase.auth.admin.deleteUser(userId);
    
    if (error) {
        console.error('Error deleting user:', error.message);
    } else {
        console.log('Successfully deleted user.');
    }
}

// --- Main Menu Loop ---
async function mainMenu() {
    while (true) {
        console.log('\n====== eMonitor Admin Panel ======');
        console.log('1. Upload Email to Sender Pool');
        console.log('2. List Sender Pool Status');
        console.log('3. Activate/Deactivate Sender');
        console.log('4. List All Users');
        console.log('5. View Emergency Alerts');
        console.log('6. Acknowledge Emergency Alert');
        console.log('7. Delete a User (Advanced)');
        console.log('8. Exit');
        const choice = await prompt('Select an option (1-8): ');

        switch (choice) {
            case '1':
                await uploadEmailPool();
                break;
            case '2':
                await listSenderPool();
                break;
            case '3':
                await toggleSenderStatus();
                break;
            case '4':
                await listUsers();
                break;
            case '5':
                await listEmergencyAlerts();
                break;
            case '6':
                await acknowledgeEmergencyAlert();
                break;
            case '7':
                await deleteUser();
                break;
            case '8':
                console.log('Exiting admin panel.');
                rl.close();
                return;
            default:
                console.log('Invalid choice. Please select 1-8.');
        }
    }
}

// --- Start the Tool ---
(async () => {
    if (await login()) {
        await mainMenu();
    } else {
        rl.close();
    }
})();