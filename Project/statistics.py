from flask import Blueprint, jsonify
from . import db
from .models import Member, MembershipLog
from datetime import datetime, timedelta
import pytz

statistics = Blueprint('statistics', __name__)

@statistics.route('/admin/members-statistics', methods=['GET'])
def get_members_statistics():
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    start_of_day = tz.localize(datetime(now.year, now.month, now.day))
    start_of_month = tz.localize(datetime(now.year, now.month, 1))

    members = Member.query.all()
    total_revenue = daily_revenue = monthly_revenue = 0
    total_members = len(members)
    active_members = 0

    member_list = []

    for m in members:
        price = float(m.price_paid or 0)
        created_at = m.date_registered

        # Make datetime timezone-aware if it's naive
        if created_at.tzinfo is None:
            created_at = tz.localize(created_at)

        total_revenue += price
        if created_at >= start_of_month:
            monthly_revenue += price
        if created_at >= start_of_day:
            daily_revenue += price

        if m.status.lower() == "active":
            active_members += 1

        member_list.append({
            "id": m.member_id,
            "unique_code": m.unique_code,
            "first_name": m.first_name,
            "last_name": m.last_name,
            "price_paid": m.price_paid,
            "member_type": m.member_type,
            "gym_plan": m.gym_plan,
            "status": m.status,
            "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return jsonify({
        "members": member_list,
        "stats": {
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "daily_revenue": daily_revenue,
            "total_members": total_members,
            "active_members": active_members
        }
    })

@statistics.route('/admin/membership-logs', methods=['GET'])
def get_membership_logs():
    tz = pytz.timezone('Asia/Manila')
    now = datetime.now(tz)
    one_week_ago = now - timedelta(days=7)

    logs = (
        db.session.query(MembershipLog, Member)
        .join(Member, MembershipLog.member_id == Member.member_id)
        .filter(MembershipLog.action_date >= one_week_ago)
        .order_by(MembershipLog.action_date.desc())
        .all()
    )

    result = []
    for log, member in logs:
        try:
            action_type = str(log.action_type)
        except LookupError:
            action_type = "Unknown"

        result.append({
            "log_id": log.log_id,
            "member_id": member.member_id,
            "member_name": f"{member.first_name} {member.last_name}",
            "action_type": action_type,
            "action_date": log.action_date.strftime("%Y-%m-%d %H:%M:%S"),
            "remarks": log.remarks or ""
        })

    return jsonify(result)

@statistics.route("/admin/statistics-summary", methods=["GET"])
def statistics_summary():
    tz = pytz.timezone("Asia/Manila")
    now = datetime.now(tz)

    labels = []
    students_data = []
    faculty_data = []
    outsiders_data = []

    # Collect last 6 months
    for i in range(5, -1, -1):  # 5 -> 0 months ago
        month = (now.month - i - 1) % 12 + 1
        year = now.year if now.month - i > 0 else now.year - 1
        labels.append(f"{year}-{month:02d}")

        # Count members per type for that month
        start = tz.localize(datetime(year, month, 1))
        if month == 12:
            end = tz.localize(datetime(year + 1, 1, 1))
        else:
            end = tz.localize(datetime(year, month + 1, 1))

        students_count = Member.query.filter(Member.date_registered >= start,
                                            Member.date_registered < end,
                                            Member.member_type == "Student").count()
        faculty_count = Member.query.filter(Member.date_registered >= start,
                                            Member.date_registered < end,
                                            Member.member_type == "Faculty").count()
        outsiders_count = Member.query.filter(Member.date_registered >= start,
                                            Member.date_registered < end,
                                            Member.member_type == "Outsider").count()

        students_data.append(students_count)
        faculty_data.append(faculty_count)
        outsiders_data.append(outsiders_count)

    # Summary cards
    total_members = Member.query.count()
    active_members = Member.query.filter_by(status="Active").count()
    most_active = "Students"  # Example, or compute based on activity logs

    return jsonify({
        "summary": {
            "total": total_members,
            "active": active_members,
            "most_active": most_active
        },
        "overview_chart": {
            "labels": labels,
            "students": students_data,
            "faculty": faculty_data,
            "outsiders": outsiders_data
        }
    })
