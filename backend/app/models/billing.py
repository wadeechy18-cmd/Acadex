import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPKMixin


class SubscriptionStatus(str, PyEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class PaymentStatus(str, PyEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class PurchaseType(str, PyEnum):
    COURSE = "course"
    LIVE_CLASS = "live_class"


class EntitlementResourceType(str, PyEnum):
    COURSE = "course"
    LIVE_CLASS = "live_class"
    SUBSCRIPTION_PLAN = "subscription_plan"


class EntitlementGrantedVia(str, PyEnum):
    FREE = "free"
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    ADMIN_GRANT = "admin_grant"


class Subscription(UUIDPKMixin, TimestampMixin, Base):
    """(future) Premium subscription plans. Unused while the platform is 100% free;
    modeled now so introducing paid tiers later doesn't require new tables.
    """

    __tablename__ = "subscriptions"

    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus, name="subscription_status"), nullable=False)
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Payment(UUIDPKMixin, TimestampMixin, Base):
    """(future) Payment-provider transaction record."""

    __tablename__ = "payments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="gbp", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"), nullable=False)


class Purchase(UUIDPKMixin, TimestampMixin, Base):
    """(future) One-off purchase of a Course or LiveClass, linked to the Payment
    that funded it.
    """

    __tablename__ = "purchases"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL")
    )
    purchase_type: Mapped[PurchaseType] = mapped_column(Enum(PurchaseType, name="purchase_type"), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class Entitlement(UUIDPKMixin, TimestampMixin, Base):
    """The single source of truth the API checks before serving gated content.
    In the MVP, all content is `is_published`/free, so the access-check helper in
    `app.services` always short-circuits to 'granted' without needing this table.
    Once paid content ships, the same helper starts consulting Entitlement rows —
    no route that already calls the helper needs to change.
    """

    __tablename__ = "entitlements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[EntitlementResourceType] = mapped_column(
        Enum(EntitlementResourceType, name="entitlement_resource_type"), nullable=False
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    granted_via: Mapped[EntitlementGrantedVia] = mapped_column(
        Enum(EntitlementGrantedVia, name="entitlement_granted_via"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
