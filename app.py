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

    # -------- FILTERS --------
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

    # -------- EXPENSE --------
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

    # -------- USER MANAGEMENT (UPDATED) --------
    st.markdown("---")
    st.subheader("👤 User Management")

    search_input = st.text_input("Search by ID / Name / Village")

    query = "SELECT * FROM users"
    params = ()

    if search_input:
        query += """
            WHERE unique_id LIKE ?
            OR name LIKE ?
            OR village LIKE ?
        """
        params = (f"%{search_input}%", f"%{search_input}%", f"%{search_input}%")

    user_df = pd.read_sql(query, conn, params=params)

    if not user_df.empty:

        st.dataframe(user_df)

        st.download_button(
            "Download Users CSV",
            user_df.to_csv(index=False),
            "users.csv"
        )

        st.markdown("### ❌ Delete User")

        user_to_delete = st.selectbox(
            "Select User",
            user_df["unique_id"] + " - " + user_df["name"]
        )

        if st.button("Delete Selected User"):
            uid = user_to_delete.split(" - ")[0]
            conn.execute("DELETE FROM users WHERE unique_id = ?", (uid,))
            conn.commit()
            st.warning("User deleted")
            st.rerun()

    else:
        st.info("No users found")

    conn.close()