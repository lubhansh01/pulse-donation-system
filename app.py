import streamlit as st
import pandas as pd
from datetime import date
from database import create_tables, get_connection
from utils import generate_unique_id

# ---------------- SETUP ----------------
st.set_page_config(page_title="Ram Aasra Annaxtra", layout="wide")
create_tables()

# ---------------- BRANDING ----------------
st.title("🙏 Ram Aasra Annaxtra")
st.subheader("Pulse Donation Management System")
st.markdown("---")

# ---------------- LOGIN FUNCTION ----------------
def login(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    if username == "admin" and password == "admin123":
        return {"role": "admin", "name": "Admin"}

    cursor.execute("""
        SELECT * FROM operators
        WHERE (phone = ? OR name = ?)
        AND password = ?
        AND is_active = 1
    """, (username.strip(), username.strip(), password.strip()))

    operator = cursor.fetchone()
    conn.close()

    if operator:
        return {"role": "operator", "name": operator[1]}

    return None

# ---------------- SESSION ----------------
if "role" not in st.session_state:
    st.session_state.role = None

if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if "show_new_user" not in st.session_state:
    st.session_state.show_new_user = False

# ---------------- LOGIN ----------------
if st.session_state.role is None:

    st.subheader("Login")

    username = st.text_input("Username (Phone or Name)")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role = login(username, password)
        if role:
            st.session_state.role = role["role"]
            st.session_state.user_name = role["name"]
            st.success(f"Logged in as {role['name']}")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------------- OPERATOR PANEL ----------------
elif st.session_state.role == "operator":

    st.sidebar.write(f"👤 {st.session_state.user_name}")

    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()

    st.header("💰 Donation Entry Panel")

    conn = get_connection()
    cursor = conn.cursor()

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ New User"):
            st.session_state.show_new_user = True

    if st.session_state.show_new_user:

        st.subheader("🆕 Create New User")

        name = st.text_input("Name")
        phone = st.text_input("Phone")
        village = st.text_input("Village")
        age = st.number_input("Age", 1, 120)

        if st.button("Create User"):
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            uid = generate_unique_id(count + 1)

            try:
                cursor.execute("""
                    INSERT INTO users (unique_id, name, phone, village, age)
                    VALUES (?, ?, ?, ?, ?)
                """, (uid, name, phone, village, age))

                conn.commit()
                st.success(f"User Created! ID: {uid}")
                st.session_state.show_new_user = False
            except:
                st.error("Phone already exists")

    st.markdown("---")
    uid_input = st.text_input("Enter Unique ID")

    user = None

    if uid_input:
        cursor.execute("SELECT * FROM users WHERE unique_id = ?", (uid_input,))
        user = cursor.fetchone()

        if user:
            st.success(f"{user[2]} | {user[4]}")
        else:
            st.error("User not found")

    if user:
        amount = st.number_input("Amount", min_value=1)

        cause = st.selectbox("Cause", [
            "Donate for Gaushala",
            "Donate for Annaxtra",
            "Other"
        ])

        if st.button("Submit Donation"):
            cursor.execute("""
                INSERT INTO donations (user_id, amount, cause, operator)
                VALUES (?, ?, ?, ?)
            """, (user[0], amount, cause, st.session_state.user_name))

            conn.commit()
            st.success("Donation recorded")

    conn.close()

# ---------------- ADMIN PANEL ----------------
elif st.session_state.role == "admin":

    st.sidebar.write("👑 Admin")

    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()

    st.header("📊 Admin Dashboard")

    conn = get_connection()

    df = pd.read_sql("""
        SELECT d.id, u.unique_id, u.name, u.village,
               d.amount, d.cause, d.operator, d.timestamp
        FROM donations d
        JOIN users u ON d.user_id = u.id
    """, conn)

    st.metric("Total Donations", f"₹ {df['amount'].sum() if not df.empty else 0}")

    st.markdown("---")

    st.subheader("🔍 Filters")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("From Date", date.today())

    with col2:
        end_date = st.date_input("To Date", date.today())

    village = st.text_input("Village")

    cause = st.selectbox("Cause", ["All",
        "Donate for Gaushala",
        "Donate for Annaxtra",
        "Other"
    ])

    operator_filter = st.selectbox(
        "Filter by Operator",
        ["All"] + list(df["operator"].dropna().unique())
    )

    if st.button("Show Data"):

        f = df.copy()
        f["timestamp"] = pd.to_datetime(f["timestamp"])

        f = f[
            (f["timestamp"].dt.date >= start_date) &
            (f["timestamp"].dt.date <= end_date)
        ]

        if village:
            f = f[f["village"].str.contains(village, case=False, na=False)]

        if cause != "All":
            f = f[f["cause"] == cause]

        if operator_filter != "All":
            f = f[f["operator"] == operator_filter]

        st.metric("Filtered Total", f"₹ {f['amount'].sum() if not f.empty else 0}")
        st.dataframe(f)

        st.download_button("Download CSV", f.to_csv(index=False), "report.csv")

    st.markdown("---")

    # ---------------- EXPENSE ----------------
    st.subheader("💸 Add Expense")

    exp_date = st.date_input("Date", date.today())
    exp_amt = st.number_input("Amount", min_value=1)
    exp_desc = st.text_input("Description")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Add Expense"):
            conn.execute(
                "INSERT INTO expenses (amount, description, date) VALUES (?, ?, ?)",
                (exp_amt, exp_desc, exp_date)
            )
            conn.commit()
            st.success("Added")

    with col2:
        if st.button("📊 Show All Expenses"):
            exp_df = pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn)
            st.dataframe(exp_df)
            st.download_button("Download CSV", exp_df.to_csv(index=False), "expenses.csv")

    # ---------------- OPERATOR MANAGEMENT (UPDATED ONLY THIS PART) ----------------
    st.markdown("---")
    st.subheader("👥 Operator Management")

    op_df = pd.read_sql("SELECT * FROM operators", conn)

    if not op_df.empty:
        for _, row in op_df.iterrows():

            col1, col2, col3 = st.columns([4,2,1])

            col1.write(f"👤 {row['name']} ({row['phone']})")

            current_status = bool(row["is_active"])

            new_status = col2.toggle(
                "Active",
                value=current_status,
                key=f"toggle_{row['id']}"
            )

            if new_status != current_status:
                conn.execute(
                    "UPDATE operators SET is_active = ? WHERE id = ?",
                    (1 if new_status else 0, row["id"])
                )
                conn.commit()
                st.success(f"{row['name']} updated")

            if col3.button("❌", key=f"delete_{row['id']}"):
                conn.execute("DELETE FROM operators WHERE id = ?", (row["id"],))
                conn.commit()
                st.warning(f"{row['name']} deleted")
                st.rerun()

    st.markdown("---")

    if "show_add_operator" not in st.session_state:
        st.session_state.show_add_operator = False

    if st.button("➕ Add New Operator"):
        st.session_state.show_add_operator = True

    if st.session_state.show_add_operator:

        st.subheader("🆕 Add New Operator")

        name = st.text_input("Name")
        phone = st.text_input("Phone")
        age = st.number_input("Age", 1, 100)
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if st.button("Add New Operator"):
            try:
                conn.execute("""
                    INSERT INTO operators (name, phone, age, email, password)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    name.strip(),
                    phone.strip(),
                    age,
                    email.strip(),
                    password.strip()
                ))
                conn.commit()

                st.success("Operator Added Successfully")
                st.session_state.show_add_operator = False
                st.rerun()

            except:
                st.error("Phone already exists")

    conn.close()

    # ---------------- USER MANAGEMENT ----------------
    st.markdown("---")
    st.subheader("👤 User Management")

    conn = get_connection()

    # -------- SEARCH USER --------
    st.markdown("### 🔍 Search User")

    search_input = st.text_input("Search by ID / Name / Village")

    query = "SELECT * FROM users"
    params = ()

    if search_input:
        query += """
        WHERE unique_id LIKE ?
        OR name LIKE ?
        OR village LIKE ?
    """
    params = (
        f"%{search_input}%",
        f"%{search_input}%",
        f"%{search_input}%"
    )

    user_df = pd.read_sql(query, conn, params=params)

    # -------- SHOW USERS --------
    if not user_df.empty:
        
        for _, row in user_df.iterrows():
            
            col1, col2 = st.columns([5,1])
            
            col1.write(
                f"👤 {row['name']} | ID: {row['unique_id']} | 📍 {row['village']}"
            )
            
            # DELETE BUTTON
            if col2.button("❌", key=f"delete_user_{row['id']}"):
                
                conn.execute("DELETE FROM users WHERE id = ?", (row["id"],))
                conn.commit()

                st.warning(f"{row['name']} deleted")
                st.rerun()

    else:
        st.info("No users found")

    # -------- ADD USER --------
    st.markdown("---")

    if "show_add_user" not in st.session_state:
        st.session_state.show_add_user = False

    if st.button("➕ Add New User"):
        st.session_state.show_add_user = True
    
    if st.session_state.show_add_user:
        
        st.subheader("🆕 Add New User")
        
        name = st.text_input("Name", key="admin_user_name")
        phone = st.text_input("Phone", key="admin_user_phone")
        village = st.text_input("Village", key="admin_user_village")
        age = st.number_input("Age", 1, 120, key="admin_user_age")
        
        if st.button("Add User", key="submit_admin_user"):
            
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            unique_id = generate_unique_id(count + 1)
        try:
            conn.execute("""
                INSERT INTO users (unique_id, name, phone, village, age)
                VALUES (?, ?, ?, ?, ?)
            """, (
                unique_id,
                name.strip(),
                phone.strip(),
                village.strip(),
                age
            ))

            conn.commit()

            st.success(f"✅ User Added! ID: {unique_id}")

            st.session_state.show_add_user = False
            st.rerun()

        except:
            st.error("❌ Phone already exists")

    conn.close()