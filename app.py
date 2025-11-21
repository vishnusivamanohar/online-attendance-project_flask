from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import concurrent.futures
import threading
from collections import defaultdict
import smtplib
import requests
import time
import functools # We need this for our decorator

app = Flask(__name__)

# --- SECURITY WARNING: SECRET KEY ---
# This key is used to encrypt the user's session cookie.
# It MUST be a long, random, and secret string. Do not share it or commit it to public repositories.
# For production, it's best to load this from an environment variable.
app.secret_key = 'a-very-long-and-random-secret-key-should-go-here'

# --- SECURITY WARNING: DATABASE & EMAIL CREDENTIALS ---
# Storing credentials directly in the code is a major security risk.
# Anyone with access to this code can see your passwords.
# It is highly recommended to use environment variables to store sensitive data.
OWN_EMAIL = "vishnuthotapalli2022@gmail.com"
OWN_PASSWORD = "mhfy ffnu vfns zlsr"
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Vishnu@2022', # Replace with your DB password
    'database': 'online_attendance'
}

# --- DATABASE HELPER ---
# Function to get a new database connection
def get_db_connection():
    """Creates and returns a new connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# --- 1. THE LOGIN REQUIRED DECORATOR ---
# This is the core of our security fix. A "decorator" is a function that wraps another function
# to add extra functionality. This one checks for a valid session before running the original route function.
def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if 'logged_in' is a key in the session dictionary.
        # The session is created only after a successful login.
        if 'logged_in' not in session:
            # If the user is not logged in, flash a message and redirect them to the login page.
            flash("You need to be logged in to view this page.", "warning")
            return redirect(url_for('login'))
        # If the user IS logged in, execute the original function they were trying to access (e.g., home_page, students_page).
        return f(*args, **kwargs)
    return decorated_function

# --- 2. AUTHENTICATION ROUTES (LOGIN, LOGOUT) ---

@app.route('/', methods=['GET', 'POST'])
def login():
    """Handles the login process."""
    # If the user is already logged in, don't show the login page again.
    if 'logged_in' in session:
        return redirect(url_for('home_page'))

    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')

        # --- IMPORTANT: This is a hardcoded password check for demonstration. ---
        # In a real application, you would hash passwords and check against the hashed value from a user database.
        if password == "vishnu@2022":
            # If the password is correct, create the session.
            # The session is a secure cookie stored on the user's browser.
            session['logged_in'] = True
            session['name'] = name
            flash(f"Welcome back, {name}!", "success")
            return redirect(url_for('home_page'))
        else:
            # If password is wrong, show an error on the login page.
            flash("Incorrect Password!", "danger")
            return render_template('password.html') # Re-render the login page with an error

    # If it's a GET request, just show the login page.
    return render_template('password.html')

@app.route('/logout')
def logout():
    """Clears the session to log the user out."""
    session.clear()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for('login'))


# --- 3. PROTECTED APPLICATION ROUTES ---
# Every route below now has the @login_required decorator.
# This ensures that the code inside these functions will ONLY run if the user is logged in.
# If they are not, the decorator will automatically redirect them to the login page.

@app.route('/home')
@login_required
def home_page():
    name = session.get('name', 'User') # Safely get the name from the session
    return render_template('home.html', name=name)

@app.route('/students')
@login_required
def students_page():
    return render_template('students.html')

# (The rest of your routes follow the same pattern: add @login_required)

@app.route('/sem_year_options')
@login_required
def sem_year_options():
    return render_template('sem_year_options.html')

@app.route('/display_attendance')
@login_required
def display_attendance():
    return render_template('display_attendance.html')

@app.route('/student_attendance')
@login_required
def student_attendance():
    return render_template('student_attendance.html')

@app.route('/attendance_persentage')
@login_required
def attendance_persentage():
    return render_template('attendance_persentage.html')

@app.route('/attendance')
@login_required
def attendance_page():
    return render_template('attendance.html')

@app.route('/mail')
@login_required
def mail_page():
    return render_template('mail.html')

@app.route('/select_to_send')
@login_required
def select_to_send():
    return render_template('select_to_send.html')

@app.route('/about')
@login_required
def about_page():
    return render_template('about.html')

@app.route('/about-me')
@login_required
def about_page2():
    return render_template('about-me.html')

@app.route('/view_students')
@login_required
def view_students():
    return render_template('view_students.html')

@app.route('/add_students')
@login_required
def add_students():
    return render_template('add_students.html')

@app.route('/delete_students')
@login_required
def delete_students():
    return render_template('delete_students.html')

@app.route('/delete_students_table')
@login_required
def delete_students_table():
    return render_template('delete_students_table.html')

# --- 4. PROTECTED FORM HANDLING ROUTES ---

@app.route('/add', methods=['POST'])
@login_required
def add():
    if request.method == 'POST':
        branch = request.form.get('branch')
        section = request.form.get('section')
        year = request.form.get('year')
        num_students = request.form.get('no_of_students')

        if not all([branch, section, year, num_students]):
            flash("All fields are required to add students.", "warning")
            return redirect(url_for('add_students'))

        student_table_name = f"{year}_{branch}_{section}"
        return render_template('add_students_table.html', count=int(num_students), table_name=student_table_name)
    return redirect(url_for('add_students'))


@app.route('/add_students_table', methods=['POST'])
@login_required
def add_students_table():
    conn = None
    act = None
    if request.method == 'POST':
        table_name = request.form.get('table_name')
        count = int(request.form.get('count'))
        attendance_table_name = f"{table_name}_Attendance"
        try:
            conn = get_db_connection()
            if conn is None:
                flash("Database connection failed.", "danger")
                return redirect(url_for('students_page'))

            cursor = conn.cursor()
            for i in range(count):
                name = request.form.get(f'name{i}')
                roll = request.form.get(f'roll{i}')
                phone = request.form.get(f'phone{i}')
                email = request.form.get(f'email{i}') or None # Set to None if empty

                # Insert into student details table
                cursor.execute(f'''
                    INSERT INTO `{table_name}` (roll_number, full_name, mobile_number, email)
                    VALUES (%s, %s, %s, %s)
                ''', (roll, name, phone, email))

                # Insert into attendance table
                cursor.execute(f'''
                    INSERT INTO `{attendance_table_name}` (roll_number, full_name)
                    VALUES (%s, %s)
                ''', (roll, name))
            conn.commit()
            act = "add"
            flash(f"{count} students added successfully!", "success")
        except mysql.connector.Error as err:
            print(f"Database error on add: {err}")
            act = "noadd"
            flash(f"Error adding students: {err}", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
    return render_template('students.html', action=act)


@app.route('/delete_students', methods=['POST'])
@login_required
def delete_student_form():
    # Renamed from delete_student to avoid conflict with a potential future function
    if request.method == 'POST':
        branch = request.form.get('branch')
        section = request.form.get('section')
        year = request.form.get('year')
        num_students = request.form.get('no_of_students')

        if not all([branch, section, year, num_students]):
            flash("All fields are required to select students for deletion.", "warning")
            return redirect(url_for('delete_students'))

        student_table_name = f"{year}_{branch}_{section}"
        return render_template('delete_students_table.html', count=int(num_students), table_name=student_table_name)
    return redirect(url_for('delete_students'))


@app.route('/delete', methods=['POST'])
@login_required
def delete():
    table_name = request.form.get('table_name')
    related_table = f"{table_name}_Attendance"
    count = int(request.form.get('count'))
    conn = None
    act = "nodel"
    try:
        conn = get_db_connection()
        if conn is None:
            flash("Database connection failed.", "danger")
            return redirect(url_for('students_page'))
        cursor = conn.cursor()
        deleted_count = 0
        for i in range(count):
            roll_number = request.form.get(f'roll{i}')
            if roll_number:
                cursor.execute(f"DELETE FROM `{table_name}` WHERE roll_number = %s", (roll_number,))
                if cursor.rowcount > 0:
                    deleted_count += 1
                cursor.execute(f"DELETE FROM `{related_table}` WHERE roll_number = %s", (roll_number,))
        conn.commit()
        if deleted_count > 0:
            act = "del"
            flash(f"Successfully deleted {deleted_count} student(s).", "success")
        else:
            flash("No matching students found to delete.", "warning")

    except mysql.connector.Error as e:
        print(f"Database error on delete: {e}")
        flash(f"An error occurred while deleting: {e}", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template('students.html', action=act)


@app.route('/display', methods=['POST'])
@login_required
def display():
    if request.method == 'POST':
        branch = request.form.get('branch')
        section = request.form.get('section')
        year = request.form.get('year')
        table_name = f"{year}_{branch}_{section}"
        conn = None
        try:
            conn = get_db_connection()
            if conn is None:
                 flash("Database connection failed.", "danger")
                 return redirect(url_for('students_page'))
            cursor = conn.cursor(dictionary=True)
            query = f"SELECT * FROM `{table_name}` ORDER BY roll_number ASC"
            cursor.execute(query)
            data = cursor.fetchall()
            return render_template('table.html', data=data, table_name=table_name)
        except mysql.connector.Error as err:
            flash(f"Could not display students. The class might not exist. Error: {err}", "danger")
            return redirect(url_for('view_students'))
        finally:
            if conn and conn.is_connected():
                conn.close()
    return redirect(url_for('students_page'))

@app.route('/apply_attendance', methods=['GET', 'POST'])
def apply_attendance():
    
    time = datetime.now().strftime("%H:%M")  # Example: 14:30
    day = datetime.now().strftime("%A")
    holidays = [
    "01-01",  # New Year's Day
    "14-01",  # Makar Sankranti / Pongal (some states consider it fixed)
    "26-01",  # Republic Day
    "14-04",  # Dr. B.R. Ambedkar Jayanti
    "15-08",  # Independence Day
    "02-10",  # Gandhi Jayanti
    "25-12",  # Christmas
    ]

    if request.method == 'POST':
        # Get form data
        branch = request.form.get('branch')
        section = request.form.get('section')
        year = request.form.get('year')
        # Determine the table name based on branch and section
        table_name = f"{year}_{branch}_{section}_Attendance"  # Example: AIML_A_Attendance

        # Get today's date in the format DD-MMM-YYYY (e.g., 01-MAR-2025)
        today_date = datetime.now().strftime("%d-%b-%Y").upper()
        day_month = datetime.now().strftime("%d-%b").upper()
        print(day_month)
        if "09:00" <= time < "10:00":
            a=1
            period="period-1"
            column_name = today_date + "_p1"
        elif "10:00" <= time < "10:55":
            a=2
            period="period-2"
            column_name = today_date + "_p2"
        elif "11:10" <= time < "12:05":
            a=3
            period="period-3"
            column_name = today_date +"_p3"
        elif "12:05" <= time < "13:00":
            a=4
            period="period-4"
            column_name = today_date + "_p4"
        elif "13:45" <= time < "14:40":
            a=5
            period="period-5"
            column_name = today_date + "_p5"
        elif "14:40" <= time < "15:35":
            a=6
            period="period-6"
            column_name = today_date + "_p6"
        elif "15:35" <= time < "16:30":
            a=7
            period="period-7"
            column_name = today_date + "_p7"
        else:
            column_name = None  # No matching period
        if column_name != None and day!="Sunday" and day_month not in holidays:
            try:
                # Connect to the MySQL database
                connection = get_db_connection()
                cursor = connection.cursor(dictionary=True)

                # Check if the column for today's date already exists
                cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE '{column_name}'")
                column_exists = cursor.fetchone()

                # If the column does not exist, add it to the table
                if not column_exists:
                    alter_query = f"ALTER TABLE {table_name} ADD COLUMN `{column_name}` VARCHAR(10) DEFAULT 'A'"
                    cursor.execute(alter_query)
                    connection.commit()
                # Query to fetch data from the selected table
                query = f"SELECT * FROM {table_name} ORDER BY roll_number ASC"
                cursor.execute(query)

                # Fetch all rows
                data = cursor.fetchall()

                # Close the connection
                cursor.close()
                connection.close()

                # Render the HTML template with the data and today's date
                return render_template('apply_attendance.html', data=data, table_name=table_name,period=period,column_name=column_name,today_date=today_date)

            except mysql.connector.Error as err:
                return f"Error: {err}"
        
            # If it's a GET request, just render the form
            return render_template('attendance.html',action="yes")
        else:
            return render_template('attendance.html',action="no")
        
@app.route('/save_attendance', methods=['POST'])
def save_attendance():
    if request.method == 'POST':
        # Get form data
        branch = request.form.get('branch')
        section = request.form.get('section')
        year = request.form.get('year')
        column_name = request.form.get('column_name')

        # Check if column_name is valid
        if not column_name:
            return "Error: Column name is missing!", 400

        # Determine the table name dynamically
        table_name = f"{year}_{branch}_{section}_Attendance"

        try:
            # Connect to MySQL
            connection = get_db_connection()
            cursor = connection.cursor()

            # Loop through attendance checkboxes
            for key in request.form:
                if key.startswith('attendance_'):
                    roll_number = key.split('_')[1]  # Extract roll number
                    attendance_status = 'P' if request.form.get(key) else 'A'

                    # Update attendance in database
                    update_query = f"UPDATE `{table_name}` SET `{column_name}` = %s WHERE roll_number = %s"
                    cursor.execute(update_query, (attendance_status, roll_number))

            # Commit changes
            connection.commit()

        except mysql.connector.Error as err:
            print("MySQL Error:", err)
            return "Database error!", 500


        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()

        return render_template("attendance.html", message="Attendance updated successfully!")

@app.route('/display_attendance_table', methods=['GET', 'POST'])
def display_attendance_table():
    if request.method == 'POST':
        branch = request.form.get('branch')
        section = request.form.get('section')
        year = request.form.get('year')
        table_name = f"{year}_{branch}_{section}_Attendance"

        try:
            # Connect to MySQL
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            # Fetch data
            query = f"SELECT * FROM `{table_name}` ORDER BY roll_number ASC"
            cursor.execute(query)
            data = cursor.fetchall()

            # Get column names
            column_names = [column[0] for column in cursor.description]

            cursor.close()
            connection.close()

            # Extract full date-period structure
            full_dates = defaultdict(list)

            for col in column_names:
                if "_" in col and col not in ["roll_number", "full_name"]:
                    date, period = col.rsplit('_', 1)
                    full_dates[date].append(period)

            # Fill all p1 to p7 for each date (to ensure alignment)
            for date in full_dates:
                full_dates[date] = [f"p{i}" for i in range(1, 8)]

            return render_template('display_attendance_table.html',
                                   data=data,
                                   full_dates=full_dates,
                                   table_name=table_name)

        except mysql.connector.Error as err:
            return f"Error: {err}"

    return render_template('attendance_page.html', action="yes")
    
        
@app.route('/attendance_persentage_table', methods=['GET', 'POST'])
def attendance_persentage_table():
    if request.method == 'POST':
        # Get form data
        branch = request.form.get('branch')
        section = request.form.get('section')
        year = request.form.get('year')
        # Determine the table name based on branch and section
        table_name = f"{year}_{branch}_{section}_Attendance"  # Example: AIML_A_Attendance or AIML_B_Attendance

        try:
            # Connect to the MySQL database
            connection = mysql.connector.connect(**db_config)
            cursor = connection.cursor(dictionary=True)

            # Query to fetch data from the selected table
            query = f"SELECT * FROM {table_name} ORDER BY roll_number ASC"
            cursor.execute(query)

            # Fetch all rows
            data = cursor.fetchall()

            # Get column names (excluding 'id' and 'roll_number')
            column_names = [desc[0] for desc in cursor.description if desc[0] not in ['roll_number']]

            # Calculate total columns (excluding 'id' and 'roll_number')
            total_columns = len(column_names)

           
            # Close the connection
            cursor.close()
            connection.close()

            # Render the HTML template with the data and calculated values
            return render_template('attendance_persentage_table.html', data=data, table_name=table_name,
                                   total_columns=total_columns)

        except mysql.connector.Error as err:
            return f"Error: {err}"
    return render_template('attendance.html')
    
@app.route('/change_class_year')
def change_class_year():
    
    try:
         
        conn = get_db_connection()
        cursor = conn.cursor()
                
        # Fetch all tables from the database
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()  # Fetch all table names as a list of tuples 
        for table in tables:
            table_name = table[0]  # Extract table name
            parts = table_name.split("_")  # Split table name using "_"

            new_table = None  # Initialize to avoid UnboundLocalError

            if len(parts) == 3:
                if parts[0] == "1":
                    new_table = f"2_{parts[1]}_{parts[2]}"
                elif parts[0] == "2":
                    new_table = f"3_{parts[1]}_{parts[2]}"
                elif parts[0] == "3":
                    new_table = f"4_{parts[1]}_{parts[2]}"
                elif parts[0] == "4":
                    new_table = f"1_{parts[1]}_{parts[2]}"
                    cursor.execute(f"TRUNCATE TABLE `{table_name}`")  # Truncate only if year is 4

            elif len(parts) == 4:
                if parts[0] == "1":
                    new_table = f"2_{parts[1]}_{parts[2]}_{parts[3]}"
                elif parts[0] == "2":
                    new_table = f"3_{parts[1]}_{parts[2]}_{parts[3]}"
                elif parts[0] == "3":
                    new_table = f"4_{parts[1]}_{parts[2]}_{parts[3]}"
                elif parts[0] == "4":
                    new_table = f"1_{parts[1]}_{parts[2]}_{parts[3]}"
                    cursor.execute(f"TRUNCATE TABLE `{table_name}`")  # Truncate only if year is 4
            if new_table:  # Check if new_table was assigned
                cursor.execute(f"RENAME TABLE `{table_name}` TO `{new_table}`")

        act = "che"  # Success
    except mysql.connector.Error as err:
        act = "noche"
    finally:
        if conn:
            conn.close()
    return render_template('students.html',action=act)


@app.route('/delete_attendance_data')
def delete_attendance_data():
    
    try:
         
        conn = get_db_connection()
        cursor = conn.cursor()
                
        # Fetch all tables from the database
        cursor.execute("SHOW TABLES LIKE '%attendance'")
        tables = cursor.fetchall()  # Fetch all table names as a list of tuples 
        for table in tables:
            cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table[0]}'")
            columns = cursor.fetchall()
            for column in columns:
                if column[0] !="roll_number":
                    cursor.execute(f"ALTER TABLE `{table[0]}` DROP COLUMN `{column[0]}`")
                    
        act = "del"  # Success
    except mysql.connector.Error as err:
        act = "nodel"
    finally:
        if conn:
            conn.close()
    return render_template('sem_year_options.html',action=act)


@app.route('/send_mail', methods=['POST'])
def send_mail():
    email = request.form['email']
    subject = request.form['subject']
    message = request.form['message']

    status = send_email(email, subject, message)
    if status:
        return render_template("mail.html", action="Mail Sent Successfully!")
    else:
        return render_template("mail.html", action="Error! Mail not sent.")

@app.route('/Select_to_send', methods=['POST'])
def Select_to_send():
    #subject = request.form.get('subject')    
    #message = request.form.get('message')
    #print("------------------------------------------------------------------",message)
    subject = "hi this is from flask"
    message = "test 8"
    # Get form data
    branch = request.form.get('branch')
    section = request.form.get('section')
    year = request.form.get('year')
    table_name = f"{year}_{branch}_{section}"  # Example: AIML_A or AIML_B
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()

        cursor.execute(f"SELECT email FROM {table_name}")
        email_list = [row[0] for row in cursor.fetchall()]

        cursor.close()
        connection.close()
        a=0
        for email in email_list :
            status = send_email(email, subject, message)
            if status:
                a+=1
                print(a,email)
        if a>0:
            return render_template("mail.html", action="Mail Sent Successfully!")
        else:
            return render_template("mail.html", action="Error! Mail not sent.")

    except mysql.connector.Error as err:
        print( f"Error: {err}")
        return render_template('mail.html',action="Error! Mail not sent.")
        

def send_email(email, subject, message):
    try:
        email_message = f"Subject: {subject}\n\n{message}"
        with smtplib.SMTP("smtp.gmail.com", 587) as connection:
            connection.starttls()
            connection.login(OWN_EMAIL, OWN_PASSWORD)
            connection.sendmail(from_addr=OWN_EMAIL, to_addrs=email, msg=email_message)
        return True
    except Exception as er:
        print(f"Error sending email: {er}")
        return False

if __name__ == '__main__':
    # debug=True is useful for development but should be set to False in a production environment.
    app.run(host="127.0.0.1", port=5000, debug=True)
