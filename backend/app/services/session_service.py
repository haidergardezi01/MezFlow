import secrets
import random
from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.table import Table, TableStatus
from app.models.restaurant import Restaurant
from app.models.session import TableSession, SessionStatus, Diner
from app.services.realtime import session_connection_manager

AVATAR_PALETTE = [
    "#F59E0B",  # Amber
    "#10B981",  # Emerald
    "#3B82F6",  # Blue
    "#EC4899",  # Pink
    "#8B5CF6",  # Purple
    "#06B6D4",  # Cyan
    "#F97316",  # Orange
]


async def get_session_by_id(
    db: AsyncSession, session_id: UUID
) -> TableSession:
    """Loads table session by ID with 404 validation."""
    query = select(TableSession).where(TableSession.id == session_id)
    res = await db.execute(query)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dining session not found.",
        )
    return session


async def join_or_create_table_session(
    db: AsyncSession,
    qr_code_token: str,
    display_name: str,
    client_session_id: Optional[str] = None,
    avatar_color: Optional[str] = None,
    user_id: Optional[UUID] = None,
) -> Tuple[TableSession, Diner]:
    """
    Resolves table from QR token, attaches to active TableSession (or initializes one),
    sets table status to OCCUPIED, and registers/resumes the diner.
    (FR-M3-01, FR-M3-02)
    """
    # 1. Resolve Table & Restaurant
    tbl_query = (
        select(Table, Restaurant)
        .join(Restaurant, Table.restaurant_id == Restaurant.id)
        .where(Table.qr_code_token == qr_code_token)
    )
    tbl_res = await db.execute(tbl_query)
    row = tbl_res.first()

    # Friendly fallback for development/manual browsing: allow 'table-4', 'table_4', 'table4', or '4'
    if not row:
        token_clean = (
            qr_code_token.lower()
            .replace("-", "")
            .replace("_", "")
            .replace(" ", "")
        )
        num_part = (
            token_clean[5:] if token_clean.startswith("table") else token_clean
        )
        if num_part.isdigit():
            fallback_query = (
                select(Table, Restaurant)
                .join(Restaurant, Table.restaurant_id == Restaurant.id)
                .where(Table.table_number == int(num_part))
            )
            fallback_res = await db.execute(fallback_query)
            row = fallback_res.first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid QR code token. Table not found.",
        )
    table, restaurant = row

    if not restaurant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This restaurant is currently inactive.",
        )

    # 2. Find or Create Active TableSession
    sess_query = select(TableSession).where(
        TableSession.table_id == table.id,
        TableSession.status == SessionStatus.ACTIVE,
    )
    sess_res = await db.execute(sess_query)
    session = sess_res.scalar_one_or_none()

    if not session:
        # Generate unguessable session token
        session_token = f"sess_{secrets.token_urlsafe(16)}"
        session = TableSession(
            restaurant_id=restaurant.id,
            table_id=table.id,
            session_token=session_token,
            status=SessionStatus.ACTIVE,
        )
        db.add(session)
        table.status = TableStatus.OCCUPIED
        await db.flush()

    # 3. Register or Resume Diner
    diner = None
    if client_session_id:
        diner_query = select(Diner).where(
            Diner.session_id == session.id,
            Diner.client_session_id == client_session_id,
        )
        diner_res = await db.execute(diner_query)
        diner = diner_res.scalar_one_or_none()

    if diner:
        diner.display_name = display_name
        diner.is_active = True
        diner.last_seen_at = datetime.now(timezone.utc)
        if user_id:
            diner.user_id = user_id
        await db.flush()
    else:
        # Create new diner in session
        assigned_client_id = client_session_id or f"cli_{secrets.token_urlsafe(16)}"
        selected_color = avatar_color or random.choice(AVATAR_PALETTE)

        # Count current diners in session
        count_query = select(func.count(Diner.id)).where(Diner.session_id == session.id)
        count_res = await db.execute(count_query)
        diner_count = count_res.scalar_one() or 0

        is_host = diner_count == 0

        diner = Diner(
            session_id=session.id,
            user_id=user_id,
            display_name=display_name.strip(),
            avatar_color=selected_color,
            client_session_id=assigned_client_id,
            is_host=is_host,
            is_active=True,
        )
        db.add(diner)
        await db.flush()

        if is_host and not session.host_diner_id:
            session.host_diner_id = diner.id
            await db.flush()

        # Real-time WebSocket notification: DINER_JOINED (< 2s)
        await session_connection_manager.publish_event(
            session_id=session.id,
            event_data={
                "event": "DINER_JOINED",
                "session_id": str(session.id),
                "diner": {
                    "id": str(diner.id),
                    "display_name": diner.display_name,
                    "avatar_color": diner.avatar_color,
                    "is_host": diner.is_host,
                },
                "active_diners_count": diner_count + 1,
            },
        )

    await db.commit()
    await db.refresh(session)
    await db.refresh(diner)

    return session, diner
