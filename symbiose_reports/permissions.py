from __future__ import annotations

import frappe


DIFFUSION_DOCTYPE = "Diffusion"
DIFFUSION_FIELDNAME = "diffusion"
PRIVILEGED_ROLES = {"System Manager", "Quality Manager", "Coordinateur Qualit\u00e9"}


def _quote_identifier(value: str) -> str:
    return f"`{value.replace('`', '``')}`"


def _get_diffusion_child_config() -> tuple[str | None, str | None]:
    diffusion_field = frappe.get_meta(DIFFUSION_DOCTYPE).get_field(DIFFUSION_FIELDNAME)
    child_doctype = getattr(diffusion_field, "options", None)

    if not child_doctype:
        return None, None

    child_meta = frappe.get_meta(child_doctype)
    role_link_fields = [
        field.fieldname
        for field in child_meta.fields
        if field.fieldtype == "Link" and field.options == "Role" and field.fieldname
    ]

    if DIFFUSION_FIELDNAME in role_link_fields:
        return child_doctype, DIFFUSION_FIELDNAME

    if "role" in role_link_fields:
        return child_doctype, "role"

    if role_link_fields:
        return child_doctype, role_link_fields[0]

    if child_meta.get_field("role"):
        return child_doctype, "role"

    return child_doctype, None


def is_privileged_user(user: str | None = None) -> bool:
    user = user or frappe.session.user

    if user == "Administrator":
        return True

    return bool(set(frappe.get_roles(user)).intersection(PRIVILEGED_ROLES))


def diffusion_query_conditions(user: str | None = None) -> str:
    user = user or frappe.session.user

    if not user or is_privileged_user(user):
        return ""

    roles = frappe.get_roles(user)
    if not roles:
        return "1 = 0"

    child_doctype, role_fieldname = _get_diffusion_child_config()
    if not child_doctype or not role_fieldname:
        return "1 = 0"

    roles_sql = ", ".join(frappe.db.escape(role) for role in roles)
    child_table = _quote_identifier(f"tab{child_doctype}")
    role_field = _quote_identifier(role_fieldname)

    return f"""
        EXISTS (
            SELECT 1
            FROM {child_table} diffusion_role
            WHERE diffusion_role.parent = `tab{DIFFUSION_DOCTYPE}`.name
              AND diffusion_role.parenttype = {frappe.db.escape(DIFFUSION_DOCTYPE)}
              AND diffusion_role.parentfield = {frappe.db.escape(DIFFUSION_FIELDNAME)}
              AND diffusion_role.{role_field} IN ({roles_sql})
        )
    """


def diffusion_has_permission(
    doc,
    user: str | None = None,
    permission_type: str | None = None,
) -> bool | None:
    user = user or frappe.session.user

    if not user or is_privileged_user(user):
        return True

    if permission_type == "create":
        return None

    child_doctype, role_fieldname = _get_diffusion_child_config()
    if not child_doctype or not role_fieldname:
        return False

    user_roles = set(frappe.get_roles(user))
    allowed_roles = _get_allowed_roles(doc, child_doctype, role_fieldname)

    if user_roles.intersection(allowed_roles):
        return None

    return False


def _get_allowed_roles(doc, child_doctype: str, role_fieldname: str) -> set[str]:
    rows = doc.get(DIFFUSION_FIELDNAME) or []
    allowed_roles = {
        row.get(role_fieldname)
        for row in rows
        if row.get(role_fieldname)
    }

    is_new = getattr(doc, "is_new", None)
    if allowed_roles or not getattr(doc, "name", None) or (callable(is_new) and is_new()):
        return allowed_roles

    return set(
        frappe.get_all(
            child_doctype,
            filters={
                "parent": doc.name,
                "parenttype": DIFFUSION_DOCTYPE,
                "parentfield": DIFFUSION_FIELDNAME,
            },
            pluck=role_fieldname,
        )
    )
