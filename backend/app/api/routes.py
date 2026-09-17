from __future__ import annotations
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import verify_password, create_token, current_user, require_roles
from app.models.entities import User, Drone, Battery, Mission, Maintenance, Telemetry, Prediction, AuditLog
from app.schemas.domain import *
from app.services.audit import log
from app.ml.predictor import predict

router=APIRouter(prefix="/api")

@router.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm=Depends(), db: Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==form.username))
    if not user or not verify_password(form.password,user.password_hash): raise HTTPException(401,"Invalid email or password")
    return Token(access_token=create_token(user), user={"id":user.id,"email":user.email,"full_name":user.full_name,"role":user.role})

@router.get("/me", response_model=UserOut)
def me(user:User=Depends(current_user)): return user

@router.get("/users", response_model=list[UserOut])
def users(db:Session=Depends(get_db), user:User=Depends(require_roles("admin"))): return db.scalars(select(User).order_by(User.id)).all()

@router.get("/drones", response_model=list[DroneOut])
def drones(db:Session=Depends(get_db), user:User=Depends(current_user)): return db.scalars(select(Drone).order_by(Drone.id)).all()

@router.post("/drones", response_model=DroneOut)
def create_drone(body:DroneCreate, db:Session=Depends(get_db), user:User=Depends(require_roles("admin","technician"))):
    obj=Drone(**body.model_dump()); db.add(obj); db.commit(); db.refresh(obj); log(db,user,"create","drone",obj.id); return obj

@router.get("/batteries", response_model=list[BatteryOut])
def batteries(db:Session=Depends(get_db), user:User=Depends(current_user)): return db.scalars(select(Battery).order_by(Battery.id)).all()

@router.post("/batteries", response_model=BatteryOut)
def create_battery(body:BatteryCreate, db:Session=Depends(get_db), user:User=Depends(require_roles("admin","technician"))):
    status="replace" if body.state_of_health<70 else "watch" if body.state_of_health<80 else "healthy"
    obj=Battery(**body.model_dump(), status=status); db.add(obj); db.commit(); db.refresh(obj); log(db,user,"create","battery",obj.id); return obj

@router.get("/missions", response_model=list[MissionOut])
def missions(db:Session=Depends(get_db), user:User=Depends(current_user)):
    q=select(Mission).order_by(Mission.id.desc())
    if user.role=="customer": q=q.where(Mission.customer_id==user.id)
    return db.scalars(q).all()

@router.post("/missions", response_model=MissionOut)
def create_mission(body:MissionCreate, db:Session=Depends(get_db), user:User=Depends(require_roles("customer","operator","admin"))):
    obj=Mission(**body.model_dump(), customer_id=user.id if user.role=="customer" else None, operator_id=user.id if user.role in ("operator","admin") else None)
    db.add(obj); db.commit(); db.refresh(obj); log(db,user,"create","mission",obj.id); return obj

@router.post("/missions/{mission_id}/predict", response_model=PredictionOut)
def mission_predict(mission_id:int, db:Session=Depends(get_db), user:User=Depends(require_roles("operator","admin"))):
    m=db.get(Mission,mission_id)
    if not m: raise HTTPException(404,"Mission not found")
    soh=db.get(Battery,m.battery_id).state_of_health if m.battery_id and db.get(Battery,m.battery_id) else 100
    result=predict(m,soh)
    p=Prediction(mission_id=m.id, model_version=result["model_version"], energy_wh=result["energy_wh"], duration_min=result["duration_min"], efficiency_m_per_wh=result["efficiency_m_per_wh"], risk_level=result["risk_level"], explanation_json=json.dumps(result["explanation"]), recommendation=result["recommendation"])
    db.add(p); db.commit(); log(db,user,"predict","mission",m.id,result["model_version"])
    return PredictionOut(mission_id=m.id, **result)

@router.post("/missions/{mission_id}/approve")
def approve(mission_id:int, reason:str="Approved after AI-assisted pre-flight review", db:Session=Depends(get_db), user:User=Depends(require_roles("operator","admin"))):
    m=db.get(Mission,mission_id)
    if not m: raise HTTPException(404,"Mission not found")
    m.status="approved"; m.approval_reason=reason; m.operator_id=user.id; db.commit(); log(db,user,"approve","mission",m.id,reason); return {"ok":True,"status":m.status}

@router.post("/telemetry")
def add_telemetry(body:TelemetryIn, db:Session=Depends(get_db), user:User=Depends(require_roles("operator","admin"))):
    obj=Telemetry(**body.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return {"id":obj.id}

@router.get("/maintenance", response_model=list[MaintenanceOut])
def maintenance(db:Session=Depends(get_db), user:User=Depends(require_roles("technician","admin","operator"))): return db.scalars(select(Maintenance).order_by(Maintenance.id.desc())).all()

@router.post("/maintenance", response_model=MaintenanceOut)
def create_maintenance(body:MaintenanceCreate, db:Session=Depends(get_db), user:User=Depends(require_roles("technician","admin"))):
    obj=Maintenance(**body.model_dump(), technician_id=user.id if user.role=="technician" else None); db.add(obj); db.commit(); db.refresh(obj); log(db,user,"create","maintenance",obj.id); return obj

@router.get("/kpis", response_model=KPIOut)
def kpis(db:Session=Depends(get_db), user:User=Depends(require_roles("operator","admin","technician"))):
    total=db.scalar(select(func.count(Mission.id))) or 0
    completed=db.scalar(select(func.count(Mission.id)).where(Mission.status=="completed")) or 0
    avail=db.scalar(select(func.count(Drone.id)).where(Drone.status=="available")) or 0
    open_m=db.scalar(select(func.count(Maintenance.id)).where(Maintenance.status!="closed")) or 0
    soh=db.scalar(select(func.avg(Battery.state_of_health))) or 0
    avg_e=db.scalar(select(func.avg(Prediction.energy_wh))) or 0
    return KPIOut(missions_total=total, completion_rate=round(100*completed/total,1) if total else 0, fleet_available=avail, maintenance_open=open_m, avg_battery_soh=round(float(soh),1), avg_prediction_energy_wh=round(float(avg_e),1))

@router.get("/audit")
def audit(db:Session=Depends(get_db), user:User=Depends(require_roles("admin"))):
    rows=db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)).all()
    return [{"id":x.id,"action":x.action,"entity_type":x.entity_type,"entity_id":x.entity_id,"details":x.details,"created_at":x.created_at} for x in rows]
