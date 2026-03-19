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

    # -------- NEW USER BUTTON --------
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("➕ New User"):
            st.session_state.show_new_user = True

    # -------- CREATE USER --------
    if st.session_state.show_new_user:

        st.subheader("🆕 Create New User")

        name = st.text_input("Name")
        phone = st.text_input("Phone")
        village = st.text_input("Village")
        age = st.number_input("Age", 1, 120)

        if st.button("Create User"):

            # -------- VALIDATION --------
            if not name.strip():
                st.error("Name cannot be empty")

            elif not phone.strip():
                st.error("Phone cannot be empty")

            else:
                try:
                    import time
                    uid = f"U{int(time.time())}"  # unique ID (no collision)

                    cursor.execute("""
                        INSERT INTO users (unique_id, name, phone, village, age)
                        VALUES (?, ?, ?, ?, ?)
                    """, (uid, name.strip(), phone.strip(), village.strip(), age))

                    conn.commit()
                    st.success(f"User Created! ID: {uid}")
                    st.session_state.show_new_user = False
                    st.rerun()

                except Exception as e:
                    if "users.phone" in str(e):
                        st.error("Phone already exists")
                    else:
                        st.error(f"Error: {str(e)}")

    st.markdown("---")

    # -------- USER SEARCH --------
    st.subheader("🔍 Find User")

    search_input = st.text_input("Enter Unique ID / Phone / Name")

    selected_user = None

    if search_input:
        cursor.execute("""
            SELECT * FROM users
            WHERE unique_id = ?
            OR phone = ?
            OR name LIKE ?
        """, (search_input, search_input, f"%{search_input}%"))

        users = cursor.fetchall()

        if len(users) == 1:
            user = users[0]
            st.success(f"👤 {user[2]} | 📍 {user[4]} | 📞 {user[3]}")
            selected_user = user

        elif len(users) > 1:
            st.warning("Multiple users found. Please select one:")

            user_options = [
                f"{u[2]} | {u[3]} | {u[4]} | Age: {u[5]}"
                for u in users
            ]

            selected_option = st.selectbox("Select User", user_options)
            selected_index = user_options.index(selected_option)
            selected_user = users[selected_index]

        else:
            st.error("User not found. Please create new user.")

    # -------- DONATION --------
    if selected_user:
        st.markdown("### 💰 Enter Donation")

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
            """, (selected_user[0], amount, cause, st.session_state.user_name))

            conn.commit()
            st.success("✅ Donation recorded successfully")
            st.rerun()

    st.markdown("---")

    # -------- TODAY'S DONATIONS --------
    st.subheader("📊 Today's Donations")

    today_df = pd.read_sql("""
        SELECT u.name, u.village, d.amount, d.cause, d.timestamp
        FROM donations d
        JOIN users u ON d.user_id = u.id
        WHERE DATE(d.timestamp) = DATE('now')
        AND d.operator = ?
        ORDER BY d.timestamp DESC
    """, conn, params=(st.session_state.user_name,))

    if not today_df.empty:
        st.dataframe(today_df)
    else:
        st.info("No donations recorded today")

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

    total_donation = df['amount'].sum() if not df.empty else 0
    expense_df = pd.read_sql("SELECT * FROM expenses", conn)
    total_expense = expense_df['amount'].sum() if not expense_df.empty else 0
    final_balance = total_donation - total_expense

    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Total Donations", f"₹ {total_donation}")
    col2.metric("💸 Total Expenses", f"₹ {total_expense}")
    col3.metric("🏦 Final Balance", f"₹ {final_balance}")

    st.markdown("---")

    # -------- FILTERS --------
    st.subheader("🔍 Filters")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("From Date", date.today())

    with col2:
        end_date = st.date_input("To Date", date.today())

    village = st.text_input("Village")

    amount_filter = st.number_input("Filter by Amount", min_value=0.0, value=0.0)

    cause = st.selectbox("Cause", ["All",
        "Donate for Gaushala",
        "Donate for Annaxtra",
        "Other"
    ])

    operator_filter = st.selectbox(
        "Filter by Operator",
        ["All"] + list(df["operator"].dropna().unique())
    )

    # -------- SHOW DATA BUTTON --------
    if st.button("Show Data"):

        f = df.copy()

        # Convert timestamp
        f["timestamp"] = pd.to_datetime(f["timestamp"])

        # -------- DATE FILTER --------
        f = f[
            (f["timestamp"].dt.date >= start_date) &
            (f["timestamp"].dt.date <= end_date)
        ]

        # -------- VILLAGE FILTER --------
        if village:
            f = f[f["village"].str.contains(village, case=False, na=False)]

        # -------- CAUSE FILTER --------
        if cause != "All":
            f = f[f["cause"] == cause]

        # -------- OPERATOR FILTER --------
        if operator_filter != "All":
            f = f[f["operator"] == operator_filter]

        # -------- AMOUNT FILTER (FIXED) --------
        if amount_filter > 0:
            f = f[abs(f["amount"] - float(amount_filter)) < 0.01]

        # -------- RESULTS --------
        st.metric("Filtered Total", f"₹ {f['amount'].sum() if not f.empty else 0}")

        st.dataframe(f)

        # -------- DOWNLOAD CSV --------
        st.download_button(
            label="📥 Download CSV",
            data=f.to_csv(index=False),
            file_name="filtered_report.csv",
            mime="text/csv"
        )

    # -------- EXPENSE --------
    st.subheader("💸 Expense Management")

    exp_date = st.date_input("Date", date.today(), key="exp_date")
    exp_amt = st.number_input("Amount", min_value=1, key="exp_amt")
    exp_desc = st.text_input("Description", key="exp_desc")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Add Expense", key="add_expense_btn"):
            conn.execute(
                "INSERT INTO expenses (amount, description, date) VALUES (?, ?, ?)",
                (exp_amt, exp_desc, exp_date)
            )
            conn.commit()
            st.success("Expense Added")
            st.rerun()

    show_exp = st.toggle("📊 Show All Expenses")

    if show_exp:
        exp_df = pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn)

        if not exp_df.empty:
            st.dataframe(exp_df)

            st.download_button(
                "Download CSV",
                exp_df.to_csv(index=False),
                "expenses.csv"
            )

            st.markdown("### ✏️ Edit / Delete Expense")

            selected_exp = st.selectbox(
                "Select Expense",
                exp_df["id"].astype(str) + " | ₹" + exp_df["amount"].astype(str)
            )

            exp_id = int(selected_exp.split(" | ")[0])
            selected_row = exp_df[exp_df["id"] == exp_id].iloc[0]

            new_amt = st.number_input("Edit Amount", value=int(selected_row["amount"]))
            new_desc = st.text_input("Edit Description", value=selected_row["description"])
            new_date = st.date_input("Edit Date", value=pd.to_datetime(selected_row["date"]))

            col_edit, col_delete = st.columns(2)

            with col_edit:
                if st.button("Update Expense"):
                    conn.execute("""
                        UPDATE expenses
                        SET amount = ?, description = ?, date = ?
                        WHERE id = ?
                    """, (new_amt, new_desc, new_date, exp_id))
                    conn.commit()
                    st.rerun()

            with col_delete:
                if st.button("Delete Expense"):
                    conn.execute("DELETE FROM expenses WHERE id = ?", (exp_id,))
                    conn.commit()
                    st.rerun()

        else:
            st.info("No expenses found")

    # -------- OPERATOR MANAGEMENT --------
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

    # -------- ADD NEW OPERATOR BUTTON --------
    st.markdown("---")

    if "show_add_operator" not in st.session_state:
        st.session_state.show_add_operator = False

    if st.button("➕ Add New Operator"):
        st.session_state.show_add_operator = True

    # -------- ADD OPERATOR FORM --------
    if st.session_state.show_add_operator:

        st.subheader("🆕 Add New Operator")

        name = st.text_input("Name", key="new_op_name")
        phone = st.text_input("Phone", key="new_op_phone")
        age = st.number_input("Age", 1, 100, key="new_op_age")
        email = st.text_input("Email", key="new_op_email")
        password = st.text_input("Password", type="password", key="new_op_pass")

        if st.button("Add New Operator", key="submit_new_operator"):
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

    # -------- USER MANAGEMENT --------
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

    if "show_add_user" not in st.session_state:
        st.session_state.show_add_user = False

    if st.button("➕ Add New User"):
        st.session_state.show_add_user = True

    if st.session_state.show_add_user:

        st.subheader("🆕 Add User")

        name = st.text_input("Name", key="admin_user_name")
        phone = st.text_input("Phone", key="admin_user_phone")
        village = st.text_input("Village", key="admin_user_village")
        age = st.number_input("Age", 1, 120, key="admin_user_age")

        if st.button("Add User", key="submit_admin_user"):

            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]

            uid = generate_unique_id(count + 1)

            try:
                conn.execute("""
                    INSERT INTO users (unique_id, name, phone, village, age)
                    VALUES (?, ?, ?, ?, ?)
                """, (uid, name, phone, village, age))

                conn.commit()
                st.success(f"User Added! ID: {uid}")
                st.session_state.show_add_user = False
                st.rerun()
            except:
                st.error("Phone already exists")
    # -------- DELETE TRANSACTION DATA --------
    st.markdown("---")
    st.subheader("🗑️ Delete Transaction Data")

    st.warning("⚠️ This action is irreversible. Please proceed carefully.")

    col1, col2 = st.columns(2)

    with col1:
        del_start_date = st.date_input("From Date", key="del_from")

    with col2:
        del_end_date = st.date_input("To Date", key="del_to")

    df_check = pd.read_sql("SELECT * FROM donations", conn)

    filtered_delete = pd.DataFrame()

    if not df_check.empty:
        df_check["timestamp"] = pd.to_datetime(df_check["timestamp"])

        filtered_delete = df_check[
            (df_check["timestamp"].dt.date >= del_start_date) &
            (df_check["timestamp"].dt.date <= del_end_date)
        ]

        st.info(f"Records to be deleted: {len(filtered_delete)}")

        if len(filtered_delete) > 0:

            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = False

            if st.button("⚠️ Confirm Delete", key="confirm_del"):
                st.session_state.confirm_delete = True

            if st.session_state.confirm_delete:

                if st.button("🔥 Final Delete (Permanent)", key="final_del"):

                    conn.execute("""
                        DELETE FROM donations
                        WHERE DATE(timestamp) BETWEEN ? AND ?
                    """, (del_start_date, del_end_date))

                    conn.commit()

                    st.success("✅ Transaction data deleted successfully")

                    st.session_state.confirm_delete = False
                    st.rerun()

    else:
        st.info("No transaction data available")