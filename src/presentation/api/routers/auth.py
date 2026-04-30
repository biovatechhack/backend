import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Domain & Schemas
from domain.models.api_schemas import (
    DoctorRegistration,
    FamilyRegistration,
    LoginRequest,
    PatientRegistration,
    TokenResponse,
    UserRole,
)

# Security & Infrastructure
from infrastructure.security.jwt_handler import (
    create_access_token,
    get_password_hash,
    verify_password,
)
from infrastructure.supabase.client import supabase  # Assuming this exists

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest):
    # 1. Fetch user from your 'users' table in Supabase/DB
    user = supabase.table("users").select("*").eq("email", credentials.email).single().execute()
    
    if not user.data or not verify_password(credentials.password, user.data["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # 2. Create JWT
    access_token = create_access_token(
        data={"sub": user.data["id"], "role": user.data["role"]}
    )
    
    return {
        "access_token": access_token,
        "role": user.data["role"],
        "user_id": user.data["id"]
    }

@router.post("/register/patient", status_code=status.HTTP_201_CREATED)
async def register_patient(data: PatientRegistration):
    hashed_pw = get_password_hash(data.password)
    user_id = str(uuid.uuid4())
    
    # Transactional logic: Create Auth User + Patient Profile
    try:
        # Create Auth Record
        supabase.table("users").insert({
            "id": user_id,
            "email": data.email,
            "hashed_password": hashed_pw,
            "role": UserRole.PATIENT.value
        }).execute()
        
        # Create Patient Profile
        supabase.table("patients").insert({
            "id": user_id,
            "full_name": data.full_name,
            "age": data.age,
            "gender": data.gender
        }).execute()
        
        return {"message": "Patient registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register/doctor", status_code=status.HTTP_201_CREATED)
async def register_doctor(data: DoctorRegistration):
    hashed_pw = get_password_hash(data.password)
    user_id = str(uuid.uuid4())
    
    try:
        supabase.table("users").insert({
            "id": user_id,
            "email": data.email,
            "hashed_password": hashed_pw,
            "role": UserRole.DOCTOR.value
        }).execute()
        
        supabase.table("doctors").insert({
            "id": user_id,
            "full_name": data.full_name,
            "specialty": data.specialty,
            "license_number": data.license_number
        }).execute()
        
        return {"message": "Doctor registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/register/family", status_code=status.HTTP_201_CREATED)
async def register_family(data: FamilyRegistration):
    hashed_pw = get_password_hash(data.password)
    user_id = str(uuid.uuid4())
    
    try:
        supabase.table("users").insert({
            "id": user_id,
            "email": data.email,
            "hashed_password": hashed_pw,
            "role": UserRole.FAMILY.value
        }).execute()
        
        supabase.table("family_members").insert({
            "id": user_id,
            "full_name": data.full_name,
            "patient_id": str(data.patient_id)
        }).execute()
        
        return {"message": "Family member registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))