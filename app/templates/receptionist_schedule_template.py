"""
Receptionist Today Schedule HTML Template Generator
Decoupled from REST router to maintain pure API handlers.
"""
from datetime import datetime, date, time, timedelta

def render_receptionist_schedule_html(
    target_date,
    day_display,
    day_name,
    prev_date,
    next_date,
    total,
    confirmed,
    pending,
    is_today,
    now_str,
    hosp_name,
    hospital_id,
    doctors_info,
    by_doctor
) -> str:
    dept_icons = {
        "Orthopedics": "🦴", "Cardiology": "❤️", "Ophthalmology": "👁️",
        "Heart": "❤️", "Eye": "👁️", "Haddi": "🦴",
    }

    doctor_sections = ""
    if not by_doctor:
        doctor_sections = """
        <div class="empty-card">
            <div class="empty-icon">📅</div>
            <h3>इस दिन कोई अपॉइंटमेंट नहीं है</h3>
            <p>अभी तक कोई बुकिंग नहीं आई है। जैसे ही AI Receptionist call लेगी, यहाँ दिखेगी।</p>
        </div>"""
    else:
        for (doc_name, dept_name), appts in by_doctor.items():
            icon = next((v for k, v in dept_icons.items() if k.lower() in dept_name.lower()), "👨‍⚕️")
            rows = ""
            for i, a in enumerate(appts, 1):
                appt_id = a['appointment_id']
                status = a['status']
                badge_map = {
                    'SCHEDULED': '<span class="badge confirmed">✅ Confirmed</span>',
                    'PENDING_PAYMENT': '<span class="badge pending-pay">⏳ Payment Pending</span>',
                    'COMPLETED': '<span class="badge completed">🎉 Completed</span>',
                    'CANCELLED': '<span class="badge cancelled">❌ Cancelled</span>',
                    'MISSED': '<span class="badge missed">🚫 Missed</span>',
                    'RESCHEDULED': '<span class="badge rescheduled">📅 Rescheduled</span>',
                }
                badge = badge_map.get(status, f'<span class="badge">{status}</span>')

                action_btns = ""
                if status in ["SCHEDULED", "PENDING_PAYMENT", "RESCHEDULED"]:
                    reschedule_btn = f"""<button class="act-btn blue" onclick="openReschedule('{appt_id}', '{a["doctor_id"]}', '{status}')">📅 Reschedule</button>""" if status != "PENDING_PAYMENT" else ""
                    
                    action_btns = f"""
                    <div class="action-btns" id="actions-{appt_id}">
                        <button class="act-btn green" onclick="updateStatus('{appt_id}', 'COMPLETED', '{status}')">✅ Completed</button>
                        <button class="act-btn red" onclick="updateStatus('{appt_id}', 'CANCELLED', '{status}')">❌ Cancel</button>
                        <button class="act-btn orange" onclick="updateStatus('{appt_id}', 'MISSED', '{status}')">🚫 Missed</button>
                        {reschedule_btn}
                    </div>"""

                intake_panel = ""
                if a.get('intake_html'):
                    intake_panel = f"""<div class="intake-panel"><span class="intake-label">🩺 AI Intake:</span> {a['intake_html']}</div>"""

                rows += f"""
                <tr class="appt-row" id="row-{appt_id}">
                    <td class="td-sno">{i}</td>
                    <td class="td-time">
                        <span class="time-pill">{a["time"]}</span>
                    </td>
                    <td class="td-patient">
                        <div class="patient-name">{a["patient_name"]}</div>
                        {intake_panel}
                    </td>
                    <td class="td-phone">
                        <a href="tel:{a["patient_phone"]}" class="phone-link">📞 {a["patient_phone"]}</a>
                    </td>
                    <td class="td-reason">{a["reason"]}</td>
                    <td class="td-status">
                        <div id="badge-{appt_id}">{badge}</div>
                        {action_btns}
                    </td>
                </tr>"""
            doctor_sections += f"""
            <div class="doctor-card">
                <div class="doctor-header">
                    <div class="doctor-left">
                        <div class="doc-icon">{icon}</div>
                        <div class="doc-details">
                            <div class="doc-name">{doc_name}</div>
                            <div class="doc-dept">{dept_name}</div>
                        </div>
                    </div>
                    <div class="doc-right">
                        <div class="doc-count">{len(appts)}</div>
                        <div class="doc-count-label">अपॉइंटमेंट</div>
                    </div>
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>⏰ समय</th>
                                <th>👤 मरीज़ का नाम</th>
                                <th>📞 मोबाइल</th>
                                <th>🩺 समस्या</th>
                                <th>स्थिति / कार्रवाई</th>
                            </tr>
                        </thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>"""

    sidebar_html = ""
    for d in doctors_info:
        badge_class = "slots-badge" if d["free_slots_count"] > 0 else "slots-badge empty"
        badge_text = f"{d['free_slots_count']} slots free" if d["free_slots_count"] > 0 else "Full / Closed"
        sidebar_html += f"""
        <div class="sidebar-doc-item">
            <div class="sidebar-doc-name">{d["name"]}</div>
            <div class="sidebar-doc-dept">{d["dept"]}</div>
            <div class="sidebar-doc-detail">
                <span>⏰ Timing:</span>
                <span>{d["timings"].replace("Timing:", "").strip()}</span>
            </div>
            <div class="sidebar-doc-detail">
                <span>💰 OPD Fees:</span>
                <span>{d["fees"]}</span>
            </div>
            <div class="sidebar-doc-detail" style="margin-top: 8px;">
                <span>📅 Slots status:</span>
                <span class="{badge_class}">{badge_text}</span>
            </div>
        </div>"""

    today_flag = '<span class="today-badge">आज</span>' if is_today else ""

    html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{hosp_name} — रिसेप्शनिस्ट डैशबोर्ड</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: #1a4fa0;
            --primary-dark: #0f3276;
            --primary-light: #dbeafe;
            --accent: #0ea5e9;
            --green: #16a34a;
            --green-bg: #dcfce7;
            --yellow: #b45309;
            --yellow-bg: #fef9c3;
            --bg: #f0f5fc;
            --card-bg: #ffffff;
            --text: #0f172a;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --shadow: 0 4px 20px rgba(26,79,160,0.10);
            --radius: 16px;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }}
        .header {{
            background: linear-gradient(135deg, #0f3276 0%, #1a4fa0 50%, #1e6cc4 100%);
            padding: 0;
            box-shadow: 0 4px 24px rgba(15,50,118,0.35);
        }}
        .header-inner {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 18px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .header-brand {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .header-logo {{
            width: 52px;
            height: 52px;
            background: rgba(255,255,255,0.15);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 26px;
            border: 1px solid rgba(255,255,255,0.25);
        }}
        .header-title {{ color: white; }}
        .header-title h1 {{ font-size: 20px; font-weight: 800; letter-spacing: -0.3px; }}
        .header-title p {{ font-size: 12px; color: rgba(255,255,255,0.75); margin-top: 2px; }}
        .header-right {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .live-clock {{
            background: rgba(255,255,255,0.12);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            padding: 8px 16px;
            color: white;
            font-size: 15px;
            font-weight: 600;
            font-variant-numeric: tabular-nums;
            min-width: 100px;
            text-align: center;
        }}
        .refresh-btn {{
            background: rgba(255,255,255,0.15);
            border: 1px solid rgba(255,255,255,0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: background 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .refresh-btn:hover {{ background: rgba(255,255,255,0.28); }}
        .date-bar {{
            background: white;
            border-bottom: 1px solid var(--border);
        }}
        .date-bar-inner {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 14px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .date-info {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .date-text {{
            font-size: 17px;
            font-weight: 700;
            color: var(--primary-dark);
        }}
        .day-text {{
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }}
        .today-badge {{
            background: var(--primary);
            color: white;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
        }}
        .date-nav {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .date-nav a {{
            padding: 7px 14px;
            border: 1.5px solid var(--border);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-muted);
            font-size: 13px;
            font-weight: 600;
            transition: all 0.15s;
        }}
        .date-nav a:hover {{ background: var(--primary-light); border-color: var(--accent); color: var(--primary); }}
        .date-nav a.today-btn {{ background: var(--primary); color: white; border-color: var(--primary); }}
        .date-nav a.today-btn:hover {{ background: var(--primary-dark); }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 28px;
        }}
        .dashboard-layout {{
            display: grid;
            grid-template-columns: 2.2fr 1fr;
            gap: 24px;
            align-items: start;
        }}
        @media (max-width: 950px) {{
            .dashboard-layout {{
                grid-template-columns: 1fr;
            }}
        }}
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: white;
            border-radius: var(--radius);
            padding: 20px 24px;
            box-shadow: var(--shadow);
            display: flex;
            align-items: center;
            gap: 16px;
        }}
        .stat-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }}
        .stat-icon.blue {{ background: var(--primary-light); }}
        .stat-icon.green {{ background: var(--green-bg); }}
        .stat-icon.yellow {{ background: var(--yellow-bg); }}
        .stat-value {{ font-size: 28px; font-weight: 800; color: var(--text); line-height: 1; }}
        .stat-label {{ font-size: 12px; color: var(--text-muted); font-weight: 500; margin-top: 4px; }}
        .doctor-card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            margin-bottom: 20px;
            box-shadow: var(--shadow);
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .doctor-header {{
            padding: 18px 24px;
            background: linear-gradient(135deg, #eff6ff 0%, #e0f2fe 100%);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #bfdbfe;
        }}
        .doctor-left {{
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .doc-icon {{
            width: 44px;
            height: 44px;
            background: white;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .doc-name {{ font-size: 17px; font-weight: 700; color: var(--primary-dark); }}
        .doc-dept {{
            display: inline-block;
            margin-top: 4px;
            background: var(--primary);
            color: white;
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
        }}
        .doc-right {{ text-align: center; }}
        .doc-count {{ font-size: 28px; font-weight: 800; color: var(--primary); }}
        .doc-count-label {{ font-size: 11px; color: var(--text-muted); font-weight: 500; }}
        .sidebar-card {{
            background: white;
            border-radius: var(--radius);
            padding: 24px;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            position: sticky;
            top: 24px;
        }}
        .sidebar-title {{
            font-size: 16px;
            font-weight: 800;
            color: var(--primary-dark);
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            gap: 8px;
            border-bottom: 2px solid var(--primary-light);
            padding-bottom: 10px;
        }}
        .sidebar-doc-item {{
            padding: 16px 0;
            border-bottom: 1px dashed var(--border);
        }}
        .sidebar-doc-item:last-child {{
            border-bottom: none;
            padding-bottom: 0;
        }}
        .sidebar-doc-item:first-child {{
            padding-top: 0;
        }}
        .sidebar-doc-name {{
            font-size: 15px;
            font-weight: 700;
            color: var(--text);
        }}
        .sidebar-doc-dept {{
            font-size: 10px;
            font-weight: 700;
            background: var(--primary-light);
            color: var(--primary-dark);
            padding: 2px 8px;
            border-radius: 12px;
            display: inline-block;
            margin-top: 4px;
            text-transform: uppercase;
        }}
        .sidebar-doc-detail {{
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 8px;
            display: flex;
            justify-content: space-between;
            font-weight: 500;
        }}
        .slots-badge {{
            background: var(--green-bg);
            color: var(--green);
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 11px;
        }}
        .slots-badge.empty {{
            background: #fee2e2;
            color: #ef4444;
        }}
        .table-wrap {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; }}
        thead tr {{ background: #f8fafc; }}
        th {{
            padding: 11px 16px;
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            border-bottom: 1.5px solid var(--border);
            white-space: nowrap;
        }}
        td {{
            padding: 13px 16px;
            border-bottom: 1px solid #f1f5f9;
            font-size: 14px;
            vertical-align: middle;
        }}
        .appt-row:last-child td {{ border-bottom: none; }}
        .appt-row:hover {{ background: #f8fafc; }}
        .td-sno {{ color: #cbd5e1; font-weight: 700; font-size: 13px; width: 36px; }}
        .time-pill {{
            background: var(--primary-light);
            color: var(--primary-dark);
            padding: 5px 12px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 13px;
            white-space: nowrap;
            display: inline-block;
        }}
        .patient-name {{ font-weight: 600; color: var(--text); font-size: 14px; }}
        .phone-link {{ color: var(--text-muted); text-decoration: none; font-size: 13px; white-space: nowrap; }}
        .phone-link:hover {{ color: var(--primary); }}
        .td-reason {{ color: var(--text-muted); font-size: 13px; max-width: 180px; }}
        .badge {{
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            display: inline-block;
        }}
        .badge.confirmed {{ background: var(--green-bg); color: var(--green); }}
        .badge.pending-pay {{ background: var(--yellow-bg); color: var(--yellow); }}
        .empty-card {{
            background: white;
            border-radius: var(--radius);
            padding: 60px 20px;
            text-align: center;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
        }}
        .empty-icon {{ font-size: 52px; margin-bottom: 16px; }}
        .empty-card h3 {{ font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 8px; }}
        .empty-card p {{ font-size: 14px; color: var(--text-muted); max-width: 360px; margin: 0 auto; }}
        .footer {{
            text-align: center;
            color: #94a3b8;
            font-size: 12px;
            padding: 20px;
        }}
        @media (max-width: 700px) {{
            .header-inner, .date-bar-inner, .container {{ padding: 14px 16px; }}
            .stats-row {{ grid-template-columns: 1fr; }}
            th, td {{ padding: 10px 12px; }}
            .header-title h1 {{ font-size: 16px; }}
            .date-text {{ font-size: 14px; }}
        }}
        @media (max-width: 480px) {{
            .stats-row {{ grid-template-columns: 1fr 1fr; }}
            .stat-card:first-child {{ grid-column: span 2; }}
        }}
        .action-btns {{
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            margin-top: 8px;
        }}
        .act-btn {{
            padding: 4px 9px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: all 0.15s;
            white-space: nowrap;
        }}
        .act-btn.green {{ background: #dcfce7; color: #15803d; }}
        .act-btn.green:hover {{ background: #bbf7d0; }}
        .act-btn.red {{ background: #fee2e2; color: #b91c1c; }}
        .act-btn.red:hover {{ background: #fecaca; }}
        .act-btn.orange {{ background: #fff7ed; color: #c2410c; }}
        .act-btn.orange:hover {{ background: #fed7aa; }}
        .act-btn.blue {{ background: #dbeafe; color: #1d4ed8; }}
        .act-btn.blue:hover {{ background: #bfdbfe; }}
        .badge.completed {{ background: #dcfce7; color: #15803d; }}
        .badge.cancelled {{ background: #fee2e2; color: #b91c1c; }}
        .badge.missed {{ background: #fef3c7; color: #92400e; }}
        .badge.rescheduled {{ background: #ede9fe; color: #6d28d9; }}
        .intake-panel {{
            margin-top: 6px;
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 7px;
            padding: 6px 10px;
            font-size: 11.5px;
            color: #0369a1;
            line-height: 1.6;
        }}
        .intake-label {{
            font-weight: 700;
            display: block;
            margin-bottom: 2px;
        }}
        .modal-overlay {{
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(15,50,118,0.45);
            z-index: 9000;
            align-items: center;
            justify-content: center;
        }}
        .modal-overlay.open {{ display: flex; }}
        .modal-box {{
            background: white;
            border-radius: 18px;
            padding: 32px;
            max-width: 460px;
            width: 95%;
            box-shadow: 0 20px 60px rgba(15,50,118,0.25);
        }}
        .modal-title {{ font-size: 18px; font-weight: 800; color: var(--primary-dark); margin-bottom: 20px; }}
        .modal-label {{ font-size: 13px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px; }}
        .modal-input {{
            width: 100%;
            padding: 10px 14px;
            border: 1.5px solid var(--border);
            border-radius: 9px;
            font-size: 14px;
            margin-bottom: 16px;
            font-family: inherit;
        }}
        .modal-input:focus {{ outline: none; border-color: var(--primary); }}
        .modal-actions {{ display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }}
        .modal-btn {{
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 700;
            border: none;
            cursor: pointer;
            transition: background 0.15s;
        }}
        .modal-btn.confirm {{ background: var(--primary); color: white; }}
        .modal-btn.confirm:hover {{ background: var(--primary-dark); }}
        .modal-btn.cancel {{ background: #f1f5f9; color: var(--text-muted); }}
        .modal-btn.cancel:hover {{ background: #e2e8f0; }}
    </style>
</head>
<body>

    <div class="header">
        <div class="header-inner">
            <div class="header-brand">
                <div class="header-logo">🏥</div>
                <div class="header-title">
                    <h1>{hosp_name}</h1>
                    <p>रिसेप्शनिस्ट डैशबोर्ड — AI Voice Booking System</p>
                </div>
            </div>
            <div class="header-right">
                <div class="live-clock" id="clock">{now_str}</div>
                <a class="refresh-btn" href="/receptionist/schedule?hospital_id={hospital_id}">
                    🔄 Refresh
                </a>
            </div>
        </div>
    </div>

    <div class="date-bar">
        <div class="date-bar-inner">
            <div class="date-info">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="header-logo" style="width: 40px; height: 40px; font-size: 20px; background: var(--primary-light); color: var(--primary); cursor: pointer; border: 1.5px solid var(--border); display: flex; align-items: center; justify-content: center; border-radius: 10px;" onclick="document.getElementById('date-select').showPicker()">📅</div>
                    <div>
                        <div class="date-text" style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--primary-dark); font-weight: 700; font-size: 17px;" onclick="document.getElementById('date-select').showPicker()">
                            {day_display} {today_flag}
                            <span style="font-size: 11px; color: var(--accent); vertical-align: middle;">▼</span>
                        </div>
                        <div class="day-text">{day_name}</div>
                    </div>
                    <input type="date" id="date-select" value="{target_date.isoformat()}" 
                           style="opacity: 0; width: 0; height: 0; position: absolute;"
                           onchange="window.location.href='/receptionist/schedule?hospital_id={hospital_id}&date_str=' + this.value">
                </div>
            </div>
            <div class="date-nav">
                <a href="/receptionist/schedule?date_str={prev_date}&hospital_id={hospital_id}">◀ पिछला</a>
                <a href="/receptionist/schedule?hospital_id={hospital_id}" class="today-btn">आज</a>
                <a href="/receptionist/schedule?date_str={next_date}&hospital_id={hospital_id}">अगला ▶</a>
            </div>
        </div>
    </div>

    <div class="container">

        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-icon blue">📋</div>
                <div>
                    <div class="stat-value">{total}</div>
                    <div class="stat-label">कुल अपॉइंटमेंट</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon green">✅</div>
                <div>
                    <div class="stat-value">{confirmed}</div>
                    <div class="stat-label">Confirmed</div>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-icon yellow">⏳</div>
                <div>
                    <div class="stat-value">{pending}</div>
                    <div class="stat-label">Payment Pending</div>
                </div>
            </div>
        </div>

        <div class="dashboard-layout">
            <div class="main-content">
                {doctor_sections}
            </div>

            <div class="sidebar-content">
                <div class="sidebar-card">
                    <div class="sidebar-title">
                        <span>👨‍⚕️</span> डॉक्टर, समय एवं फीस सूची
                    </div>
                    <div class="sidebar-list">
                        {sidebar_html}
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            अंतिम अपडेट: {datetime.now().strftime("%d %b %Y, %I:%M:%S %p")}
        </div>
    </div>

    <div class="modal-overlay" id="rescheduleModal">
        <div class="modal-box">
            <div class="modal-title">📅 Appointment Reschedule करें</div>
            <input type="hidden" id="modal-appt-id">
            <input type="hidden" id="modal-doctor-id">
            <label class="modal-label">नई Date और Time:</label>
            <input type="datetime-local" class="modal-input" id="modal-new-datetime" onchange="fetchBusySlots()">
            
            <div id="busy-slots-container" style="display:none; margin-bottom: 16px;">
                <label class="modal-label" style="color: #b91c1c; display: flex; align-items: center; gap: 4px;">
                    🚫 व्यस्त स्लॉट्स (Already Booked Times):
                </label>
                <div id="busy-slots-list" style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px;"></div>
            </div>

            <label class="modal-label">मरीज़ के लिए पहुँचने की Cutoff Note (optional):</label>
            <input type="text" class="modal-input" id="modal-cutoff" placeholder="जैसे: कृपया 10 बजे तक पहुँचें">
            <div class="modal-actions">
                <button class="modal-btn cancel" onclick="closeReschedule()">रद्द करें</button>
                <button class="modal-btn confirm" onclick="confirmReschedule()">📅 Reschedule करें</button>
            </div>
        </div>
    </div>

    <script>
        function updateClock() {{
            const now = new Date();
            const h = String(now.getHours() % 12 || 12).padStart(2, '0');
            const m = String(now.getMinutes()).padStart(2, '0');
            const s = String(now.getSeconds()).padStart(2, '0');
            const ampm = now.getHours() >= 12 ? 'PM' : 'AM';
            document.getElementById('clock').textContent = h + ':' + m + ':' + s + ' ' + ampm;
        }}
        setInterval(updateClock, 1000);
        updateClock();

        async function updateStatus(apptId, newStatus, currentStatus) {{
            const label = {{COMPLETED: 'Completed ✅', CANCELLED: 'Cancelled ❌', MISSED: 'Missed 🚫'}}[newStatus] || newStatus;
            
            let cancelReason = null;
            if (newStatus === 'CANCELLED' && currentStatus === 'SCHEDULED') {{
                cancelReason = prompt("इस Paid Appointment को निरस्त करने का कारण (Reason) दर्ज करें (यह मरीज़ को WhatsApp रिफंड सूचना के साथ भेजा जाएगा):");
                if (cancelReason === null) return;
                if (!cancelReason.trim()) cancelReason = "अस्पताल के अनुरोध पर";
            }}

            if (!confirm(`क्या आप इस appointment को "${{label}}" mark करना चाहते हैं?`)) return;

            const formData = new FormData();
            formData.append('new_status', newStatus);
            if (cancelReason) {{
                formData.append('cancellation_reason', cancelReason);
            }}

            try {{
                const res = await fetch(`/appointments/${{apptId}}/status`, {{
                    method: 'POST',
                    body: formData
                }});
                const data = await res.json();
                if (data.success) {{
                    const badgeMap = {{
                        COMPLETED: '<span class="badge completed">🎉 Completed</span>',
                        CANCELLED: '<span class="badge cancelled">❌ Cancelled</span>',
                        MISSED: '<span class="badge missed">🚫 Missed</span>',
                    }};
                    document.getElementById(`badge-${{apptId}}`).innerHTML = badgeMap[newStatus] || newStatus;
                    const actionsDiv = document.getElementById(`actions-${{apptId}}`);
                    if (actionsDiv) actionsDiv.remove();
                    if (newStatus === 'CANCELLED' && currentStatus === 'SCHEDULED') {{
                        alert('✅ Appointment निरस्त कर दी गई है और मरीज़ को रिफंड की सूचना WhatsApp कर दी गई है।');
                    }}
                }} else {{
                    alert('कुछ गड़बड़ हो गई। दोबारा कोशिश करें।');
                }}
            }} catch (e) {{
                alert('Network error. Please try again.');
            }}
        }}

        function openReschedule(apptId, doctorId, currentStatus) {{
            if (currentStatus === 'PENDING_PAYMENT') {{
                alert('❌ भुगतान अपूर्ण है (Payment Pending)। रीशेड्यूल केवल भुगतान पूरा होने के बाद ही संभव है।');
                return;
            }}

            document.getElementById('modal-appt-id').value = apptId;
            document.getElementById('modal-doctor-id').value = doctorId;
            
            const dtInput = document.getElementById('modal-new-datetime');
            dtInput.value = '';
            
            const now = new Date();
            const tzOffset = now.getTimezoneOffset() * 60000;
            const minDt = new Date(now.getTime() - tzOffset).toISOString().slice(0, 16);
            const maxDate = new Date(now.getTime() + 2 * 24 * 60 * 60 * 1000);
            const maxDt = new Date(maxDate.getTime() - tzOffset).toISOString().slice(0, 16);
            
            dtInput.min = minDt;
            dtInput.max = maxDt;
            
            document.getElementById('modal-cutoff').value = '';
            document.getElementById('busy-slots-container').style.display = 'none';
            document.getElementById('busy-slots-list').innerHTML = '';

            document.getElementById('rescheduleModal').classList.add('open');
        }}

        function closeReschedule() {{
            document.getElementById('rescheduleModal').classList.remove('open');
        }}

        async function fetchBusySlots() {{
            const docId = document.getElementById('modal-doctor-id').value;
            const newDtVal = document.getElementById('modal-new-datetime').value;
            if (!newDtVal) return;

            const dateStr = newDtVal.split('T')[0];

            try {{
                const res = await fetch(`/receptionist/booked-slots?doctor_id=${{docId}}&date_str=${{dateStr}}`);
                const data = await res.json();
                const container = document.getElementById('busy-slots-container');
                const list = document.getElementById('busy-slots-list');
                
                list.innerHTML = '';
                if (data.booked_slots && data.booked_slots.length > 0) {{
                    data.booked_slots.forEach(slot => {{
                        const badge = document.createElement('span');
                        badge.className = 'badge cancelled';
                        badge.style.fontSize = '11px';
                        badge.style.padding = '3px 8px';
                        badge.style.background = '#fee2e2';
                        badge.style.color = '#b91c1c';
                        badge.textContent = slot;
                        list.appendChild(badge);
                    }});
                    container.style.display = 'block';
                }} else {{
                    list.innerHTML = '<span style="font-size:11px;color:#16a34a">💡 इस दिन कोई अन्य बुकिंग नहीं है। सारे स्लॉट्स खाली हैं।</span>';
                    container.style.display = 'block';
                }}
            }} catch (e) {{
                console.error("Failed to fetch busy slots", e);
            }}
        }}

        async function confirmReschedule() {{
            const apptId = document.getElementById('modal-appt-id').value;
            const newDt = document.getElementById('modal-new-datetime').value;
            const cutoff = document.getElementById('modal-cutoff').value;

            if (!newDt) {{
                alert('कृपया नई Date और Time चुनें।');
                return;
            }}

            const formData = new FormData();
            formData.append('new_status', 'RESCHEDULED');
            formData.append('new_datetime', newDt);
            formData.append('cutoff_note', cutoff);

            try {{
                const res = await fetch(`/appointments/${{apptId}}/status`, {{
                    method: 'POST',
                    body: formData
                }});
                
                if (res.status === 400) {{
                    const errData = await res.json();
                    if (errData.detail === 'appointment already rescheduled once') {{
                        alert('⚠️ यह अपॉइंटमेंट पहले ही 1 बार reschedule की जा चुकी है। इसे दोबारा reschedule नहीं किया जा सकता।');
                        closeReschedule();
                        return;
                    }}
                }}

                const data = await res.json();
                if (data.success) {{
                    closeReschedule();
                    document.getElementById(`badge-${{apptId}}`).innerHTML = '<span class="badge rescheduled">📅 Rescheduled</span>';
                    const actionsDiv = document.getElementById(`actions-${{apptId}}`);
                    if (actionsDiv) actionsDiv.remove();
                    alert('✅ Reschedule हो गया! मरीज़ के WhatsApp पर नया समय भेज दिया गया है।');
                }} else {{
                    alert('कुछ गड़बड़ हो गई।');
                }}
            }} catch (e) {{
                alert('Network error. Please try again.');
            }}
        }}

        document.getElementById('rescheduleModal').addEventListener('click', function(e) {{
            if (e.target === this) closeReschedule();
        }});
    </script>

</body>
</html>"""

    return html
