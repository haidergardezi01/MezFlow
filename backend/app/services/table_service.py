import base64
import io
import secrets
from typing import Optional, Tuple
from uuid import UUID
import qrcode
import qrcode.image.svg
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.restaurant import Restaurant
from app.models.table import Table, TableStatus
from app.schemas.table import TableLookupResponse, TableQRGraphicResponse


def generate_table_qr_token(table_number: int) -> str:
    """Generates a cryptographically random, unguessable table token."""
    return f"t{table_number}_{secrets.token_urlsafe(16)}"


async def lookup_table_by_token(
    db: AsyncSession, qr_code_token: str
) -> TableLookupResponse:
    """Validates QR code token and returns table and restaurant details."""
    query = (
        select(Table, Restaurant)
        .join(Restaurant, Table.restaurant_id == Restaurant.id)
        .where(Table.qr_code_token == qr_code_token)
    )
    result = await db.execute(query)
    row = result.first()

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

    # Convert status to lowercase string for response
    status_str = table.status.value if hasattr(table.status, "value") else str(table.status).lower()

    return TableLookupResponse(
        table_id=table.id,
        table_number=table.table_number,
        table_name=table.name,
        capacity=table.capacity,
        status=status_str,
        restaurant_id=restaurant.id,
        restaurant_name=restaurant.name,
        restaurant_slug=restaurant.slug,
        currency=restaurant.currency,
        qr_code_token=table.qr_code_token,
    )


def generate_qr_assets(
    diner_url: str,
) -> Tuple[str, str]:
    """Generates SVG string and Base64-encoded PNG data URL for a given URL."""
    # 1. Generate SVG
    svg_factory = qrcode.image.svg.SvgPathImage
    svg_img = qrcode.make(diner_url, image_factory=svg_factory)
    svg_buf = io.BytesIO()
    svg_img.save(svg_buf)
    svg_data = svg_buf.getvalue().decode("utf-8")

    # 2. Generate PNG Data URL
    png_img = qrcode.make(diner_url)
    png_buf = io.BytesIO()
    png_img.save(png_buf, format="PNG")
    png_b64 = base64.b64encode(png_buf.getvalue()).decode("utf-8")
    png_data_url = f"data:image/png;base64,{png_b64}"

    return svg_data, png_data_url


def build_table_qr_response(
    table: Table, restaurant: Restaurant, base_url: str = "http://localhost:3000"
) -> TableQRGraphicResponse:
    """Builds printable table QR response including diner URL and image assets."""
    diner_url = f"{base_url.rstrip('/')}/r/{restaurant.slug}/t/{table.qr_code_token}"
    svg_data, png_data_url = generate_qr_assets(diner_url)

    return TableQRGraphicResponse(
        table_id=table.id,
        table_number=table.table_number,
        table_name=table.name,
        qr_code_token=table.qr_code_token,
        diner_url=diner_url,
        svg_data=svg_data,
        png_data_url=png_data_url,
    )
