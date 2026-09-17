from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.entities import User, Drone, Battery, Mission, Maintenance
from app.core.security import hash_password

def seed():
    db=SessionLocal()
    try:
        if db.scalar(select(User).limit(1)): return
        users=[
            User(email="admin@droneopt.ai",full_name="System Admin",role="admin",password_hash=hash_password("Admin123!")),
            User(email="operator@droneopt.ai",full_name="Flight Operator",role="operator",password_hash=hash_password("Operator123!")),
            User(email="tech@droneopt.ai",full_name="Maintenance Technician",role="technician",password_hash=hash_password("Tech123!")),
            User(email="customer@droneopt.ai",full_name="Demo Customer",role="customer",password_hash=hash_password("Customer123!")),
        ]
        db.add_all(users); db.flush()
        drones=[Drone(serial_number="DOA-001",model="DJI Matrice Demo",max_payload_kg=2.7,total_flight_hours=84.2),Drone(serial_number="DOA-002",model="Delivery X2",max_payload_kg=4.0,total_flight_hours=51.8),Drone(serial_number="DOA-003",model="Delivery X2",status="maintenance",max_payload_kg=4.0,total_flight_hours=132.4)]
        db.add_all(drones); db.flush()
        bats=[Battery(code="BAT-001",drone_id=drones[0].id,state_of_health=94,charge_cycles=71),Battery(code="BAT-002",drone_id=drones[1].id,state_of_health=82,charge_cycles=144),Battery(code="BAT-003",drone_id=drones[2].id,state_of_health=68,charge_cycles=242,status="replace")]
        db.add_all(bats); db.flush()
        missions=[Mission(customer_id=users[3].id,operator_id=users[1].id,drone_id=drones[0].id,battery_id=bats[0].id,origin="Hub A",destination="Zone North",distance_km=7.5,payload_kg=1.2,altitude_m=90,planned_speed_ms=11,wind_speed_ms=4.2,temperature_c=18,humidity_pct=61,status="approved"),Mission(customer_id=users[3].id,operator_id=users[1].id,drone_id=drones[1].id,battery_id=bats[1].id,origin="Hub B",destination="Zone East",distance_km=12.3,payload_kg=2.4,altitude_m=110,planned_speed_ms=12,wind_speed_ms=9.5,temperature_c=16,humidity_pct=70,status="planned")]
        db.add_all(missions)
        db.add(Maintenance(drone_id=drones[2].id,technician_id=users[2].id,category="Battery performance inspection",severity="high",notes="Battery SOH below replacement threshold"))
        db.commit()
    finally: db.close()
