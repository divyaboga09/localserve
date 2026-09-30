# LocalServe

**Book local services. Pick your time. Get it done.**

LocalServe is a lightweight local service booking system for small providers such as salons, tutors, repair shops, photographers, cleaners, and fitness trainers. Its main feature is real-time available time-slot management: customers can only select slots that are actually free.

## Features

- Service browsing with category filters
- Provider selection, prices, and durations
- Real-time available slots (no double bookings)
- Customer booking with a unique booking ID
- Booking tracking by phone number
- Admin dashboard with booking statistics
- Booking status management (Confirm, Reject, Complete)
- Service management (add and delete services)
- Basic analytics with charts

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

The database (`localserve.db`) and sample services are created automatically on the first run.

## Admin Login

- Username: `admin`
- Password: `admin123`

(Demo credentials for a college project only.)

## Project Structure

    localserve/
    ├── app.py             # Streamlit pages and UI
    ├── database.py        # SQLite functions
    ├── requirements.txt
    ├── README.md
    └── assets/