import html
import re
from datetime import date, datetime

import pandas as pd
import streamlit as st

from database import (init_database, get_services, get_service_by_id,
                      add_service, delete_service,
                      get_booked_times, create_booking, get_customer_bookings,
                      get_bookings, update_booking_status, SLOTS)

st.set_page_config(page_title="LocalServe",layout="wide")
init_database()

# ---------- Styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&display=swap');

.block-container {padding-top: 2rem; max-width: 1200px;}
.stApp h1, .stApp h2, .stApp h3 {font-family: 'Poppins', sans-serif; color: #0F172A;}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #EFF6FF, #DBEAFE);
}

/* Cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF; border-radius: 16px; border: 1px solid #E2E8F0;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
    transition: box-shadow 0.2s, transform 0.2s;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 10px 26px rgba(37, 99, 235, 0.18);
    transform: translateY(-3px);
}

/* Stat boxes */
div[data-testid="stMetric"] {
    background: #FFFFFF; border: 1px solid #E2E8F0;
    border-left: 5px solid #2563EB; border-radius: 12px; padding: 14px 16px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

/* Buttons */
button {border-radius: 999px !important; font-weight: 600 !important;}
button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primaryFormSubmit"] {
    background: linear-gradient(135deg, #2563EB, #06B6D4) !important;
    border: none !important; color: #FFFFFF !important;
}

/* Hero banner */
.hero {
    background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 55%, #06B6D4 100%);
    padding: 44px 36px; border-radius: 22px; margin-bottom: 16px;
    position: relative; overflow: hidden;
}
.hero::after {
    content: ""; position: absolute; right: -60px; top: -60px;
    width: 260px; height: 260px; border-radius: 50%;
    background: rgba(255, 255, 255, 0.10);
}
.hero-title {font-family: 'Poppins', sans-serif; color: #FFFFFF;
             font-size: 2.8rem; font-weight: 700;}
.hero-tag {color: #E0F2FE; font-size: 1.35rem; font-weight: 600; margin: 6px 0 10px 0;}
.hero-text {color: #F0F9FF; font-size: 1.05rem; max-width: 620px;}

/* Feature strip */
.strip {display: flex; gap: 12px; flex-wrap: wrap; margin: 6px 0 14px 0;}
.strip span {
    background: #EFF6FF; color: #1E40AF; padding: 8px 16px;
    border-radius: 999px; font-weight: 600; font-size: 0.9rem;
    border: 1px solid #BFDBFE;
}

/* Service cards */
.badge {padding: 4px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 600;}
.price {font-size: 1.35rem; font-weight: 700; color: #1D4ED8; margin: 6px 0;}
.price span {font-size: 0.9rem; font-weight: 500; color: #64748B;}

/* How it works */
.step {
    background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px;
    padding: 22px 18px; text-align: center;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
}
.num {
    width: 46px; height: 46px; border-radius: 50%; margin: 0 auto 10px auto;
    background: linear-gradient(135deg, #2563EB, #06B6D4); color: #FFFFFF;
    font-size: 1.3rem; font-weight: 700; line-height: 46px;
}
.step-t {font-weight: 700; color: #0F172A;}
.step-d {color: #64748B; font-size: 0.9rem; margin-top: 4px;}

footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

PAGES = ["Home", "Services", "Book a Service", "My Bookings", "Admin Dashboard"]

# Demo admin login (fine for a college project)
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# Colour and icon for each category (unknown categories get the default)
CATEGORY_COLORS = {
    "Salon": "#EC4899", "Home Cleaning": "#10B981", "Laptop Repair": "#F59E0B",
    "Tutoring": "#8B5CF6", "Photography": "#EF4444", "Fitness Training": "#06B6D4",
}
CATEGORY_ICONS = {
    "Salon": "✂️", "Home Cleaning": "🧹", "Laptop Repair": "💻",
    "Tutoring": "📚", "Photography": "📷", "Fitness Training": "🏋️",
}

# Remember which page is open, and whether admin is logged in
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False


def go_to_booking(service_id):
    """Called when a Book Now button is clicked."""
    st.session_state.booking_service = service_id
    st.session_state.page = "Book a Service"


def style_status(df):
    """Colour the Status column of a table."""
    colors = {
        "Pending": "background-color:#FEF3C7;color:#92400E",
        "Confirmed": "background-color:#DBEAFE;color:#1E40AF",
        "Completed": "background-color:#DCFCE7;color:#166534",
        "Rejected": "background-color:#FEE2E2;color:#991B1B",
    }
    return df.style.map(lambda v: colors.get(v, ""), subset=["Status"])


def service_card(s, prefix, show_description=False):
    """Draw one service card."""
    color = CATEGORY_COLORS.get(s["category"], "#64748B")
    icon = CATEGORY_ICONS.get(s["category"], "🛎️")
    category = html.escape(s["category"])
    with st.container(border=True):
        st.markdown(
            f'<span class="badge" style="background:{color}22;color:{color}">'
            f'{icon} {category}</span>', unsafe_allow_html=True)
        st.subheader(s["service_name"])
        st.write(f"🏢 {s['provider_name']}")
        if show_description:
            st.caption(s["description"])
        st.markdown(
            f'<div class="price">₹{s["price"]:,} '
            f'<span>· ⏱️ {s["duration"]} min</span></div>',
            unsafe_allow_html=True)
        st.button("Book Now", key=f"{prefix}_{s['id']}",
                  on_click=go_to_booking, args=(s["id"],))


def show_cards(services, prefix, show_description=False):
    """Show services in rows of 3 cards."""
    for start in range(0, len(services), 3):
        cols = st.columns(3)
        for col, s in zip(cols, services[start:start + 3]):
            with col:
                service_card(s, prefix, show_description)


# ---------- Sidebar ----------
st.sidebar.title(" LocalServe")
st.sidebar.caption("Book local services. Pick your time. Get it done.")
st.sidebar.radio("Go to", PAGES, key="page")
page = st.session_state.page


# ---------- Home ----------
def show_home():
    st.markdown("""
    <div class="hero">
        <div class="hero-title"> LocalServe</div>
        <div class="hero-tag">Book local services. Pick your time. Get it done.</div>
        <div class="hero-text">Find trusted local services, check available
        slots, and book appointments in minutes.</div>
    </div>
    <div class="strip">
        <span>⚡ Real-time available slots</span>
        <span>🚫 No double bookings</span>
        <span>🎫 Instant booking ID</span>
    </div>
    """, unsafe_allow_html=True)
    st.button("Book a Service", type="primary",
              on_click=lambda: st.session_state.update(page="Book a Service"))

    st.divider()
    st.header("Popular Services")
    show_cards(get_services()[:6], "home")

    st.divider()
    st.header("How LocalServe Works")
    steps = [
        ("1", "Choose a service", "Browse local providers"),
        ("2", "Check available slots", "See only free times"),
        ("3", "Book your appointment", "Enter your details"),
        ("4", "Get the service", "Show up and enjoy"),
    ]
    cols = st.columns(4)
    for col, (num, title, desc) in zip(cols, steps):
        with col:
            st.markdown(
                f'<div class="step"><div class="num">{num}</div>'
                f'<div class="step-t">{title}</div>'
                f'<div class="step-d">{desc}</div></div>',
                unsafe_allow_html=True)


# ---------- Services ----------
def show_services():
    st.title("Services")
    services = get_services()

    # Build the filter list from the database, so new categories appear automatically
    categories = ["All"] + sorted({s["category"] for s in services})
    choice = st.radio("Filter by category", categories, horizontal=True)

    if choice != "All":
        services = [s for s in services if s["category"] == choice]

    st.caption(f"{len(services)} service(s) found")
    if not services:
        st.info("No services found in this category.")
    show_cards(services, "svc", show_description=True)


# ---------- Booking helpers ----------
def clean_phone(text):
    """Return a 10-digit phone number, or None if invalid."""
    digits = re.sub(r"[\s\-]", "", text)
    if digits.startswith("+91"):
        digits = digits[3:]
    if re.fullmatch(r"[6-9]\d{9}", digits):
        return digits
    return None


def is_valid_email(text):
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text) is not None


def available_slots(provider, chosen_date):
    """All slots minus booked ones (and minus past times if today)."""
    booked = get_booked_times(provider, str(chosen_date))
    slots = [t for t in SLOTS if t not in booked]
    if chosen_date == date.today():
        now = datetime.now().time()
        slots = [t for t in slots
                 if datetime.strptime(t, "%I:%M %p").time() > now]
    return slots, booked


def show_confirmation():
    """Show the booking confirmation after a successful booking."""
    b = st.session_state.confirmation
    st.success(
        "✓ Booking Confirmed  \n\n"
        f"**Booking ID:** {b['code']}  \n"
        f"**Service:** {b['service']}  \n"
        f"**Provider:** {b['provider']}  \n"
        f"**Date:** {b['date']}  \n"
        f"**Time:** {b['time']}  \n"
        f"**Price:** ₹{b['price']:,}  \n"
        "**Status:** Pending"
    )
    st.info("Save your Booking ID. You can track it in My Bookings "
            "using your phone number.")

    def clear():
        del st.session_state["confirmation"]

    st.button("Make another booking", on_click=clear)


# ---------- Book a Service ----------
def show_booking():
    st.title("Book a Service")

    if "confirmation" in st.session_state:
        show_confirmation()
        return

    services = get_services()
    if not services:
        st.info("No services available yet.")
        return

    names = {s["id"]: f"{s['service_name']} - {s['provider_name']}"
             for s in services}

    # If the remembered service was deleted, forget it
    if st.session_state.get("booking_service") not in names:
        st.session_state.pop("booking_service", None)

    service_id = st.selectbox("Choose a service", list(names.keys()),
                              format_func=lambda i: names[i],
                              key="booking_service")
    service = get_service_by_id(service_id)

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns(4)
        c1.write(f"**Service**  \n{service['service_name']}")
        c2.write(f"**Provider**  \n{service['provider_name']}")
        c3.write(f"**Price**  \n₹{service['price']:,}")
        c4.write(f"**Duration**  \n{service['duration']} min")

    today = date.today()
    chosen_date = st.date_input("Select Date", value=today, min_value=today)

    st.subheader("Available Time")
    slots, booked = available_slots(service["provider_name"], chosen_date)
    slot = None
    if slots:
        slot = st.radio("Pick a time", slots, horizontal=True)
    else:
        st.warning("No slots available on this date. Please pick another date.")
    if booked:
        st.caption("Already booked: " + ", ".join(booked))

    st.subheader("Your Details")
    # A form sends all fields together when the button is clicked
    with st.form("booking_form"):
        name = st.text_input("Customer Name")
        phone = st.text_input("Phone Number")
        email = st.text_input("Email")
        confirm = st.checkbox("I confirm that these booking details are correct.")
        submitted = st.form_submit_button("Confirm Booking", type="primary")

    if submitted:
        if not name.strip() or not phone.strip() or not email.strip():
            st.error("Please fill in all required fields.")
        elif chosen_date < today:
            st.error("Please select a future date.")
        elif slot is None:
            st.error("Please select an available time slot.")
        elif not is_valid_email(email.strip()):
            st.error("Please enter a valid email address.")
        elif clean_phone(phone.strip()) is None:
            st.error("Please enter a valid phone number.")
        elif not confirm:
            st.error("Please tick the confirmation checkbox.")
        else:
            code = create_booking(name.strip(), clean_phone(phone.strip()),
                                  email.strip(), service, str(chosen_date), slot)
            if code is None:
                st.error("This time slot is no longer available. "
                         "Please select another slot.")
            else:
                st.session_state.confirmation = {
                    "code": code,
                    "service": service["service_name"],
                    "provider": service["provider_name"],
                    "date": chosen_date.strftime("%d %B %Y"),
                    "time": slot,
                    "price": service["price"],
                }
                st.rerun()


# ---------- My Bookings ----------
def show_my_bookings():
    st.title("My Bookings")
    st.write("Enter the phone number you used while booking.")

    with st.form("lookup_form"):
        phone = st.text_input("Phone Number")
        search = st.form_submit_button("Find My Bookings", type="primary")

    if search:
        if not phone.strip():
            st.error("Please fill in all required fields.")
            return
        digits = clean_phone(phone.strip())
        if digits is None:
            st.error("Please enter a valid phone number.")
            return

        rows = get_customer_bookings(digits)
        if not rows:
            st.info("No bookings found.")
            return

        table = pd.DataFrame([{
            "Booking ID": r["booking_code"],
            "Service": r["service_name"],
            "Provider": r["provider_name"],
            "Date": r["booking_date"],
            "Time": r["booking_time"],
            "Price": f"₹{r['price']:,}",
            "Status": r["status"],
        } for r in rows])

        st.success(f"{len(rows)} booking(s) found.")
        st.dataframe(style_status(table), hide_index=True,
                     use_container_width=True)


# ---------- Admin ----------
def show_admin_login():
    """Simple login form for the admin."""
    st.title("Admin Login")
    st.write("Please log in to manage bookings and services.")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login = st.form_submit_button("Login", type="primary")

    if login:
        if not username.strip() or not password.strip():
            st.error("Please fill in all required fields.")
        elif username.strip() == ADMIN_USER and password == ADMIN_PASS:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Incorrect username or password.")


def admin_bookings_tab():
    """Stats, booking table and status buttons."""
    rows = get_bookings()

    # ----- Stats -----
    pending = sum(1 for r in rows if r["status"] == "Pending")
    confirmed = sum(1 for r in rows if r["status"] == "Confirmed")
    completed = [r for r in rows if r["status"] == "Completed"]
    revenue = sum(r["price"] for r in completed)  # money from completed jobs

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Bookings", len(rows))
    c2.metric("Pending", pending)
    c3.metric("Confirmed", confirmed)
    c4.metric("Completed", len(completed))
    c5.metric("Total Revenue", f"₹{revenue:,}")

    st.divider()

    # ----- Booking table -----
    st.subheader("All Bookings")
    if not rows:
        st.info("No bookings found.")
        return

    table = pd.DataFrame([{
        "Booking ID": r["booking_code"],
        "Customer": r["customer_name"],
        "Phone": r["customer_phone"],
        "Service": r["service_name"],
        "Provider": r["provider_name"],
        "Date": r["booking_date"],
        "Time": r["booking_time"],
        "Price": f"₹{r['price']:,}",
        "Status": r["status"],
    } for r in rows])
    st.dataframe(style_status(table), hide_index=True, use_container_width=True)

    # ----- Change status -----
    st.subheader("Manage a Booking")
    by_id = {r["id"]: r for r in rows}
    chosen_id = st.selectbox(
        "Select a booking", list(by_id.keys()),
        format_func=lambda i: (f"{by_id[i]['booking_code']} - "
                               f"{by_id[i]['customer_name']} - "
                               f"{by_id[i]['service_name']} "
                               f"({by_id[i]['status']})"))
    status = by_id[chosen_id]["status"]
    st.write(f"Current status: **{status}**")

    b1, b2, b3 = st.columns(3)
    # Pending -> Confirmed or Rejected;  Confirmed -> Completed
    if b1.button("✅ Confirm", disabled=status != "Pending"):
        update_booking_status(chosen_id, "Confirmed")
        st.rerun()
    if b2.button("❌ Reject", disabled=status != "Pending"):
        update_booking_status(chosen_id, "Rejected")
        st.rerun()
    if b3.button("🏁 Complete", disabled=status != "Confirmed"):
        update_booking_status(chosen_id, "Completed")
        st.rerun()


def admin_services_tab():
    """Add and delete services."""
    # Show a message left over from the last action (add / delete)
    message = st.session_state.pop("service_message", None)
    if message:
        st.success(message)

    # ----- Add a service -----
    st.subheader("Add a Service")
    existing = sorted({s["category"] for s in get_services()})

    with st.form("add_service_form", clear_on_submit=True):
        service_name = st.text_input("Service Name")
        c1, c2 = st.columns(2)
        category = c1.selectbox("Category", existing) if existing else None
        new_category = c2.text_input("Or type a new category (optional)")
        provider = st.text_input("Provider Name")
        description = st.text_area("Description")
        c3, c4 = st.columns(2)
        price = c3.number_input("Price (₹)", min_value=0, value=500, step=50)
        duration = c4.number_input("Duration (minutes)", min_value=0,
                                   value=60, step=15)
        add = st.form_submit_button("Add Service", type="primary")

    if add:
        final_category = new_category.strip() or category
        if (not service_name.strip() or not provider.strip()
                or not description.strip() or not final_category):
            st.error("Please fill in all required fields.")
        elif price <= 0 or duration <= 0:
            st.error("Price and duration must be greater than zero.")
        else:
            add_service(service_name.strip(), final_category,
                        provider.strip(), description.strip(),
                        int(price), int(duration))
            st.session_state.service_message = (
                f"Service '{service_name.strip()}' added.")
            st.rerun()

    st.divider()

    # ----- Existing services -----
    st.subheader("Existing Services")
    services = get_services()
    if not services:
        st.info("No services found.")
        return

    table = pd.DataFrame([{
        "ID": s["id"],
        "Service": s["service_name"],
        "Category": s["category"],
        "Provider": s["provider_name"],
        "Price": f"₹{s['price']:,}",
        "Duration": f"{s['duration']} min",
    } for s in services])
    st.dataframe(table, hide_index=True, use_container_width=True)

    # ----- Delete a service -----
    st.subheader("Delete a Service")
    by_id = {s["id"]: s for s in services}
    delete_id = st.selectbox(
        "Select a service to delete", list(by_id.keys()),
        format_func=lambda i: (f"{by_id[i]['service_name']} - "
                               f"{by_id[i]['provider_name']}"))
    sure = st.checkbox("Yes, delete this service")
    if st.button("🗑️ Delete Service"):
        if not sure:
            st.error("Please tick the checkbox to confirm.")
        else:
            delete_service(delete_id)
            st.session_state.service_message = (
                f"Service '{by_id[delete_id]['service_name']}' deleted.")
            st.rerun()


def admin_analytics_tab():
    """Simple charts built with Pandas."""
    rows = get_bookings()
    if not rows:
        st.info("No bookings found.")
        return

    # Put the bookings into a Pandas table
    df = pd.DataFrame([{
        "Service": r["service_name"],
        "Status": r["status"],
        "Price": r["price"],
    } for r in rows])

    done = df[df["Status"] == "Completed"]

    # ----- Summary numbers -----
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Bookings", len(df))
    c2.metric("Completed", len(done))
    c3.metric("Pending", int((df["Status"] == "Pending").sum()))
    c4.metric("Revenue", f"₹{int(done['Price'].sum()):,}")

    st.divider()

    # ----- Bookings by service -----
    st.subheader("Bookings by Service")
    counts = df.groupby("Service").size().sort_values(ascending=False)
    st.bar_chart(counts, color="#2563EB")
    st.dataframe(counts.reset_index(name="Bookings"),
                 hide_index=True, use_container_width=True)

    # ----- Bookings by status -----
    st.subheader("Bookings by Status")
    st.bar_chart(df.groupby("Status").size(), color="#06B6D4")

    # ----- Revenue by service (completed only) -----
    st.subheader("Revenue by Service")
    if done.empty:
        st.info("No completed bookings yet.")
    else:
        st.bar_chart(done.groupby("Service")["Price"].sum(), color="#10B981")


def show_admin_dashboard():
    """Shown only after a successful login."""
    st.title("Admin Dashboard")

    def logout():
        st.session_state.admin_logged_in = False

    st.button("Logout", on_click=logout)

    tab1, tab2, tab3 = st.tabs(["📋 Bookings", "🛠️ Manage Services",
                                "📊 Analytics"])
    with tab1:
        admin_bookings_tab()
    with tab2:
        admin_services_tab()
    with tab3:
        admin_analytics_tab()


def show_admin():
    if st.session_state.admin_logged_in:
        show_admin_dashboard()
    else:
        show_admin_login()


# ---------- Page router ----------
if page == "Home":
    show_home()
elif page == "Services":
    show_services()
elif page == "Book a Service":
    show_booking()
elif page == "My Bookings":
    show_my_bookings()
elif page == "Admin Dashboard":
    show_admin()