from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.schemas.common import ORMModel

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserOut(ORMModel):
    id: int
    email: str
    full_name: str
    role: str
    active: bool

class DroneCreate(BaseModel):
    serial_number: str
    model: str
    max_payload_kg: float = 2.0

class DroneOut(ORMModel):
    id: int
    serial_number: str
    model: str
    max_payload_kg: float
    status: str
    total_flight_hours: float

class BatteryCreate(BaseModel):
    code: str
    drone_id: int | None = None
    state_of_health: float = 100
    charge_cycles: int = 0

class BatteryOut(ORMModel):
    id: int
    code: str
    drone_id: int | None
    state_of_health: float
    charge_cycles: int
    status: str

class MissionCreate(BaseModel):
    origin: str
    destination: str
    distance_km: float = Field(gt=0)
    payload_kg: float = Field(ge=0)
    altitude_m: float = Field(gt=0)
    planned_speed_ms: float = Field(gt=0)
    wind_speed_ms: float = 0
    temperature_c: float = 20
    humidity_pct: float = 50
    drone_id: int | None = None
    battery_id: int | None = None

class MissionOut(ORMModel):
    id: int
    origin: str
    destination: str
    distance_km: float
    payload_kg: float
    altitude_m: float
    planned_speed_ms: float
    wind_speed_ms: float
    temperature_c: float
    humidity_pct: float
    drone_id: int | None
    battery_id: int | None
    customer_id: int | None
    operator_id: int | None
    status: str
    approval_reason: str | None
    created_at: datetime

class MaintenanceCreate(BaseModel):
    drone_id: int
    category: str
    severity: str = "medium"
    notes: str | None = None

class MaintenanceOut(ORMModel):
    id: int
    drone_id: int
    category: str
    severity: str
    notes: str | None
    technician_id: int | None
    status: str
    created_at: datetime

class TelemetryIn(BaseModel):
    mission_id: int
    battery_pct: float
    speed_ms: float
    altitude_m: float
    power_w: float

class PredictionOut(BaseModel):
    mission_id: int
    model_version: str
    energy_wh: float
    duration_min: float
    efficiency_m_per_wh: float
    risk_level: str
    explanation: dict
    recommendation: str

class KPIOut(BaseModel):
    missions_total: int
    completion_rate: float
    fleet_available: int
    maintenance_open: int
    avg_battery_soh: float
    avg_prediction_energy_wh: float
