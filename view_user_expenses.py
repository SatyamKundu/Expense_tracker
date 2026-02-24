import sqlite3
from datetime import datetime

def view_expenses_by_user():
    """Display expenses grouped by user"""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    
    print("EXPENSES BY USER")
    print("=" * 80)
    
    # Get all users
    cursor.execute("SELECT id, username, email FROM user ORDER BY username")
    users = cursor.fetchall()
    
    if not users:
        print("No users found in database.")
        return
    
    for user in users:
        user_id, username, email = user
        print(f"\n{'='*60}")
        print(f"USER: {username} (ID: {user_id})")
        print(f"Email: {email}")
        print(f"{'='*60}")
        
        # Get expenses for this user
        cursor.execute("""
            SELECT id, description, amount, category, date, time, created_at 
            FROM expense 
            WHERE user_id = ? 
            ORDER BY date DESC, created_at DESC
        """, (user_id,))
        
        expenses = cursor.fetchall()
        
        if not expenses:
            print("  No expenses found for this user.")
            continue
        
        # Calculate total
        total_amount = sum(exp[2] for exp in expenses)  # amount is at index 2
        
        print(f"  Total Expenses: {len(expenses)} items")
        print(f"  Total Amount: ${total_amount:.2f}")
        print(f"\n  {'ID':<5} {'Description':<20} {'Amount':<10} {'Category':<15} {'Date':<12} {'Time':<8}")
        print(f"  {'-'*5} {'-'*20} {'-'*10} {'-'*15} {'-'*12} {'-'*8}")
        
        for exp in expenses:
            exp_id, description, amount, category, date, time, created_at = exp
            print(f"  {exp_id:<5} {description[:18]:<20} ${amount:<9.2f} {category:<15} {date:<12} {time or 'N/A':<8}")
    
    # Summary
    cursor.execute("SELECT COUNT(*) FROM expense")
    total_expenses = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM expense")
    total_amount = cursor.fetchone()[0] or 0
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"Total Users: {len(users)}")
    print(f"Total Expenses: {total_expenses}")
    print(f"Total Amount: ${total_amount:.2f}")
    print(f"{'='*80}")
    
    conn.close()

def view_single_user_expenses(username):
    """View expenses for a specific user"""
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    
    # Find user
    cursor.execute("SELECT id, username, email FROM user WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    if not user:
        print(f"User '{username}' not found in database.")
        conn.close()
        return
    
    user_id, username, email = user
    
    print(f"EXPENSES FOR: {username}")
    print(f"Email: {email}")
    print("=" * 60)
    
    # Get expenses
    cursor.execute("""
        SELECT id, description, amount, category, date, time, created_at 
        FROM expense 
        WHERE user_id = ? 
        ORDER BY date DESC, created_at DESC
    """, (user_id,))
    
    expenses = cursor.fetchall()
    
    if not expenses:
        print("No expenses found for this user.")
        conn.close()
        return
    
    # Calculate totals
    total_amount = sum(exp[2] for exp in expenses)
    
    # Group by category
    category_totals = {}
    for exp in expenses:
        category = exp[3]  # category is at index 3
        amount = exp[2]     # amount is at index 2
        category_totals[category] = category_totals.get(category, 0) + amount
    
    print(f"Total Expenses: {len(expenses)} items")
    print(f"Total Amount: ${total_amount:.2f}")
    
    print(f"\nCategory Breakdown:")
    for category, amount in category_totals.items():
        print(f"  {category}: ${amount:.2f}")
    
    print(f"\nDetailed Expenses:")
    print(f"{'ID':<5} {'Description':<25} {'Amount':<10} {'Category':<15} {'Date':<12} {'Time':<8}")
    print(f"{'-'*5} {'-'*25} {'-'*10} {'-'*15} {'-'*12} {'-'*8}")
    
    for exp in expenses:
        exp_id, description, amount, category, date, time, created_at = exp
        print(f"{exp_id:<5} {description[:23]:<25} ${amount:<9.2f} {category:<15} {date:<12} {time or 'N/A':<8}")
    
    conn.close()

if __name__ == "__main__":
    print("Choose an option:")
    print("1. View all users' expenses")
    print("2. View expenses for specific user")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        view_expenses_by_user()
    elif choice == "2":
        username = input("Enter username: ").strip()
        view_single_user_expenses(username)
    else:
        print("Invalid choice.")
