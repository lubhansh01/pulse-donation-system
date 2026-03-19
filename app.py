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
    if username == "admin" and password == "admin123":
        return "admin"
    elif username == "operator" and password == "operator123":
        return "operator"
    return None

# ---------------- SESSION ----------------
if "role" not in st.session_state:
    st.session_state.role = None

if "show_new_user" not in st.session_state:
    st.session_state.show_new_user = False

# ---------------- LOGIN PAGE ----------------
if st.session_state.role is None:

    st.subheader("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        role = login(username, password)
        if role:
            st.session_state.role = role
            st.success(f"Logged in as {role}")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------------- OPERATOR PANEL ----------------
elif st.session_state.role == "operator":

    st.sidebar.write("Logged in as Operator")

    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()

    st.header("💰 Donation Entry Panel")

    conn = get_connection()
    cursor = conn.cursor()

    # -------- NEW USER BUTTON --------
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ New User"):
            st.session_state.show_new_user = True

    # -------- NEW USER FORM --------
    if st.session_state.show_new_user:

        st.subheader("🆕 Create New User")

        name = st.text_input("Name")
        phone = st.text_input("Phone Number")
        village = st.text_input("Village")
        age = st.number_input("Age", 1, 120)

        if st.button("Create User"):
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]

            unique_id = generate_unique_id(count + 1)

            try:
                cursor.execute("""
                    INSERT INTO users (unique_id, name, phone, village, age)
                    VALUES (?, ?, ?, ?, ?)
                """, (unique_id, name, phone, village, age))

                conn.commit()

                st.success(f"✅ User Created! Unique ID: {unique_id}")
                st.session_state.show_new_user = False

            except:
                st.error("❌ Phone already exists!")

    # -------- SEARCH USER --------
    st.markdown("---")
    st.subheader("🔍 Enter Unique ID")

    unique_id_input = st.text_input("Unique ID (e.g. PD1001)")

    user = None

    if unique_id_input:
        cursor.execute("SELECT * FROM users WHERE unique_id = ?", (unique_id_input,))
        user = cursor.fetchone()

        if user:
            st.success(f"User: {user[2]} | Village: {user[4]}")
        else:
            st.error("❌ User not found. Please create new user.")

    # -------- DONATION ENTRY --------
    if user:
        st.markdown("---")
        st.subheader("💵 Add Donation")

        amount = st.number_input("Amount", min_value=1)

        cause = st.selectbox("Select Cause", [
            "Donate for Gaushala",
            "Donate for Annaxtra",
            "Other"
        ])

        if st.button("Submit Donation"):
            cursor.execute("""
                INSERT INTO donations (user_id, amount, cause, operator)
                VALUES (?, ?, ?, ?)
            """, (user[0], amount, cause, "operator"))

            conn.commit()
            st.success("✅ Donation Recorded Successfully")

    conn.close()

# ---------------- ADMIN PANEL ----------------
elif st.session_state.role == "admin":

    st.sidebar.write("Logged in as Admin")

    if st.sidebar.button("Logout"):
        st.session_state.role = None
        st.rerun()

    st.header("📊 Admin Dashboard")

    conn = get_connection()

    df = pd.read_sql("""
        SELECT d.id, u.unique_id, u.name, u.village, d.amount, d.cause, d.timestamp
        FROM donations d
        JOIN users u ON d.user_id = u.id
    """, conn)

    total = df["amount"].sum() if not df.empty else 0
    st.metric("Total Donations", f"₹ {total}")

    st.markdown("---")

    # -------- FILTERS --------
    st.subheader("🔍 Filters")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("From Date", date.today())

    with col2:
        end_date = st.date_input("To Date", date.today())

    village_filter = st.text_input("Filter by Village")

    cause_filter = st.selectbox("Filter by Cause", ["All",
        "Donate for Gaushala",
        "Donate for Annaxtra",
        "Other"
    ])

    show_data = st.button("🔍 Show Data")

    # -------- APPLY FILTERS --------
    if show_data:

        filtered_df = df.copy()

        filtered_df["timestamp"] = pd.to_datetime(filtered_df["timestamp"])

        filtered_df = filtered_df[
            (filtered_df["timestamp"].dt.date >= start_date) &
            (filtered_df["timestamp"].dt.date <= end_date)
        ]

        if village_filter:
            filtered_df = filtered_df[
                filtered_df["village"].str.contains(village_filter, case=False, na=False)
            ]

        if cause_filter != "All":
            filtered_df = filtered_df[
                filtered_df["cause"] == cause_filter
            ]

        st.markdown("---")

        st.metric("Filtered Total", f"₹ {filtered_df['amount'].sum() if not filtered_df.empty else 0}")

        st.dataframe(filtered_df)

        st.download_button(
            "Download CSV",
            filtered_df.to_csv(index=False),
            "filtered_data.csv"
        )

    else:
        st.info("Select filters and click 'Show Data'")

    # -------- EXPENSES --------
    st.markdown("---")
    st.subheader("💸 Add Expense")

    exp_date = st.date_input("Expense Date", date.today())
    
    exp_amount = st.number_input("Expense Amount", min_value=1)
    exp_desc = st.text_input("Description")

    if st.button("Add Expense"):
        conn.execute(
            "INSERT INTO expenses (amount, description, date) VALUES (?, ?, ?)",
            (exp_amount, exp_desc, exp_date)
        )

        conn.commit()
        st.success("Expense Added")
    # -------- BUTTONS --------
    col1, col2 = st.columns(2)
    
    with col1:
        add_expense_btn = st.button("Add Expense")
        
    with col2:
        show_expense_btn = st.button("📊 Show All Expenses")


    # -------- ADD EXPENSE --------
    if add_expense_btn:
        conn.execute(
            "INSERT INTO expenses (amount, description, date) VALUES (?, ?, ?)",
            (exp_amount, exp_desc, exp_date)
      )
        conn.commit()
        st.success("Expense Added Successfully")


    # -------- SHOW EXPENSES --------
    if show_expense_btn:
        st.markdown("---")
        st.subheader("📊 All Expenses")
        
        exp_df = pd.read_sql(
            "SELECT id, amount, description, date FROM expenses ORDER BY date DESC",
            conn
       )
        
    st.dataframe(exp_df)

    # CSV DOWNLOAD ONLY
    st.download_button(
        "⬇️ Download CSV",
        exp_df.to_csv(index=False),
        "expenses.csv",
        mime="text/csv"
    )