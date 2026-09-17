from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Drone(Base):
    __tablename__ = "drones"
    id: Mapped[int] = mapped_column(primary_key=True)
    serial_number: Mapped[str] = mapped_column(String(80), unique=True)
    model: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default="available")
    max_payload_kg: Mapped[float] = mapped_column(Float, default=2.0)
    total_flight_hours: Mapped[float] = mapped_column(Float, default=0.0)

class Battery(Base):
    __tablename__ = "batteries"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    drone_id: Mapped[int | None] = mapped_column(ForeignKey("drones.id"), nullable=True)
    state_of_health: Mapped[float] = mapped_column(Float, default=100.0)
    charge_cycles: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="healthy")

class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    drone_id: Mapped[int | None] = mapped_column(ForeignKey("drones.id"), nullable=True)
    battery_id: Mapped[int | None] = mapped_column(ForeignKey("batteries.id"), nullable=True)
    origin: Mapped[str] = mapped_column(String(120))
    destination: Mapped[str] = mapped_column(String(120))
    distance_km: Mapped[float] = mapped_column(Float)
    payload_kg: Mapped[float] = mapped_column(Float)
    altitude_m: Mapped[float] = mapped_column(Float)
    planned_speed_ms: Mapped[float] = mapped_column(Float)
    wind_speed_ms: Mapped[float] = mapped_column(Float, default=0)
    temperature_c: Mapped[float] = mapped_column(Float, default=20)
    humidity_pct: Mapped[float] = mapped_column(Float, default=50)
    status: Mapped[str] = mapped_column(String(30), default="planned")
    approval_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Maintenance(Base):
    __tablename__ = "maintenance"
    id: Mapped[int] = mapped_column(primary_key=True)
    drone_id: Mapped[int] = mapped_column(ForeignKey("drones.id"))
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30), default="medium")
    status: Mapped[str] = mapped_column(String(30), default="open")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Telemetry(Base):
    __tablename__ = "telemetry"
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    battery_pct: Mapped[float] = mapped_column(Float)
    speed_ms: Mapped[float] = mapped_column(Float)
    altitude_m: Mapped[float] = mapped_column(Float)
    power_w: Mapped[float] = mapped_column(Float)

class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(ForeignKey("missions.id"), index=True)
    model_version: Mapped[str] = mapped_column(String(80))
    energy_wh: Mapped[float] = mapped_column(Float)
    duration_min: Mapped[float] = mapped_column(Float)
    efficiency_m_per_wh: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(30))
    explanation_json: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
