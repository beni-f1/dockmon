"""
DockMon v2 User Management API

Provides admin-only endpoints for managing users with role-based access control.

ROLES:
- admin: Full access - can manage users, hosts, containers, and all settings
- user: Standard access - can manage containers and hosts but not users
- readonly: View-only access - can only view data, no modifications

SECURITY:
- All endpoints require admin scope
- Password hashing with Argon2id
- Audit logging for all user management actions
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, field_validator
import secrets

from auth.api_key_auth import get_current_user_or_api_key as get_current_user, require_scope
from auth.shared import db
from database import User, UserPrefs
from security.audit import security_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/users", tags=["users"])

# Valid roles
VALID_ROLES = ["admin", "user", "readonly"]


def parse_tags(tags_json: Optional[str]) -> Optional[List[str]]:
    """Parse JSON string of tags to list"""
    if not tags_json:
        return None
    try:
        tags = json.loads(tags_json)
        return tags if isinstance(tags, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


def serialize_tags(tags: Optional[List[str]]) -> Optional[str]:
    """Serialize tags list to JSON string"""
    if not tags:
        return None
    return json.dumps(tags)


# ==================== Request/Response Models ====================

class UserCreate(BaseModel):
    """Create user request"""
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)
    role: str = Field(default="user", pattern=r"^(admin|user|readonly)$")
    visible_tags: Optional[List[str]] = Field(None, description="Whitelist: only show containers with these tags")
    hidden_tags: Optional[List[str]] = Field(None, description="Blacklist: hide containers with these tags")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
        return v


class UserUpdate(BaseModel):
    """Update user request"""
    display_name: Optional[str] = Field(None, max_length=100)
    role: Optional[str] = Field(None, pattern=r"^(admin|user|readonly)$")
    must_change_password: Optional[bool] = None
    visible_tags: Optional[List[str]] = Field(None, description="Whitelist: only show containers with these tags")
    hidden_tags: Optional[List[str]] = Field(None, description="Blacklist: hide containers with these tags")
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_ROLES:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")
        return v


class UserResponse(BaseModel):
    """User response model"""
    id: int
    username: str
    display_name: Optional[str] = None
    role: str
    visible_tags: Optional[List[str]] = None
    hidden_tags: Optional[List[str]] = None
    is_first_login: bool
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class UserListResponse(BaseModel):
    """List users response"""
    users: List[UserResponse]
    total: int


class PasswordResetResponse(BaseModel):
    """Password reset response"""
    temporary_password: str
    message: str


# ==================== API Endpoints ====================

@router.get("", response_model=UserListResponse, dependencies=[Depends(require_scope("admin"))])
async def list_users(
    current_user: dict = Depends(get_current_user)
):
    """
    List all users.
    
    SECURITY: Requires admin scope
    """
    with db.get_session() as session:
        users = session.query(User).order_by(User.created_at.desc()).all()
        
        user_list = [
            UserResponse(
                id=u.id,
                username=u.username,
                display_name=u.display_name,
                role=u.role,
                visible_tags=parse_tags(u.visible_tags),
                hidden_tags=parse_tags(u.hidden_tags),
                is_first_login=u.is_first_login,
                must_change_password=u.must_change_password,
                created_at=u.created_at.replace(tzinfo=timezone.utc) if u.created_at else datetime.now(timezone.utc),
                updated_at=u.updated_at.replace(tzinfo=timezone.utc) if u.updated_at else datetime.now(timezone.utc),
                last_login=u.last_login.replace(tzinfo=timezone.utc) if u.last_login else None
            )
            for u in users
        ]
        
        return UserListResponse(users=user_list, total=len(user_list))


@router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_scope("admin"))])
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Get user by ID.
    
    SECURITY: Requires admin scope
    """
    with db.get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            visible_tags=parse_tags(user.visible_tags),
            hidden_tags=parse_tags(user.hidden_tags),
            is_first_login=user.is_first_login,
            must_change_password=user.must_change_password,
            created_at=user.created_at.replace(tzinfo=timezone.utc) if user.created_at else datetime.now(timezone.utc),
            updated_at=user.updated_at.replace(tzinfo=timezone.utc) if user.updated_at else datetime.now(timezone.utc),
            last_login=user.last_login.replace(tzinfo=timezone.utc) if user.last_login else None
        )


@router.post("", response_model=UserResponse, status_code=201, dependencies=[Depends(require_scope("admin"))])
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new user.
    
    If no password is provided, a random temporary password is generated
    and the user will be required to change it on first login.
    
    SECURITY: Requires admin scope
    """
    with db.get_session() as session:
        # Check if username already exists
        existing = session.query(User).filter(User.username == user_data.username).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Generate password if not provided
        password = user_data.password
        must_change = False
        if not password:
            password = secrets.token_urlsafe(12)
            must_change = True
        
        # Hash password
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        password_hash = ph.hash(password)
        
        # Create user
        new_user = User(
            username=user_data.username,
            password_hash=password_hash,
            display_name=user_data.display_name,
            role=user_data.role,
            visible_tags=serialize_tags(user_data.visible_tags),
            hidden_tags=serialize_tags(user_data.hidden_tags),
            is_first_login=True,
            must_change_password=must_change,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(new_user)
        session.flush()  # Get the ID
        
        # Create user preferences
        user_prefs = UserPrefs(
            user_id=new_user.id,
            theme="dark",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(user_prefs)
        session.commit()
        
        # Log event
        security_audit.log_event(
            event_type="user_created",
            severity="info",
            user_id=current_user.get("user_id"),
            details={
                "created_user_id": new_user.id,
                "created_username": new_user.username,
                "role": new_user.role,
                "created_by": current_user.get("username")
            }
        )
        
        logger.info(f"User '{new_user.username}' created by '{current_user.get('username')}'")
        
        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            display_name=new_user.display_name,
            role=new_user.role,
            visible_tags=parse_tags(new_user.visible_tags),
            hidden_tags=parse_tags(new_user.hidden_tags),
            is_first_login=new_user.is_first_login,
            must_change_password=new_user.must_change_password,
            created_at=new_user.created_at,
            updated_at=new_user.updated_at,
            last_login=None
        )


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_scope("admin"))])
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(get_current_user)
):
    """
    Update user details.
    
    SECURITY: 
    - Requires admin scope
    - Cannot demote the last admin user
    """
    with db.get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prevent demoting the last admin
        if user_data.role and user_data.role != "admin" and user.role == "admin":
            admin_count = session.query(User).filter(User.role == "admin").count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot change role of the last admin user"
                )
        
        # Update fields
        if user_data.display_name is not None:
            user.display_name = user_data.display_name if user_data.display_name.strip() else None
        if user_data.role is not None:
            user.role = user_data.role
        if user_data.must_change_password is not None:
            user.must_change_password = user_data.must_change_password
        if user_data.visible_tags is not None:
            # Empty list clears the filter, None keeps existing value
            user.visible_tags = serialize_tags(user_data.visible_tags) if user_data.visible_tags else None
        if user_data.hidden_tags is not None:
            user.hidden_tags = serialize_tags(user_data.hidden_tags) if user_data.hidden_tags else None
        
        user.updated_at = datetime.now(timezone.utc)
        session.commit()
        
        # Log event
        security_audit.log_event(
            event_type="user_updated",
            severity="info",
            user_id=current_user.get("user_id"),
            details={
                "updated_user_id": user.id,
                "updated_username": user.username,
                "changes": user_data.model_dump(exclude_none=True),
                "updated_by": current_user.get("username")
            }
        )
        
        logger.info(f"User '{user.username}' updated by '{current_user.get('username')}'")
        
        return UserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
            visible_tags=parse_tags(user.visible_tags),
            hidden_tags=parse_tags(user.hidden_tags),
            is_first_login=user.is_first_login,
            must_change_password=user.must_change_password,
            created_at=user.created_at.replace(tzinfo=timezone.utc) if user.created_at else datetime.now(timezone.utc),
            updated_at=user.updated_at.replace(tzinfo=timezone.utc) if user.updated_at else datetime.now(timezone.utc),
            last_login=user.last_login.replace(tzinfo=timezone.utc) if user.last_login else None
        )


@router.delete("/{user_id}", dependencies=[Depends(require_scope("admin"))])
async def delete_user(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a user.
    
    SECURITY:
    - Requires admin scope
    - Cannot delete yourself
    - Cannot delete the last admin user
    """
    with db.get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Cannot delete yourself
        if user.id == current_user.get("user_id"):
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Cannot delete the last admin
        if user.role == "admin":
            admin_count = session.query(User).filter(User.role == "admin").count()
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete the last admin user"
                )
        
        username = user.username
        
        # Delete user preferences first
        session.query(UserPrefs).filter(UserPrefs.user_id == user_id).delete()
        
        # Delete user
        session.delete(user)
        session.commit()
        
        # Log event
        security_audit.log_event(
            event_type="user_deleted",
            severity="warning",
            user_id=current_user.get("user_id"),
            details={
                "deleted_user_id": user_id,
                "deleted_username": username,
                "deleted_by": current_user.get("username")
            }
        )
        
        logger.info(f"User '{username}' deleted by '{current_user.get('username')}'")
        
        return {"message": f"User '{username}' deleted successfully"}


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse, dependencies=[Depends(require_scope("admin"))])
async def reset_user_password(
    user_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Reset user password to a temporary password.
    
    The user will be required to change the password on next login.
    
    SECURITY: Requires admin scope
    """
    with db.get_session() as session:
        user = session.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate temporary password
        temp_password = secrets.token_urlsafe(12)
        
        # Hash and save
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        user.password_hash = ph.hash(temp_password)
        user.must_change_password = True
        user.updated_at = datetime.now(timezone.utc)
        session.commit()
        
        # Log event
        security_audit.log_event(
            event_type="user_password_reset",
            severity="warning",
            user_id=current_user.get("user_id"),
            details={
                "reset_user_id": user.id,
                "reset_username": user.username,
                "reset_by": current_user.get("username")
            }
        )
        
        logger.info(f"Password reset for user '{user.username}' by '{current_user.get('username')}'")
        
        return PasswordResetResponse(
            temporary_password=temp_password,
            message=f"Password reset for '{user.username}'. User must change password on next login."
        )


@router.get("/roles/available", dependencies=[Depends(require_scope("read"))])
async def get_available_roles(
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of available roles with descriptions.
    
    SECURITY: Requires read scope (for UI display)
    """
    return {
        "roles": [
            {
                "id": "admin",
                "name": "Administrator",
                "description": "Full access - can manage users, hosts, containers, and all settings",
                "scopes": ["admin"]
            },
            {
                "id": "user",
                "name": "Standard User",
                "description": "Can manage containers and hosts but cannot manage users",
                "scopes": ["read", "write"]
            },
            {
                "id": "readonly",
                "name": "Read Only",
                "description": "View-only access - cannot make any modifications",
                "scopes": ["read"]
            }
        ]
    }
