from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from . import db
from .models import Member, MembershipLog, GymPricing
from datetime import datetime
from functools import lru_cache
import pytz
import calendar
import time  # ✅ for time.time()
from sqlalchemy import and_, func  # ✅ for and_ and func


addMember = Blueprint('addMember', __name__)

# Cache (in-memory)
_cache_data = None
_cache_time = 0

# Automatically mark members as expired if their end_date has passed.
def auto_update_expired_members():
    tz = pytz.timezone("Asia/Manila")
    today = datetime.now(tz).date()

    expired_members = Member.query.filter(
        and_(
            Member.end_date < today,
            Member.status != "Expired"
        )
    ).all()

    count = 0
    for member in expired_members:
        # 🔥 Skip members manually set to Active (admin override)
        if member.status == "Active":
            continue

        member.status = "Expired"
        count += 1

        log = MembershipLog(
            member_id=member.member_id,
            action_type='Status Update',
            remarks=f"Automatically marked as expired (End date: {member.end_date})."
        )
        db.session.add(log)

    if count > 0:
        db.session.commit()

    return count



# Add Member
@addMember.route('/admin/add-member', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        try:
            # --- Collect form data ---
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            age = request.form.get('age')
            gender = request.form.get('gender')
            member_type = request.form.get('member_type')
            student_number = request.form.get('student_number') if member_type == 'Student' else None
            gym_plan = request.form.get('gym_plan')
            email = request.form.get('email')
            contact_number = request.form.get('contact_number')
            address = request.form.get('address')
            start_date = request.form.get('Start_date')
            end_date = request.form.get('End_date')

            # --- Validation ---
            required_fields = [first_name, last_name, member_type, gym_plan, start_date, end_date]
            if not all(required_fields):
                return jsonify({
                    "success": False,
                    "error": "Please fill in all required fields."
                }), 400

            # --- Convert dates ---
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

            # --- Create new member ---
            new_member = Member(
                first_name=first_name,
                last_name=last_name,
                age=age if age else None,
                gender=gender if gender else None,
                member_type=member_type,
                student_number=student_number,
                gym_plan=gym_plan,
                email=email,
                contact_number=contact_number,
                address=address,
                start_date=start_date,
                end_date=end_date,
                status='Active'
            )

            # --- Fetch price based on type/plan ---
            current_price = GymPricing.query.filter_by(
                member_type=member_type,
                plan_type=gym_plan
            ).first()

            new_member.price_paid = current_price.price if current_price else 0.0

            db.session.add(new_member)
            db.session.commit()

            # --- Log registration ---
            new_log = MembershipLog(
                member_id=new_member.member_id,
                action_type='Registered',
                remarks=f"Member {first_name} {last_name} registered successfully."
            )
            db.session.add(new_log)
            db.session.commit()

            # --- JSON Response (for AJAX/fetch) ---
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    "success": True,
                    "message": f"New member registered successfully! Paid ₱{new_member.price_paid:.2f}",
                    "member": {
                        "id": new_member.member_id,
                        "first_name": new_member.first_name,
                        "last_name": new_member.last_name,
                        "price_paid": new_member.price_paid
                    }
                }), 200

            # --- Normal form submission ---
            flash(f"New member {new_member.first_name} {new_member.last_name} added successfully!", "success")
            return redirect(url_for('addMember.add_member'))

        except Exception as e:
            db.session.rollback()
            return jsonify({
                "success": False,
                "error": f"Error registering member: {str(e)}"
            }), 500

    # ===========================
    # 📋 GET Request - Render Members Page
    # ===========================
    if request.method == 'GET':
        members = Member.query.all()
        auto_update_expired_members()  # check and update expired members
        return render_template('members.html', members=members)

# View specific member details (AJAX endpoint)
@addMember.route('/admin/member/<int:member_id>', methods=['GET'])
def view_member(member_id):
    member = Member.query.get_or_404(member_id)
    
    member_data = {
        "member_id": member.member_id,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "age": member.age,
        "gender": member.gender,
        "member_type": member.member_type,
        "gym_plan": member.gym_plan,
        "email": member.email,
        "contact_number": member.contact_number,
        "address": member.address,
        "start_date": member.start_date.strftime("%Y-%m-%d"),
        "end_date": member.end_date.strftime("%Y-%m-%d"),
        "status": member.status
    }
    return jsonify(member_data)


# Update Member
@addMember.route('/admin/member/<int:member_id>/edit', methods=['POST'])
def edit_member(member_id):
    member = Member.query.get_or_404(member_id)

    try:
        data = request.get_json()   

        # Track original type
        old_type = member.member_type
        new_type = data.get('member_type', member.member_type)

        # Update general info
        member.first_name = data.get('first_name', member.first_name)
        member.last_name = data.get('last_name', member.last_name)
        member.age = data.get('age', member.age)
        member.gender = data.get('gender', member.gender)
        member.gym_plan = data.get('gym_plan', member.gym_plan)
        member.email = data.get('email', member.email)
        member.contact_number = data.get('contact_number', member.contact_number)
        member.address = data.get('address', member.address)
        member.start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d').date()
        member.end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d').date()
        member.status = data.get('status', member.status)

        # Handle type change
        if new_type != old_type:
            member.update_member_type(new_type)

        # Auto-update status based on new end date
        from pytz import timezone
        tz = timezone("Asia/Manila")
        current_date = datetime.now(tz).date()

        member.status = data.get('status', member.status)

        db.session.commit()

        # Log edit
        log = MembershipLog(
            member_id=member.member_id,
            action_type='Updated',
            remarks=f"Updated information for {member.first_name} {member.last_name}."
        )
        db.session.add(log)
        db.session.commit()

        flash(f"Member {member.first_name} {member.last_name} was updated successfully!", "success")

        # Return success response
        return jsonify({
            "success": True,
            "message": f"{member.first_name} {member.last_name} updated successfully!",
            "member": {
                "id": member.member_id,
                "first_name": member.first_name,
                "last_name": member.last_name,
                "plan": member.gym_plan,
                "status": member.status
            }
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# Delete Member
@addMember.route('/admin/member/<int:member_id>/delete', methods=['DELETE'])
def delete_member(member_id):
    # Get member ID from database
    member = Member.query.get_or_404(member_id)
    try:
        db.session.delete(member)
        db.session.commit()

        # log membership
        log = MembershipLog(
            member_id=member_id,
            action_type='Updated',
            remarks=f"Deleted member record for {member.first_name} {member.last_name}."
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({"success": True, "message": "Member deleted successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@addMember.route('/admin/dashboard-summary', methods=['GET'])
def dashboard_summary():
    global _cache_data, _cache_time
    now_time = time.time()
    auto_update_expired_members()
    # Serve from cache if < 10s old
    if _cache_data and now_time - _cache_time < 10:
        return jsonify(_cache_data)

    try:
        tz = pytz.timezone("Asia/Manila")
        now = datetime.now(tz)

        # === SUMMARY AGGREGATION ===
        status_counts = (
            db.session.query(Member.status, func.count(Member.member_id))
            .group_by(Member.status)
            .all()
        )
        type_counts_active = (
            db.session.query(Member.member_type, func.count(Member.member_id))
            .filter(Member.status == "Active")
            .group_by(Member.member_type)
            .all()
        )

        # Convert to dicts
        status_dict = dict(status_counts)
        type_dict = dict(type_counts_active)

        total_members = sum(status_dict.values())
        active_members = status_dict.get("Active", 0)

        student_active = type_dict.get("Student", 0)
        faculty_active = type_dict.get("Faculty", 0)
        outsider_active = type_dict.get("Outsider", 0)

        type_counts = {
            "Student": student_active,
            "Faculty": faculty_active,
            "Outsider": outsider_active
        }
        most_active_type = max(type_counts, key=type_counts.get) if type_counts else "N/A"

        # === CHART DATA: Active Members by Type (past 6 months) ===
        monthly_labels, student_counts, faculty_counts, outsider_counts = [], [], [], []

        for i in range(5, -1, -1):
            month = now.month - i
            year = now.year
            if month <= 0:
                month += 12
                year -= 1

            label = datetime(year, month, 1).strftime("%b")
            start = tz.localize(datetime(year, month, 1))
            end_day = calendar.monthrange(year, month)[1]
            end = tz.localize(datetime(year, month, end_day, 23, 59, 59))

            base_filter = and_(Member.status == "Active", Member.start_date <= end, Member.end_date >= start)

            # Aggregate by member_type in one go
            counts = (
                db.session.query(Member.member_type, func.count(Member.member_id))
                .filter(base_filter)
                .group_by(Member.member_type)
                .all()
            )
            count_map = dict(counts)

            monthly_labels.append(label)
            student_counts.append(count_map.get("Student", 0))
            faculty_counts.append(count_map.get("Faculty", 0))
            outsider_counts.append(count_map.get("Outsider", 0))

        result = {
            "summary": {
                "total": total_members,
                "active": active_members,
                "most_active": most_active_type
            },
            "overview_chart": {
                "labels": monthly_labels,
                "students": student_counts,
                "faculty": faculty_counts,
                "outsiders": outsider_counts
            },
            "status_chart": {
                "labels": ["Student", "Faculty", "Outsider"],
                "values": [student_active, faculty_active, outsider_active]
            },
            "status_overview": {
                "labels": ["Active", "Inactive", "Expired"],
                "values": [
                    status_dict.get("Active", 0),
                    status_dict.get("Inactive", 0),
                    status_dict.get("Expired", 0)
                ]
            }
        }

        # Store to cache
        _cache_data = result
        _cache_time = now_time

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Get all members as JSON (for members.js use)
@addMember.route('/admin/members-json', methods=['GET'])
def get_members_json():
    members = Member.query.all()
    return jsonify({
        "members": [
            {
                "member_id": m.member_id,
                "unique_code": m.unique_code,
                "first_name": m.first_name,
                "last_name": m.last_name,
                "member_type": m.member_type,
                "gym_plan": m.gym_plan,
                "status": m.status,
                "email": m.email,
                "contact_number": m.contact_number,
                "start_date": m.start_date.strftime("%Y-%m-%d"),
                "end_date": m.end_date.strftime("%Y-%m-%d")
            }
            for m in members
        ]
    })