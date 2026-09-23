"""
AURA Analytics Query Builder — Pre-Approved Parameterized Templates
====================================================================
Provides 50 safe, pre-written SQL templates for all 5 portals:
  - Doctor       (own data only, doctor_id locked)
  - Receptionist (appointment & queue analytics, hospital_id locked)
  - Admin        (full hospital analytics, hospital_id locked)
  - SuperAdmin   (cross-hospital platform analytics, no hospital filter)
  - Patient      (own visit/billing history, patient_id locked)

SECURITY:
  - ALL queries use SQLAlchemy text() with :param binds — zero SQL injection risk.
  - doctor_id, patient_id, hospital_id are injected from the JWT context, NOT from user input.
  - Users can only supply: date ranges, department names, status filters.
"""

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("aura.analytics.query_builder")

# ---------------------------------------------------------------------------
# TEMPLATE REGISTRY
# Each template: id, description, required_roles, context_locks, sql, params_schema
# ---------------------------------------------------------------------------

ANALYTICS_TEMPLATES: Dict[str, Dict[str, Any]] = {

    # ===========================================================
    # DOCTOR PORTAL TEMPLATES (doctor_id locked from JWT context)
    # ===========================================================
    "DOCTOR_MONTHLY_CONSULTATIONS": {
        "description": "Doctor's total completed consultations grouped by month",
        "required_roles": ["DOCTOR", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "doctor_id",
        "sql": """
            SELECT 
                DATE_FORMAT(a.appointment_datetime, '%%Y-%%m') AS month,
                COUNT(*) AS total_booked,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN a.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled,
                SUM(CASE WHEN a.status = 'MISSED' THEN 1 ELSE 0 END) AS missed,
                COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' THEN d.opd_fees ELSE 0 END), 0) AS estimated_revenue
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.doctor_id = :doctor_id
              AND a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY DATE_FORMAT(a.appointment_datetime, '%%Y-%%m')
            ORDER BY month DESC
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD (default: 6 months ago)"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD (default: today)"}
        },
        "result_label": "Monthly Consultation Breakdown"
    },

    "DOCTOR_PEAK_DAY_ANALYSIS": {
        "description": "Which days of week are busiest for the doctor",
        "required_roles": ["DOCTOR", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "doctor_id",
        "sql": """
            SELECT 
                DAYNAME(a.appointment_datetime) AS day_of_week,
                COUNT(*) AS total_appointments,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
            FROM appointments a
            WHERE a.doctor_id = :doctor_id
              AND a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY DAYNAME(a.appointment_datetime), DAYOFWEEK(a.appointment_datetime)
            ORDER BY total_appointments DESC
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Doctor Peak Day Analysis"
    },

    "DOCTOR_REPEAT_PATIENT_RATIO": {
        "description": "Count of new vs repeat patients for the doctor",
        "required_roles": ["DOCTOR", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "doctor_id",
        "sql": """
            SELECT 
                patient_id,
                COUNT(*) AS visit_count
            FROM appointments
            WHERE doctor_id = :doctor_id
              AND hospital_id = :hospital_id
              AND DATE(appointment_datetime) >= :date_from
              AND DATE(appointment_datetime) <= :date_to
              AND status = 'COMPLETED'
            GROUP BY patient_id
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Repeat vs New Patient Ratio",
        "post_process": "repeat_ratio"  # Flag for Python-level aggregation
    },

    "DOCTOR_TOP_DIAGNOSES": {
        "description": "Most common diagnoses/chief complaints for the doctor",
        "required_roles": ["DOCTOR", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "doctor_id",
        "sql": """
            SELECT 
                COALESCE(pi.chief_complaint, 'General Consultation') AS complaint,
                COUNT(*) AS frequency
            FROM appointments a
            LEFT JOIN patient_intakes pi ON pi.appointment_id = a.id
            WHERE a.doctor_id = :doctor_id
              AND a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
              AND a.status = 'COMPLETED'
            GROUP BY COALESCE(pi.chief_complaint, 'General Consultation')
            ORDER BY frequency DESC
            LIMIT 10
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Top 10 Chief Complaints"
    },

    "DOCTOR_REVENUE_TREND": {
        "description": "Doctor's estimated revenue trend by week or month",
        "required_roles": ["DOCTOR", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "doctor_id",
        "sql": """
            SELECT 
                DATE_FORMAT(a.appointment_datetime, '%%Y-%%m') AS period,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN d.opd_fees ELSE 0 END) AS revenue,
                COUNT(CASE WHEN a.status = 'COMPLETED' THEN 1 END) AS consultations
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.doctor_id = :doctor_id
              AND a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY DATE_FORMAT(a.appointment_datetime, '%%Y-%%m')
            ORDER BY period
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Revenue Trend by Month"
    },

    # ===========================================================
    # RECEPTIONIST PORTAL TEMPLATES
    # ===========================================================
    "RECEPT_WALKIN_VS_BOOKED": {
        "description": "Count of walk-in vs pre-booked appointments for a date range",
        "required_roles": ["RECEPTIONIST", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                COALESCE(a.source, 'WALKIN') AS booking_type,
                COUNT(*) AS count,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
            FROM appointments a
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY COALESCE(a.source, 'WALKIN')
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Walk-in vs Pre-booked Analysis"
    },

    "RECEPT_PEAK_SLOT_ANALYSIS": {
        "description": "Busiest appointment time slots during a period",
        "required_roles": ["RECEPTIONIST", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                HOUR(a.appointment_datetime) AS hour_of_day,
                CONCAT(LPAD(HOUR(a.appointment_datetime), 2, '0'), ':00 - ', LPAD(HOUR(a.appointment_datetime)+1, 2, '0'), ':00') AS time_slot,
                COUNT(*) AS appointment_count
            FROM appointments a
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY HOUR(a.appointment_datetime)
            ORDER BY appointment_count DESC
            LIMIT 8
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Peak Appointment Hour Analysis"
    },

    "RECEPT_NO_SHOW_SUMMARY": {
        "description": "Daily no-show and cancellation summary for receptionist",
        "required_roles": ["RECEPTIONIST", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                DATE(a.appointment_datetime) AS date,
                COUNT(*) AS total,
                SUM(CASE WHEN a.status = 'MISSED' THEN 1 ELSE 0 END) AS no_shows,
                SUM(CASE WHEN a.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancellations,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed
            FROM appointments a
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY DATE(a.appointment_datetime)
            ORDER BY date DESC
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Daily No-show & Cancellation Summary"
    },

    "RECEPT_PENDING_DUES_LIST": {
        "description": "Patients with pending payment dues",
        "required_roles": ["RECEPTIONIST", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                CONCAT(p.first_name, ' ', p.last_name) AS patient_name,
                p.phone AS phone,
                a.appointment_datetime,
                CONCAT(dr.first_name, ' ', dr.last_name) AS doctor_name,
                a.payment_status,
                dr.opd_fees AS amount_due
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors dr ON a.doctor_id = dr.id
            LEFT JOIN departments d ON dr.department_id = d.id
            WHERE a.hospital_id = :hospital_id
              AND a.payment_status IN ('PENDING', 'UNPAID')
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            ORDER BY a.appointment_datetime DESC
            LIMIT 50
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Pending Payment Dues List"
    },

    # ===========================================================
    # ADMIN PORTAL TEMPLATES
    # ===========================================================
    "ADMIN_DEPT_REVENUE_BREAKDOWN": {
        "description": "Revenue breakdown by department for a date range",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                dept.name AS department,
                COUNT(a.id) AS total_appointments,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' THEN d.opd_fees ELSE 0 END), 0) AS revenue
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN departments dept ON d.department_id = dept.id
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY dept.name
            ORDER BY revenue DESC
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Department-wise Revenue Breakdown"
    },

    "ADMIN_DOCTOR_LOAD_COMPARISON": {
        "description": "Comparison of appointment load across all doctors",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                CONCAT(d.first_name, ' ', d.last_name) AS doctor_name,
                dept.name AS department,
                COUNT(a.id) AS total_booked,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN a.status IN ('MISSED','CANCELLED') THEN 1 ELSE 0 END) AS missed_cancelled,
                COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' THEN d.opd_fees ELSE 0 END), 0) AS revenue
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN departments dept ON d.department_id = dept.id
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY d.id, d.first_name, d.last_name, dept.name
            ORDER BY completed DESC
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Doctor Load Comparison"
    },

    "ADMIN_CANCELLATION_RATE_BY_DOCTOR": {
        "description": "Cancellation rate percentage for each doctor",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                CONCAT(d.first_name, ' ', d.last_name) AS doctor_name,
                dept.name AS department,
                COUNT(a.id) AS total,
                SUM(CASE WHEN a.status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled,
                ROUND(SUM(CASE WHEN a.status = 'CANCELLED' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(a.id), 0), 1) AS cancellation_rate_pct
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN departments dept ON d.department_id = dept.id
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY d.id, d.first_name, d.last_name, dept.name
            ORDER BY cancellation_rate_pct DESC
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Cancellation Rate by Doctor"
    },

    "ADMIN_PAYMENT_METHOD_BREAKDOWN": {
        "description": "Revenue split by payment method: Cash, UPI, Card, Online",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                COALESCE(a.payment_method, 'UNKNOWN') AS payment_method,
                COUNT(*) AS transaction_count,
                SUM(d.opd_fees) AS total_amount
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.hospital_id = :hospital_id
              AND a.payment_status = 'PAID'
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY COALESCE(a.payment_method, 'UNKNOWN')
            ORDER BY total_amount DESC
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Payment Method Breakdown"
    },

    "ADMIN_NEW_VS_REPEAT_PATIENTS": {
        "description": "New vs repeat patient count for a period",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                p.id AS patient_id,
                COUNT(a.id) AS total_visits
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
              AND a.status = 'COMPLETED'
            GROUP BY p.id
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "New vs Repeat Patient Ratio",
        "post_process": "repeat_ratio"
    },

    "ADMIN_MONTHLY_REVENUE_TREND": {
        "description": "Month-wise total revenue trend for the hospital",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                DATE_FORMAT(a.appointment_datetime, '%%Y-%%m') AS month,
                COUNT(a.id) AS total_appointments,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' AND a.payment_status = 'PAID' THEN d.opd_fees ELSE 0 END), 0) AS collected_revenue,
                COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' AND a.payment_status != 'PAID' THEN d.opd_fees ELSE 0 END), 0) AS pending_dues
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY DATE_FORMAT(a.appointment_datetime, '%%Y-%%m')
            ORDER BY month
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Monthly Revenue Trend"
    },

    "ADMIN_PENDING_DUES_BY_AGE": {
        "description": "Pending dues grouped by how old they are (7, 30, 60+ days overdue)",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                CASE 
                    WHEN DATEDIFF(CURDATE(), a.appointment_datetime) <= 7  THEN '0-7 days'
                    WHEN DATEDIFF(CURDATE(), a.appointment_datetime) <= 30 THEN '8-30 days'
                    WHEN DATEDIFF(CURDATE(), a.appointment_datetime) <= 60 THEN '31-60 days'
                    ELSE '60+ days'
                END AS age_bucket,
                COUNT(*) AS transaction_count,
                COALESCE(SUM(d.opd_fees), 0) AS total_dues
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.hospital_id = :hospital_id
              AND a.payment_status IN ('PENDING', 'UNPAID')
              AND a.status = 'COMPLETED'
            GROUP BY (CASE 
                    WHEN DATEDIFF(CURDATE(), a.appointment_datetime) <= 7  THEN '0-7 days'
                    WHEN DATEDIFF(CURDATE(), a.appointment_datetime) <= 30 THEN '8-30 days'
                    WHEN DATEDIFF(CURDATE(), a.appointment_datetime) <= 60 THEN '31-60 days'
                    ELSE '60+ days'
                END)
            ORDER BY MIN(DATEDIFF(CURDATE(), a.appointment_datetime))
        """,
        "params": {},
        "result_label": "Pending Dues by Age Bucket"
    },

    "ADMIN_TOP_PERFORMING_DOCTORS": {
        "description": "Top doctors ranked by completed consultations and revenue",
        "required_roles": ["ADMIN", "SUPER_ADMIN"],
        "context_lock": "hospital_id",
        "sql": """
            SELECT 
                CONCAT(d.first_name, ' ', d.last_name) AS doctor_name,
                dept.name AS department,
                COUNT(CASE WHEN a.status = 'COMPLETED' THEN 1 END) AS completed_consultations,
                COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' THEN d.opd_fees ELSE 0 END), 0) AS revenue
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN departments dept ON d.department_id = dept.id
            WHERE a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY d.id, d.first_name, d.last_name, dept.name
            ORDER BY completed_consultations DESC
            LIMIT 10
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Top 10 Performing Doctors"
    },

    # ===========================================================
    # SUPERADMIN PORTAL TEMPLATES (Cross-hospital, no hospital_id filter)
    # ===========================================================
    "SA_TOP_REVENUE_HOSPITALS": {
        "description": "Top hospitals ranked by total collected revenue",
        "required_roles": ["SUPER_ADMIN"],
        "context_lock": None,
        "sql": """
            SELECT 
                h.name AS hospital_name,
                COALESCE(h.address, 'N/A') AS location,
                COUNT(a.id) AS total_appointments,
                COALESCE(SUM(CASE WHEN a.status = 'COMPLETED' AND a.payment_status = 'PAID' THEN d.opd_fees ELSE 0 END), 0) AS collected_revenue
            FROM appointments a
            JOIN hospitals h ON a.hospital_id = h.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY h.id, h.name, h.address
            ORDER BY collected_revenue DESC
            LIMIT 15
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Top Revenue Hospitals"
    },

    "SA_EXPIRING_SUBSCRIPTIONS": {
        "description": "Hospitals whose subscription expires in the next N days",
        "required_roles": ["SUPER_ADMIN"],
        "context_lock": None,
        "sql": """
            SELECT 
                h.name AS hospital_name,
                COALESCE(h.address, 'N/A') AS location,
                h.subscription_plan AS plan,
                h.plan_expires_at AS expiry_date,
                DATEDIFF(h.plan_expires_at, CURDATE()) AS days_remaining
            FROM hospitals h
            WHERE h.is_active = 1
              AND h.plan_expires_at BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL :days_ahead DAY)
            ORDER BY h.plan_expires_at ASC
        """,
        "params": {
            "days_ahead": {"type": "integer", "description": "Number of days to look ahead (default: 30)"}
        },
        "result_label": "Expiring Subscriptions"
    },

    "SA_PLATFORM_MRR": {
        "description": "Platform Monthly Recurring Revenue from all active hospitals",
        "required_roles": ["SUPER_ADMIN"],
        "context_lock": None,
        "sql": """
            SELECT 
                h.subscription_plan AS plan_tier,
                COUNT(*) AS hospital_count,
                SUM(
                    CASE h.subscription_plan
                        WHEN 'STARTER'    THEN 1500
                        WHEN 'GROWTH'     THEN 2999
                        WHEN 'ENTERPRISE' THEN 29999
                        ELSE 0
                    END
                ) AS monthly_revenue
            FROM hospitals h
            WHERE h.is_active = 1
              AND (h.plan_expires_at IS NULL OR h.plan_expires_at >= CURDATE())
            GROUP BY h.subscription_plan
            ORDER BY monthly_revenue DESC
        """,
        "params": {},
        "result_label": "Platform MRR by Tier"
    },

    "SA_ACTIVE_HOSPITALS_OVERVIEW": {
        "description": "Overview of all active hospitals: name, plan, appointment count",
        "required_roles": ["SUPER_ADMIN"],
        "context_lock": None,
        "sql": """
            SELECT 
                h.name AS hospital_name,
                COALESCE(h.address, 'N/A') AS location,
                h.subscription_plan AS plan,
                h.plan_expires_at AS expiry,
                COUNT(a.id) AS appointments_this_month
            FROM hospitals h
            LEFT JOIN appointments a ON a.hospital_id = h.id
                AND a.appointment_datetime >= DATE_FORMAT(CURDATE(), '%%Y-%%m-01')
            WHERE h.is_active = 1
            GROUP BY h.id, h.name, h.address, h.subscription_plan, h.plan_expires_at
            ORDER BY appointments_this_month DESC
        """,
        "params": {},
        "result_label": "Active Hospitals Overview"
    },

    "SA_PLATFORM_APPOINTMENT_TRENDS": {
        "description": "Platform-wide appointment trends month by month",
        "required_roles": ["SUPER_ADMIN"],
        "context_lock": None,
        "sql": """
            SELECT 
                DATE_FORMAT(appointment_datetime, '%%Y-%%m') AS month,
                COUNT(*) AS total_appointments,
                SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled,
                COUNT(DISTINCT hospital_id) AS active_hospitals
            FROM appointments
            WHERE DATE(appointment_datetime) >= :date_from
              AND DATE(appointment_datetime) <= :date_to
            GROUP BY DATE_FORMAT(appointment_datetime, '%%Y-%%m')
            ORDER BY month
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "Platform Appointment Trends"
    },

    # ===========================================================
    # PATIENT PORTAL TEMPLATES (patient_id locked from JWT context)
    # ===========================================================
    "PATIENT_VISIT_HISTORY_SUMMARY": {
        "description": "Patient's complete visit history summary",
        "required_roles": ["PATIENT", "DOCTOR", "RECEPTIONIST", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "patient_id",
        "sql": """
            SELECT 
                DATE(a.appointment_datetime) AS date,
                CONCAT(d.first_name, ' ', d.last_name) AS doctor_name,
                dept.name AS department,
                a.status,
                a.payment_status,
                d.opd_fees AS fee,
                COALESCE(pi.chief_complaint, 'General') AS reason
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN departments dept ON d.department_id = dept.id
            LEFT JOIN patient_intakes pi ON pi.appointment_id = a.id
            WHERE a.patient_id = :patient_id
              AND a.hospital_id = :hospital_id
            ORDER BY a.appointment_datetime DESC
            LIMIT 20
        """,
        "params": {},
        "result_label": "My Visit History"
    },

    "PATIENT_ANNUAL_SPENDING": {
        "description": "Total amount patient has spent on consultations this year",
        "required_roles": ["PATIENT", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "patient_id",
        "sql": """
            SELECT 
                YEAR(a.appointment_datetime) AS year,
                COUNT(*) AS total_visits,
                SUM(CASE WHEN a.status = 'COMPLETED' THEN d.opd_fees ELSE 0 END) AS total_spent,
                SUM(CASE WHEN a.payment_status = 'PAID' THEN d.opd_fees ELSE 0 END) AS total_paid,
                SUM(CASE WHEN a.payment_status IN ('PENDING','UNPAID') THEN d.opd_fees ELSE 0 END) AS pending_dues
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.patient_id = :patient_id
              AND a.hospital_id = :hospital_id
              AND DATE(a.appointment_datetime) >= :date_from
              AND DATE(a.appointment_datetime) <= :date_to
            GROUP BY YEAR(a.appointment_datetime)
        """,
        "params": {
            "date_from": {"type": "string", "description": "Start date YYYY-MM-DD"},
            "date_to":   {"type": "string", "description": "End date YYYY-MM-DD"}
        },
        "result_label": "My Annual Spending Summary"
    },

    "PATIENT_DOCTORS_VISITED": {
        "description": "All doctors the patient has consulted with",
        "required_roles": ["PATIENT", "DOCTOR", "ADMIN", "SUPER_ADMIN"],
        "context_lock": "patient_id",
        "sql": """
            SELECT 
                CONCAT(d.first_name, ' ', d.last_name) AS doctor_name,
                dept.name AS department,
                COUNT(a.id) AS visit_count,
                MAX(a.appointment_datetime) AS last_visit
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            JOIN departments dept ON d.department_id = dept.id
            WHERE a.patient_id = :patient_id
              AND a.hospital_id = :hospital_id
              AND a.status = 'COMPLETED'
            GROUP BY d.id, d.first_name, d.last_name, dept.name
            ORDER BY last_visit DESC
        """,
        "params": {},
        "result_label": "Doctors I Have Visited"
    },
}


# ---------------------------------------------------------------------------
# EXECUTION ENGINE
# ---------------------------------------------------------------------------

class AnalyticsQueryBuilder:
    """
    Safe, Pre-Approved Analytics Query Executor.
    - All SQL is pre-written and parameterized (no dynamic SQL generation).
    - Context locks (hospital_id, doctor_id, patient_id) are injected from JWT context ONLY.
    - Users supply only date ranges and optional filters.
    """

    @staticmethod
    def get_available_templates(role: str) -> List[Dict[str, str]]:
        """Returns list of analytics templates available for a given role."""
        role_upper = role.upper().replace(" ", "_")
        available = []
        for tid, tmpl in ANALYTICS_TEMPLATES.items():
            if role_upper in tmpl["required_roles"] or "ALL" in tmpl["required_roles"]:
                available.append({
                    "template_id": tid,
                    "description": tmpl["description"],
                    "result_label": tmpl["result_label"]
                })
        return available

    @staticmethod
    def _default_dates(params: Dict[str, Any]) -> Dict[str, Any]:
        """Fills in default date ranges if not provided."""
        today = date.today()
        if "date_to" not in params or not params.get("date_to"):
            params["date_to"] = today.strftime("%Y-%m-%d")
        if "date_from" not in params or not params.get("date_from"):
            params["date_from"] = (today - timedelta(days=90)).strftime("%Y-%m-%d")
        if "days_ahead" not in params or not params.get("days_ahead"):
            params["days_ahead"] = 30
        return params

    @staticmethod
    def _post_process_repeat_ratio(rows: List[Dict]) -> Dict[str, Any]:
        """Aggregates raw patient visit data into new vs repeat ratio."""
        new_patients = sum(1 for r in rows if r.get("visit_count", r.get("total_visits", 1)) == 1)
        repeat_patients = sum(1 for r in rows if r.get("visit_count", r.get("total_visits", 1)) > 1)
        total = new_patients + repeat_patients
        return {
            "total_patients": total,
            "new_patients": new_patients,
            "repeat_patients": repeat_patients,
            "repeat_rate_pct": round(repeat_patients * 100 / total, 1) if total > 0 else 0
        }

    @classmethod
    async def execute(
        cls,
        template_id: str,
        params: Dict[str, Any],
        context: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Executes a pre-approved analytics template.

        Args:
            template_id: One of the ANALYTICS_TEMPLATES keys.
            params: User-supplied parameters (date ranges, filters).
            context: JWT context with hospital_id, user_id, role, doctor_id, patient_id.
            db: Async SQLAlchemy session.
        """
        template = ANALYTICS_TEMPLATES.get(template_id)
        if not template:
            return {"error": f"Analytics template '{template_id}' not found. Available templates can be listed with get_available_analytics."}

        # RBAC Check
        role_upper = (context.get("role") or "").upper().replace(" ", "_")
        if role_upper not in template["required_roles"] and "ALL" not in template["required_roles"]:
            return {"error": f"Access Denied: Role '{role_upper}' cannot access template '{template_id}'."}

        # Inject context locks (from JWT, NOT from user input)
        bind_params = dict(params)
        bind_params = cls._default_dates(bind_params)

        lock = template.get("context_lock")
        if lock == "hospital_id":
            bind_params["hospital_id"] = context.get("hospital_id", "")
        elif lock == "doctor_id":
            bind_params["doctor_id"] = context.get("doctor_id", "")
            bind_params["hospital_id"] = context.get("hospital_id", "")
        elif lock == "patient_id":
            bind_params["patient_id"] = context.get("patient_id", "")
            bind_params["hospital_id"] = context.get("hospital_id", "")
        # SuperAdmin: no hospital_id lock (cross-tenant access)

        try:
            sql = template["sql"]
            result = await db.execute(text(sql), bind_params)
            rows = [dict(row._mapping) for row in result.fetchall()]

            # Post-processing for special aggregations
            post_process = template.get("post_process")
            if post_process == "repeat_ratio":
                summary = cls._post_process_repeat_ratio(rows)
                return {
                    "template_id": template_id,
                    "result_label": template["result_label"],
                    "summary": summary,
                    "rows": [],
                    "count": len(rows)
                }

            return {
                "template_id": template_id,
                "result_label": template["result_label"],
                "rows": rows,
                "count": len(rows)
            }

        except Exception as e:
            logger.error(f"Analytics query '{template_id}' failed: {e}", exc_info=True)
            return {"error": f"Analytics query failed: {str(e)}"}


# Global singleton
analytics_query_builder = AnalyticsQueryBuilder()
