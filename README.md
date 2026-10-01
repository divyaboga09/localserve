# LocalServe

**Book local services. Pick your time. Get it done.**

**Live demo:** https://localserve-bydivyasrinivas.streamlit.app

LocalServe is a lightweight local service booking system for small providers such as salons, tutors, repair shops, photographers, cleaners, and fitness trainers. Its main feature is real-time available time-slot management: customers can only select slots that are actually free.

## Features

- Customer sign-up and login (passwords stored as salted hashes)
- Service browsing with category filters
- Real-time available slots (no double bookings)
- Booking with a unique booking ID
- My Bookings page showing only the logged-in customer's bookings
- Admin dashboard with statistics, customer list, and analytics
- Booking status management (Confirm, Reject, Complete)
- Service management (add and delete services)

## Technologies

- Python 3
- Streamlit
- SQLite
- Pandas

## How to run

1. Install the requirements:

       pip install -r requirements.txt

2. Start the app:

       streamlit run app.py

The database and sample services are created automatically on the first run.

## Admin Login

For local use, the demo login is `admin` / `admin123`.
The hosted version uses private credentials set in Streamlit secrets.

## Project Structure

    localserve/
    ├── app.py             # Streamlit pages and UI
    ├── database.py        # SQLite and password functions
    ├── requirements.txt
    ├── README.md
    └── assets/