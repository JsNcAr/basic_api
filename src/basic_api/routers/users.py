from fastapi import APIRouter, HTTPException, Depends, Body
from sqlmodel.ext.asyncio.session import AsyncSession
from ..schemas.user import UserCreateSchema, UserUpdateSchema, UserLoginSchema, User, UserResponseSchema
from ..schemas import SuccessResponse
from ..dependencies import get_current_user, get_session
from ..auth import get_password_hash


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post("/", response_model=SuccessResponse[UserResponseSchema], status_code=201)
async def create_user(
    user_create: UserCreateSchema = Body(...),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new user.
    
    Args:
        user_create: UserCreateSchema containing user details
        session: Database session
        
    Returns:
        SuccessResponse[UserResponseSchema]: Created user information
    """
    # Hash the password
    hashed_password = get_password_hash(user_create.password)
    
    # Create DB user instance
    # Exclude 'password' from the input data as it's not in the User table
    user_data = user_create.model_dump(exclude={"password"})
    db_user = User(**user_data, hashed_password=hashed_password)
    
    try:
        session.add(db_user)
        await session.commit()
        await session.refresh(db_user)
    except Exception as e:
        await session.rollback()
        # Handle unique constraint violations (e.g. username/email already exists)
        # For now, just raise a generic 400
        raise HTTPException(status_code=400, detail=str(e))

    return SuccessResponse(
        success=True,
        message="User created successfully",
        data=db_user
    )
    
