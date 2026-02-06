from flask import Flask, render_template, request, redirect, flash, session
from flask_mail import Mail, Message
import pymysql, uuid, os
from dotenv import load_dotenv
from pymysql.err import IntegrityError

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from werkzeug.security import check_password_hash
from config import Config

# ================= ENV =================
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ================= LIMITER =================
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    storage_uri=os.getenv("REDIS_URL", "memory://"),
    default_limits=["100 per minute"]
)

app.config.from_object(Config)
# ================= DB CONNECTION (Local + Aiven) =================
def get_db():
    # Aiven requires SSL; Local usually does not. 
    # Set MYSQL_SSL_MODE=REQUIRED in Render/Aiven environment variables.
    ssl_mode = os.getenv("MYSQL_SSL_MODE")
    
    config = {
        "host": os.getenv("MYSQL_HOST"),
        "port": int(os.getenv("MYSQL_PORT", 3306)),
        "user": os.getenv("MYSQL_USER"),
        "password": os.getenv("MYSQL_PASSWORD"),
        "database": os.getenv("MYSQL_DB"),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False
    }

    if ssl_mode:
        config["ssl"] = {"ssl_mode": ssl_mode}

    return pymysql.connect(**config)

# ================= MAIL =================
app.config.update(
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    MAIL_PORT=int(os.getenv("MAIL_PORT", 587)),
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER")
)
mail = Mail(app)

# ================= HOME =================
@app.route('/')
def home():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) c FROM teams")
        total_registrations = cur.fetchone()['c']
    finally:
        cur.close()
        conn.close()
    return render_template("home.html", total_registrations=total_registrations)

# ================= EMAIL =================
def send_approval_email(team_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT team_name, leader_email, registration_type
            FROM teams WHERE team_id=%s
        """, (team_id,))
        team = cur.fetchone()

        if not team or not team['leader_email']:
            return

        cur.execute("""
            SELECT student_id, member_name, phone, college_email
            FROM members WHERE team_id=%s ORDER BY student_id
        """, (team_id,))
        members = cur.fetchall()

        cur.execute("""
            SELECT event_name FROM team_events WHERE team_id=%s
        """, (team_id,))
        events = [e['event_name'] for e in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT wr.workshop_name
            FROM workshop_registrations wr
            JOIN members m ON wr.member_id = m.id
            WHERE m.team_id=%s
        """, (team_id,))
        workshops = [w['workshop_name'] for w in cur.fetchall()]

        body = f"""
🎉 NEXOVATE'26 – REGISTRATION APPROVED 🎉

Team ID : {team_id}
Team    : {team['team_name'] or 'Individual'}
Type    : {team['registration_type']}

==============================
👥 MEMBER DETAILS
==============================
"""
        for m in members:
            body += f"\nStudent ID : {m['student_id']}\nName       : {m['member_name']}\nPhone      : {m['phone']}\nEmail      : {m['college_email']}\n------------------------------\n"

        if events:
            body += "\n🎯 EVENTS:\n" + "\n".join(f"• {e}" for e in events)
        if workshops:
            body += "\n\n🛠 WORKSHOPS:\n" + "\n".join(f"• {w}" for w in workshops)

        body += "\n\n📍 Venue: Kongu Engineering College\n📅 Event: NEXOVATE'26\n"

        with mail.connect() as mail_conn:
            msg = Message(
                subject="NEXOVATE'26 – Registration Approved",
                recipients=[team['leader_email']],
                body=body
            )
            mail_conn.send(msg)
    except Exception as e:
        print(f"Mail Error: {e}")
    finally:
        cur.close()
        conn.close()

# ================= WORKSHOP LIMIT =================
def workshop_full(name):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT max_participants FROM events
            WHERE event_name=%s AND category='workshop'
        """, (name,))
        row = cur.fetchone()
        if not row or row['max_participants'] is None:
            return False

        cur.execute("""
            SELECT COUNT(*) c
            FROM workshop_registrations wr
            JOIN members m ON wr.member_id=m.id
            WHERE wr.workshop_name=%s
        """, (name,))
        count = cur.fetchone()['c']
        return count >= row['max_participants']
    finally:
        cur.close()
        conn.close()

# ================= TEAM =================
@app.route('/team', methods=['GET','POST'])
@limiter.limit("10 per minute")
def team():
    if request.method == 'POST':
        conn = get_db()
        cur = conn.cursor()
        try:
            names = request.form.getlist('member_name[]')
            years = request.form.getlist('study_year[]')
            depts = request.form.getlist('department[]')
            colleges = request.form.getlist('college_name[]')
            phones = request.form.getlist('phone[]')
            emails = request.form.getlist('college_email[]')
            workshops = request.form.getlist('workshop_choice[]')
            tech_events = request.form.getlist('tech_events[]')
            nontech_events = request.form.getlist('nontech_events[]')

            members = [
                (n,y,d,c,p,e)
                for n,y,d,c,p,e in zip(names,years,depts,colleges,phones,emails)
                if all([n,y,d,c,p,e])
            ]

            if not members or len(members) > 3:
                flash("Invalid participant count", "danger")
                return redirect('/team')

            # Capacity Check
            for w in workshops:
                if w and workshop_full(w):
                    flash(f"{w} workshop is full", "danger")
                    return redirect('/team')

            # Rule Validation
            if len(members) == 3:
                if not (set(nontech_events) & {'IPL Auction','Cleverquest'} or any(workshops)):
                    flash("3 members allowed only for specific events", "danger")
                    return redirect('/team')

            reg_type = "technical_nontech_workshop" if any(workshops) and (tech_events or nontech_events) else \
                       "technical_nontech" if nontech_events else \
                       "technical" if tech_events else "workshop_only"

            team_id = "NX" + uuid.uuid4().hex[:6].upper()
            leader_email = members[0][5]
            amount = len(members) * 250

            cur.execute("""
                INSERT INTO teams (team_id, team_name, leader_email, registration_type, member_count, amount_paid)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (team_id, request.form.get('team_name'), leader_email, reg_type, len(members), amount))

            member_ids = []
            for i, m in enumerate(members, 1):
                cur.execute("""
                    INSERT INTO members (team_id, student_id, member_name, study_year, department, college_name, phone, college_email)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (team_id, f"{team_id}-{i:02d}", *m))
                member_ids.append(cur.lastrowid)

            for ev in set(tech_events + nontech_events):
                cur.execute("INSERT INTO team_events (team_id,event_name) VALUES (%s,%s)", (team_id, ev))

            for mid, w in zip(member_ids, workshops):
                if w:
                    cur.execute("INSERT INTO workshop_registrations (member_id,workshop_name) VALUES (%s,%s)", (mid, w))

            conn.commit()
            return redirect(f"/payment/{team_id}")

        except IntegrityError:
            conn.rollback()
            flash("Duplicate data detected", "danger")
        except Exception as e:
            conn.rollback()
            print(f"Registration Error: {e}")
            flash("An error occurred. Please try again.", "danger")
        finally:
            cur.close()
            conn.close()

    return render_template("team_register.html")

# ================= PAYMENT =================
@app.route('/payment/<team_id>', methods=['GET','POST'])
def payment(team_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT amount_paid, member_count, transaction_id FROM teams WHERE team_id=%s", (team_id,))
        team = cur.fetchone()

        if not team:
            flash("Invalid payment link", "danger")
            return redirect('/')

        if request.method == 'POST':
            if team['transaction_id']:
                flash("Transaction already submitted", "warning")
                return redirect('/')

            cur.execute("""
                UPDATE teams SET transaction_id=%s, payment_status='WAITING'
                WHERE team_id=%s
            """, (request.form['transaction_id'], team_id))
            conn.commit()
            flash("Payment submitted successfully", "success")
            return redirect('/')
    finally:
        cur.close()
        conn.close()

    return render_template("payment.html", team_id=team_id, amount=team['amount_paid'], members=team['member_count'])

# ================= ADMIN LOGIN =================
# ================= ADMIN LOGIN (Plain Text Fix) =================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        cur = conn.cursor()
        try:
            # Plain text comparison: No hashing functions used
            query = "SELECT * FROM admin WHERE username=%s AND password=%s"
            cur.execute(query, (username, password))
            admin = cur.fetchone()
            
            if admin:
                session['admin_logged_in'] = True
                flash("Welcome back, Admin!", "success")
                return redirect('/admin/dashboard')
            else:
                flash("Invalid admin credentials", "danger")
        except Exception as e:
            flash(f"Database error: {str(e)}", "danger")
        finally:
            cur.close()
            conn.close()
            
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash("Please login as admin", "warning")
        return redirect('/admin/login')

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT t.*, GROUP_CONCAT(DISTINCT te.event_name) AS team_events
            FROM teams t
            LEFT JOIN team_events te ON t.team_id = te.team_id
            GROUP BY t.team_id
            ORDER BY t.created_at DESC
        """)
        teams = cur.fetchall()

        for t in teams:
            cur.execute("SELECT student_id, member_name, phone, college_email FROM members WHERE team_id=%s", (t['team_id'],))
            t['members'] = cur.fetchall()

            cur.execute("""
                SELECT DISTINCT wr.workshop_name FROM workshop_registrations wr
                JOIN members m ON wr.member_id = m.id WHERE m.team_id=%s
            """, (t['team_id'],))
            workshops = [w['workshop_name'] for w in cur.fetchall()]

            events = [t['team_events']] if t['team_events'] else []
            if workshops:
                events.append("Workshops: " + ", ".join(workshops))
            t['events'] = " | ".join(events) if events else "—"

        cur.execute("SELECT COUNT(*) c FROM teams WHERE payment_status='APPROVED'")
        total_paid = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) c FROM teams WHERE payment_status='WAITING'")
        pending_count = cur.fetchone()['c']
    finally:
        cur.close()
        conn.close()

    return render_template("admin/dashboard.html", teams=teams, total_paid=total_paid, pending_count=pending_count)

@app.route('/approve/<team_id>')
@limiter.limit("20 per minute")
def approve(team_id):
    if not session.get('admin_logged_in'):
        return redirect('/admin/login')

    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT payment_status FROM teams WHERE team_id=%s", (team_id,))
        row = cur.fetchone()

        if not row or row['payment_status'] == 'APPROVED':
            flash("Already approved or invalid team", "warning")
            return redirect('/admin/dashboard')

        cur.execute("UPDATE teams SET payment_status='APPROVED' WHERE team_id=%s", (team_id,))
        conn.commit()
        send_approval_email(team_id)
        flash("Payment approved & email sent", "success")
    finally:
        cur.close()
        conn.close()
    return redirect('/admin/dashboard')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/')

if __name__ == "__main__":
    # Render provides a PORT environment variable, otherwise use 5000 for local
    port = int(os.environ.get("PORT", 5000))
    # use 0.0.0.0 to make the server available externally on Render
    app.run(host="0.0.0.0", port=port, debug=True)