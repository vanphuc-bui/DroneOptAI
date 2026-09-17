from __future__ import annotations

import copy
import json
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import verify_password, create_token, current_user, require_roles
from app.models.entities import User, Drone, Battery, Mission, Maintenance, Telemetry, Prediction, AuditLog
from app.schemas.domain import (
    Token, UserOut, DroneCreate, DroneOut, BatteryCreate, BatteryOut,
    MissionCreate, MissionOut, MaintenanceCreate, MaintenanceOut,
    TelemetryIn, TelemetryOut, PredictionOut, PredictionHistoryOut,
    KPIOut, WhatIfIn
)
from app.services.audit import log
from app.ml.predictor import predict

router = APIRouter(prefix="/api")


def mission_for_user(db: Session, mission_id: int, user: User) -> Mission:
    mission = db.get(Mission, mission_id)
    if not mission:
        raise HTTPException(404, "Mission not found")
    if user.role == "customer" and mission.customer_id != user.id:
        raise HTTPException(403, "Insufficient permissions")
    return mission


@router.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return Token(access_token=create_token(user), user={"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role})


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.get("/users", response_model=list[UserOut])
def users(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    return db.scalars(select(User).order_by(User.id)).all()


@router.get("/drones", response_model=list[DroneOut])
def drones(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "operator", "technician"))):
    return db.scalars(select(Drone).order_by(Drone.id)).all()


@router.post("/drones", response_model=DroneOut)
def create_drone(body: DroneCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "technician"))):
    obj = Drone(**body.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    log(db, user, "create", "drone", obj.id)
    return obj


@router.get("/batteries", response_model=list[BatteryOut])
def batteries(db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "operator", "technician"))):
    return db.scalars(select(Battery).order_by(Battery.id)).all()


@router.post("/batteries", response_model=BatteryOut)
def create_battery(body: BatteryCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("admin", "technician"))):
    status = "replace" if body.state_of_health < 70 else "watch" if body.state_of_health < 80 else "healthy"
    obj = Battery(**body.model_dump(), status=status)
    db.add(obj); db.commit(); db.refresh(obj)
    log(db, user, "create", "battery", obj.id)
    return obj


@router.get("/missions", response_model=list[MissionOut])
def missions(db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Mission).order_by(Mission.id.desc())
    if user.role == "customer":
        q = q.where(Mission.customer_id == user.id)
    return db.scalars(q).all()


@router.post("/missions", response_model=MissionOut)
def create_mission(body: MissionCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("customer", "operator", "admin"))):
    obj = Mission(**body.model_dump(), customer_id=user.id if user.role == "customer" else None, operator_id=user.id if user.role in ("operator", "admin") else None)
    db.add(obj); db.commit(); db.refresh(obj)
    log(db, user, "create", "mission", obj.id)
    return obj


@router.post("/missions/{mission_id}/predict", response_model=PredictionOut)
def mission_predict(mission_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("operator", "admin"))):
    mission = mission_for_user(db, mission_id, user)
    battery = db.get(Battery, mission.battery_id) if mission.battery_id else None
    result = predict(mission, battery.state_of_health if battery else 100)
    p = Prediction(mission_id=mission.id, model_version=result["model_version"], energy_wh=result["energy_wh"], duration_min=result["duration_min"], efficiency_m_per_wh=result["efficiency_m_per_wh"], risk_level=result["risk_level"], explanation_json=json.dumps(result["explanation"]), recommendation=result["recommendation"])
    db.add(p); db.commit(); db.refresh(p)
    log(db, user, "predict", "mission", mission.id, result["model_version"])
    return PredictionOut(mission_id=mission.id, **result)


@router.post("/missions/{mission_id}/what-if", response_model=PredictionOut)
def mission_what_if(mission_id: int, body: WhatIfIn, db: Session = Depends(get_db), user: User = Depends(require_roles("operator", "admin"))):
    mission = mission_for_user(db, mission_id, user)
    scenario = copy.copy(mission)
    if body.payload_kg is not None: scenario.payload_kg = body.payload_kg
    if body.wind_speed_ms is not None: scenario.wind_speed_ms = body.wind_speed_ms
    if body.planned_speed_ms is not None: scenario.planned_speed_ms = body.planned_speed_ms
    battery = db.get(Battery, mission.battery_id) if mission.battery_id else None
    soh = body.battery_soh if body.battery_soh is not None else (battery.state_of_health if battery else 100)
    result = predict(scenario, soh)
    result["model_version"] = result["model_version"] + "-what-if"
    log(db, user, "what_if", "mission", mission.id, json.dumps(body.model_dump(exclude_none=True)))
    return PredictionOut(mission_id=mission.id, **result)


@router.post("/missions/{mission_id}/approve")
def approve(mission_id: int, reason: str = "Approved after AI-assisted pre-flight review", db: Session = Depends(get_db), user: User = Depends(require_roles("operator", "admin"))):
    mission = mission_for_user(db, mission_id, user)
    mission.status = "approved"; mission.approval_reason = reason; mission.operator_id = user.id
    db.commit(); log(db, user, "approve", "mission", mission.id, reason)
    return {"ok": True, "status": mission.status}


@router.get("/predictions", response_model=list[PredictionHistoryOut])
def predictions(mission_id: int | None = Query(default=None), db: Session = Depends(get_db), user: User = Depends(require_roles("operator", "admin"))):
    q = select(Prediction).order_by(Prediction.id.desc()).limit(50)
    if mission_id is not None: q = q.where(Prediction.mission_id == mission_id)
    rows = db.scalars(q).all()
    return [PredictionHistoryOut(id=x.id, mission_id=x.mission_id, model_version=x.model_version, energy_wh=x.energy_wh, duration_min=x.duration_min, efficiency_m_per_wh=x.efficiency_m_per_wh, risk_level=x.risk_level, explanation=json.loads(x.explanation_json), recommendation=x.recommendation, created_at=x.created_at) for x in rows]


@router.post("/telemetry")
def add_telemetry(body: TelemetryIn, db: Session = Depends(get_db), user: User = Depends(require_roles("operator", "admin"))):
    mission_for_user(db, body.mission_id, user)
    obj = Telemetry(**body.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    log(db, user, "telemetry", "mission", body.mission_id, f"sample={obj.id}")
    return {"id": obj.id}


@router.get("/telemetry/{mission_id}", response_model=list[TelemetryOut])
def telemetry(mission_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    mission_for_user(db, mission_id, user)
    return db.scalars(select(Telemetry).where(Telemetry.mission_id == mission_id).order_by(Telemetry.timestamp)).all()


@router.get("/weather/current")
def weather_current(lat: float = Query(default=57.0488, ge=-90, le=90), lon: float = Query(default=9.9217, ge=-180, le=180), user: User = Depends(current_user)):
    params = {"latitude": lat, "longitude": lon, "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m", "wind_speed_unit": "ms", "timezone": "auto"}
    try:
        r = httpx.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=8.0)
        r.raise_for_status(); data = r.json()
        return {"source": "Open-Meteo", "latitude": data.get("latitude", lat), "longitude": data.get("longitude", lon), "timezone": data.get("timezone"), "current": data.get("current", {}), "units": data.get("current_units", {})}
    except Exception as exc:
        raise HTTPException(502, f"Weather provider unavailable: {exc.__class__.__name__}")


@router.get("/maintenance", response_model=list[MaintenanceOut])
def maintenance(db: Session = Depends(get_db), user: User = Depends(require_roles("technician", "admin", "operator"))):
    return db.scalars(select(Maintenance).order_by(Maintenance.id.desc())).all()


@router.post("/maintenance", response_model=MaintenanceOut)
def create_maintenance(body: MaintenanceCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("technician", "admin"))):
    obj = Maintenance(**body.model_dump(), technician_id=user.id if user.role == "technician" else None)
    db.add(obj); db.commit(); db.refresh(obj)
    log(db, user, "create", "maintenance", obj.id)
    return obj


@router.get("/kpis", response_model=KPIOut)
def kpis(db: Session = Depends(get_db), user: User = Depends(require_roles("operator", "admin", "technician"))):
    total = db.scalar(select(func.count(Mission.id))) or 0
    completed = db.scalar(select(func.count(Mission.id)).where(Mission.status == "completed")) or 0
    avail = db.scalar(select(func.count(Drone.id)).where(Drone.status == "available")) or 0
    open_m = db.scalar(select(func.count(Maintenance.id)).where(Maintenance.status != "closed")) or 0
    soh = db.scalar(select(func.avg(Battery.state_of_health))) or 0
    avg_e = db.scalar(select(func.avg(Prediction.energy_wh))) or 0
    return KPIOut(missions_total=total, completion_rate=round(100 * completed / total, 1) if total else 0, fleet_available=avail, maintenance_open=open_m, avg_battery_soh=round(float(soh), 1), avg_prediction_energy_wh=round(float(avg_e), 1))


@router.get("/reports/summary")
def report_summary(db: Session = Depends(get_db), user: User = Depends(require_roles("operator", "admin"))):
    risk_rows = db.execute(select(Prediction.risk_level, func.count(Prediction.id)).group_by(Prediction.risk_level)).all()
    return {
        "missions": {"total": db.scalar(select(func.count(Mission.id))) or 0, "planned": db.scalar(select(func.count(Mission.id)).where(Mission.status == "planned")) or 0, "approved": db.scalar(select(func.count(Mission.id)).where(Mission.status == "approved")) or 0, "completed": db.scalar(select(func.count(Mission.id)).where(Mission.status == "completed")) or 0},
        "predictions": {"total": db.scalar(select(func.count(Prediction.id))) or 0, "avg_energy_wh": round(float(db.scalar(select(func.avg(Prediction.energy_wh))) or 0), 2), "risk_distribution": {risk: count for risk, count in risk_rows}},
        "fleet": {"drones": db.scalar(select(func.count(Drone.id))) or 0, "available": db.scalar(select(func.count(Drone.id)).where(Drone.status == "available")) or 0, "avg_battery_soh": round(float(db.scalar(select(func.avg(Battery.state_of_health))) or 0), 2)},
        "maintenance_open": db.scalar(select(func.count(Maintenance.id)).where(Maintenance.status != "closed")) or 0,
    }


@router.get("/audit")
def audit(db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)).all()
    return [{"id": x.id, "action": x.action, "entity_type": x.entity_type, "entity_id": x.entity_id, "details": x.details, "created_at": x.created_at} for x in rows]
