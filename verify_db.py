import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def main():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        # Hospitals
        r = await conn.execute(text("SELECT id, name, phone FROM hospitals"))
        print("=== HOSPITALS ===")
        for row in r.fetchall():
            print(f"  {row}")
        # Doctors in Balaji
        r2 = await conn.execute(text(
            "SELECT d.id, d.first_name, d.last_name, dep.name "
            "FROM doctors d LEFT JOIN departments dep ON d.department_id = dep.id "
            "WHERE d.hospital_id = 'HOSP-BALA-7282' AND d.is_active=1"
        ))
        print("=== BALAJI DOCTORS (active) ===")
        for row in r2.fetchall():
            print(f"  {row}")
        # Doctor schedules
        r3 = await conn.execute(text(
            "SELECT ds.doctor_id, ds.day_of_week, ds.start_time, ds.end_time "
            "FROM doctor_schedules ds "
            "INNER JOIN doctors d ON ds.doctor_id = d.id "
            "WHERE d.hospital_id = 'HOSP-BALA-7282'"
        ))
        print("=== DOCTOR SCHEDULES ===")
        for row in r3.fetchall():
            print(f"  {row}")
        # Recent appointments
        r4 = await conn.execute(text(
            "SELECT id, patient_id, doctor_id, appointment_datetime, status "
            "FROM appointments "
            "WHERE hospital_id = 'HOSP-BALA-7282' "
            "ORDER BY created_at DESC LIMIT 5"
        ))
        print("=== RECENT BALAJI APPOINTMENTS ===")
        rows = r4.fetchall()
        if rows:
            for row in rows:
                print(f"  {row}")
        else:
            print("  (none yet)")
    await engine.dispose()

asyncio.run(main())
