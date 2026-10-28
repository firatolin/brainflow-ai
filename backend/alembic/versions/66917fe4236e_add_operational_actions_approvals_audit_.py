"""add operational actions, approvals, audit events

Revision ID: 66917fe4236e
Revises: d4d5a078a04d
Create Date: 2026-10-28 09:22:17.376633
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '66917fe4236e'
down_revision: Union[str, None] = 'd4d5a078a04d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action_type", sa.String(length=60), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("recovery_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum(
            "DRAFT", "PENDING_APPROVAL", "APPROVED", "REJECTED", "EXECUTED", "CANCELLED",
            name="action_status",
        ), nullable=False, server_default="PENDING_APPROVAL"),
        sa.Column("before_state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("proposed_state_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("expected_impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer", sa.String(length=120), nullable=True),
        sa.Column("execution_result", sa.Text(), nullable=True),
    )
    op.create_index("ix_operational_actions_plan_id", "operational_actions", ["plan_id"])
    op.create_index("ix_operational_actions_status", "operational_actions", ["status"])
    op.create_index("ix_operational_actions_requested_at", "operational_actions", ["requested_at"])

    op.create_table(
        "approvals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("action_id", sa.Integer(), sa.ForeignKey("operational_actions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.Enum(
            "PENDING", "APPROVED", "REJECTED",
            name="approval_decision",
        ), nullable=False, server_default="PENDING"),
        sa.Column("reviewer", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approvals_action_id", "approvals", ["action_id"])
    op.create_index("ix_approvals_decision", "approvals", ["decision"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=False, server_default="system"),
        sa.Column("context_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_entity_id", table_name="audit_events")
    op.drop_index("ix_audit_events_entity_type", table_name="audit_events")
    op.drop_index("ix_audit_events_event_type", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("ix_approvals_decision", table_name="approvals")
    op.drop_index("ix_approvals_action_id", table_name="approvals")
    op.drop_table("approvals")

    op.drop_index("ix_operational_actions_requested_at", table_name="operational_actions")
    op.drop_index("ix_operational_actions_status", table_name="operational_actions")
    op.drop_index("ix_operational_actions_plan_id", table_name="operational_actions")
    op.drop_table("operational_actions")
