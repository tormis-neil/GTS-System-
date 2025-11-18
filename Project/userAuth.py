from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from . import db
from .models import Member, MembershipLog, GymPricing
from datetime import datetime, timedelta
import pytz
import re

userAuth = Blueprint('userAuth', __name__)

# ========================================
# HELPER: Email Validation
# ========================================
def is_valid_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ========================================
# HELPER: Calculate End Date
# ========================================
def calculate_end_date(start_date, gym_plan):
    """Calculate membership end date based on plan."""
    if gym_plan == 'Daily':
        return start_date + timedelta(days=1)
    elif gym_plan == 'Monthly':
        return start_date + timedelta(days=30)
    elif gym_plan == 'Annual':
        return start_date + timedelta(days=365)
    return start_date

# ========================================
# USER REGISTRATION
# ========================================
@userAuth.route('/user/register', methods=['GET', 'POST'])
def user_register():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('userRoutes.dashboard'))

    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        age = request.form.get('age', type=int)
        gender = request.form.get('gender')
        member_type = request.form.get('member_type')
        student_number = request.form.get('student_number', '').strip()
        gym_plan = request.form.get('gym_plan')
        contact_number = request.form.get('contact_number', '').strip()
        address = request.form.get('address', '').strip()

        # Validation
        errors = []

        if not first_name or not last_name:
            errors.append('First name and last name are required.')

        if not email or not is_valid_email(email):
            errors.append('Valid email is required.')

        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')

        if password != confirm_password:
            errors.append('Passwords do not match.')

        if not age or age < 1 or age > 120:
            errors.append('Valid age is required.')

        if gender not in ['Male', 'Female']:
            errors.append('Gender is required.')

        if member_type not in ['Student', 'Faculty', 'Outsider']:
            errors.append('Member type is required.')

        if member_type == 'Student' and not student_number:
            errors.append('Student number is required for students.')

        if gym_plan not in ['Daily', 'Monthly', 'Annual']:
            errors.append('Gym plan is required.')

        if gym_plan == 'Annual':
            errors.append('Annual plans are not available yet.')

        # Check for existing email
        existing_member = Member.query.filter_by(email=email).first()
        if existing_member:
            if existing_member.password_hash:
                errors.append('Email already registered. Please login instead.')
            else:
                # Allow claiming admin-created account
                errors.append('Email exists in our system. Please contact admin to activate your account.')

        # If validation fails, show errors
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('user_register.html')

        # Create new member
        tz = pytz.timezone('Asia/Manila')
        start_date = datetime.now(tz).date()
        end_date = calculate_end_date(start_date, gym_plan)

        new_member = Member(
            first_name=first_name,
            last_name=last_name,
            email=email,
            age=age,
            gender=gender,
            member_type=member_type,
            student_number=student_number if member_type == 'Student' else None,
            gym_plan=gym_plan,
            contact_number=contact_number,
            address=address,
            start_date=start_date,
            end_date=end_date,
            status='Active',
            is_self_registered=True
        )

        # Set password
        new_member.set_password(password)

        # Set price
        new_member.set_registration_price()

        # Save to database
        try:
            db.session.add(new_member)
            db.session.commit()

            # Create membership log
            log = MembershipLog(
                member_id=new_member.member_id,
                action_type='User Registration',
                remarks=f'User self-registered with {gym_plan} plan'
            )
            db.session.add(log)
            db.session.commit()

            flash(f'Registration successful! Your Member ID is {new_member.unique_code}. Please login.', 'success')
            return redirect(url_for('userAuth.user_login'))

        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            print(f"Registration error: {e}")
            return render_template('user_register.html')

    # GET request - show registration form
    return render_template('user_register.html')

# ========================================
# USER LOGIN
# ========================================
@userAuth.route('/user/login', methods=['GET', 'POST'])
def user_login():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('userRoutes.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        # Validation
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('user_login.html')

        # Find user
        member = Member.query.filter_by(email=email).first()

        if not member:
            flash('Invalid email or password.', 'error')
            return render_template('user_login.html')

        # Check if user has password (is self-registered)
        if not member.password_hash:
            flash('This account has not been activated yet. Please activate your account first.', 'warning')
            return redirect(url_for('userAuth.activate_account'))

        # Verify password
        if not member.check_password(password):
            flash('Invalid email or password.', 'error')
            return render_template('user_login.html')

        # Check membership status
        member.check_and_update_status()

        if member.status == 'Expired':
            flash('Your membership has expired. Please renew to continue.', 'warning')
            # Still allow login to see expired status

        # Login successful - create session
        session['user_id'] = member.member_id
        session['user_name'] = f"{member.first_name} {member.last_name}"
        session['user_email'] = member.email

        flash(f'Welcome back, {member.first_name}!', 'success')
        return redirect(url_for('userRoutes.dashboard'))

    # GET request - show login form
    return render_template('user_login.html')

# ========================================
# USER LOGOUT
# ========================================
@userAuth.route('/user/logout')
def user_logout():
    # Clear user session
    session.pop('user_id', None)
    session.pop('user_name', None)
    session.pop('user_email', None)

    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('main.index'))

# ========================================
# ACCOUNT ACTIVATION (For admin-created members)
# ========================================
@userAuth.route('/activate-account', methods=['GET', 'POST'])
def activate_account():
    # If already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('userRoutes.dashboard'))

    if request.method == 'POST':
        step = request.form.get('step', '1')

        # Step 1: Verify email + member_id
        if step == '1':
            email = request.form.get('email', '').strip().lower()
            member_id = request.form.get('member_id', '').strip().upper()

            # Validation
            if not email or not member_id:
                flash('Email and Member ID are required.', 'error')
                return render_template('activate_account.html', step=1)

            # Find member
            member = Member.query.filter_by(email=email, unique_code=member_id).first()

            if not member:
                flash('Invalid email or Member ID. Please check your details.', 'error')
                return render_template('activate_account.html', step=1)

            # Check if already activated
            if member.password_hash:
                flash('This account is already activated. Please login instead.', 'warning')
                return redirect(url_for('userAuth.user_login'))

            # Verification successful - show password form
            return render_template('activate_account.html',
                                 step=2,
                                 email=email,
                                 member_id=member_id,
                                 member_name=f"{member.first_name} {member.last_name}")

        # Step 2: Set password
        elif step == '2':
            email = request.form.get('email', '').strip().lower()
            member_id = request.form.get('member_id', '').strip().upper()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Validation
            if not password or len(password) < 6:
                flash('Password must be at least 6 characters.', 'error')
                return render_template('activate_account.html',
                                     step=2,
                                     email=email,
                                     member_id=member_id)

            if password != confirm_password:
                flash('Passwords do not match.', 'error')
                return render_template('activate_account.html',
                                     step=2,
                                     email=email,
                                     member_id=member_id)

            # Find member again
            member = Member.query.filter_by(email=email, unique_code=member_id).first()

            if not member:
                flash('Session expired. Please try again.', 'error')
                return redirect(url_for('userAuth.activate_account'))

            # Check if already activated (double-check)
            if member.password_hash:
                flash('This account is already activated. Please login instead.', 'warning')
                return redirect(url_for('userAuth.user_login'))

            # Set password
            member.set_password(password)

            # Create activation log
            try:
                log = MembershipLog(
                    member_id=member.member_id,
                    action_type='Account Activated',
                    remarks=f'User activated admin-created account'
                )
                db.session.add(log)
                db.session.commit()

                flash(f'Account activated successfully! You can now login with your email and password.', 'success')
                return redirect(url_for('userAuth.user_login'))

            except Exception as e:
                db.session.rollback()
                flash('Activation failed. Please try again.', 'error')
                print(f"Activation error: {e}")
                return redirect(url_for('userAuth.activate_account'))

    # GET request - show step 1 (email + member_id form)
    return render_template('activate_account.html', step=1)
