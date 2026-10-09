"""
User service: registration, profile, password change and account deletion.

Every function takes the session it should use and commits its own work, so a
router is one call and one translation of exceptions to status codes.
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..auth import get_password_hash_async, verify_password_async
from ..exceptions import IdentifierTakenError, PasswordVerificationError
from ..schemas.user import (
    PasswordChangeSchema,
    User,
    UserCreateSchema,
    UserUpdateSchema,
)

logger = logging.getLogger(__name__)

# What a client is told when an identifier collides, per field, so a form can
# mark the right input. Checked before the insert; the unique constraints are
# the backstop for two requests racing past the checks.
_TAKEN_MESSAGES = {
    "username": "Username is already taken",
    "email": "Email address is already registered",
    "phone_number": "Phone number is already associated with an account",
}
_RACE_MESSAGE = "A user with this username, email, or phone number already exists"


async def _assert_identifiers_free(
    session: AsyncSession,
    values: dict[str, str | None],
    exclude_user_id: uuid.UUID | None = None,
) -> None:
    """
    Raise IdentifierTakenError if any given identifier belongs to another account.

    Args:
        session: Database session.
        values: Field name to value; None values are skipped.
        exclude_user_id: The account being edited, so its own current values
            do not count as taken.
    """
    for field, value in values.items():
        if value is None:
            continue
        statement = select(User).where(col(getattr(User, field)) == value)
        if exclude_user_id is not None:
            statement = statement.where(col(User.id) != exclude_user_id)
        if (await session.exec(statement)).first():
            raise IdentifierTakenError(_TAKEN_MESSAGES[field])


async def create_user(session: AsyncSession, user_create: UserCreateSchema) -> User:
    """
    Register a user.

    Args:
        session: Database session.
        user_create: Registration payload; `username` and `password` required.

    Returns:
        The stored User.

    Raises:
        IdentifierTakenError: A username, email or phone number is in use. The
            message names the field, or is generic if the collision was only
            caught by the database's unique constraint.
    """
    await _assert_identifiers_free(
        session,
        {
            "username": user_create.username,
            "email": user_create.email,
            "phone_number": user_create.phone_number,
        },
    )
    hashed_password = await get_password_hash_async(user_create.password)
    db_user = User(
        **user_create.model_dump(exclude={"password"}), hashed_password=hashed_password
    )
    try:
        session.add(db_user)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise IdentifierTakenError(_RACE_MESSAGE)
    await session.refresh(db_user)
    return db_user


async def update_user(
    session: AsyncSession, db_user: User, user_update: UserUpdateSchema
) -> User:
    """
    Apply the fields present in `user_update` to the user's profile.

    Only fields the client sent are touched, so an omitted field is left alone
    and an explicit null clears it.

    Args:
        session: Database session.
        db_user: The account being edited (the authenticated user).
        user_update: Profile fields to change.

    Returns:
        The updated User.

    Raises:
        IdentifierTakenError: The new email or phone number belongs to another
            account.
    """
    changes = user_update.model_dump(exclude_unset=True)
    await _assert_identifiers_free(
        session,
        {k: changes.get(k) for k in ("email", "phone_number")},
        exclude_user_id=db_user.id,
    )
    for field, value in changes.items():
        if field == "profile_picture_url" and value is not None:
            value = str(value)  # HttpUrl -> str for the column
        setattr(db_user, field, value)
    try:
        session.add(db_user)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise IdentifierTakenError(_RACE_MESSAGE)
    await session.refresh(db_user)
    return db_user


async def change_user_password(
    session: AsyncSession, db_user: User, password_change: PasswordChangeSchema
) -> None:
    """
    Replace the user's password after confirming the current one.

    Requiring the current password means a stolen token alone cannot lock the
    owner out of their account.

    Args:
        session: Database session.
        db_user: The authenticated user.
        password_change: Current and new password.

    Raises:
        PasswordVerificationError: The current password does not match.
    """
    if not await verify_password_async(
        password_change.current_password, db_user.hashed_password
    ):
        raise PasswordVerificationError("Incorrect current password")
    db_user.hashed_password = await get_password_hash_async(
        password_change.new_password
    )
    session.add(db_user)
    await session.commit()


async def delete_user(session: AsyncSession, db_user: User, password: str) -> None:
    """
    Permanently delete the user's account after confirming the password.

    A hard delete: the row is gone and every token for it stops working on the
    next request, because tokens are resolved by id against the table.

    Args:
        session: Database session.
        db_user: The authenticated user.
        password: The account's current password.

    Raises:
        PasswordVerificationError: The password does not match.
    """
    if not await verify_password_async(password, db_user.hashed_password):
        raise PasswordVerificationError("Incorrect password")
    await session.delete(db_user)
    await session.commit()
