import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    conditions = get_conditions(filters)
    data = get_data(conditions, filters)
    return columns, data


def get_columns(filters):
    columns = [
        {"label": _("Project id"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
        {"label": _("Client Reference"), "fieldname": "ref_client", "fieldtype": "Data", "width": 150},
        {"label": _("Project Order Amount"), "fieldname": "project_order_amount", "fieldtype": "Currency", "width": 160},
        {"label": _("Project Billed Amount"), "fieldname": "project_billed_amount", "fieldtype": "Currency", "width": 160},
        {"label": _("% Billed"), "fieldname": "billed_percent", "fieldtype": "Percent", "width": 110},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": _("Hours"), "fieldname": "hours", "fieldtype": "Float", "width": 120},
        {"label": _("Hourly Cost"), "fieldname": "hourly_cost", "fieldtype": "Currency", "width": 150},
        {"label": _("Employee Cost"), "fieldname": "employee_cost", "fieldtype": "Currency", "width": 150},
        {"label": _("Gross Margin"), "fieldname": "gross_margin", "fieldtype": "Currency", "width": 150},
    ]
    if filters.get("details"):
        columns.append({"label": _("From Time"), "fieldname": "from_time", "fieldtype": "Datetime", "width": 150})
        columns.append({"label": _("To Time"), "fieldname": "to_time", "fieldtype": "Datetime", "width": 150})
    return columns


def get_data(conditions, filters):
    is_details = bool(filters.get("details"))
    group_by = "" if is_details else "GROUP BY TD.project, TS.employee, PR.ref_client, OA.project_order_amount, BA.project_billed_amount"

    salary_hourly_rate_expr = """
        (
            SELECT SD.base
            FROM `tabSalary Structure Assignment Details` SD
            INNER JOIN `tabSalary Structure Assignment` SA ON SA.name = SD.parent
            WHERE SA.employee = TS.employee
                AND SA.docstatus = 1
                AND TD.from_time BETWEEN SD.from_date AND SD.end_date
            ORDER BY SD.from_date DESC
            LIMIT 1
        )
    """

    hourly_cost_row_expr = f"COALESCE(TD.costing_rate, {salary_hourly_rate_expr}, 0)"
    employee_cost_row_expr = f"COALESCE(TD.costing_amount, ({hourly_cost_row_expr}) * TD.hours, 0)"

    hours_expr = "TD.hours" if is_details else "SUM(TD.hours)"
    employee_cost_expr = employee_cost_row_expr if is_details else f"SUM({employee_cost_row_expr})"
    hourly_cost_expr = (
        hourly_cost_row_expr
        if is_details
        else f"ROUND(SUM({employee_cost_row_expr}) / NULLIF(SUM(TD.hours), 0), 2)"
    )

    query = f"""
        SELECT
            TS.employee,
            IFNULL(TD.project, 'N/A') AS project,
            {hours_expr} AS hours,
            PR.ref_client,
            IFNULL(OA.project_order_amount, 0) AS project_order_amount,
            IFNULL(BA.project_billed_amount, 0) AS project_billed_amount,
            CASE
                WHEN IFNULL(OA.project_order_amount, 0) = 0 THEN 0
                ELSE ROUND((IFNULL(BA.project_billed_amount, 0) / OA.project_order_amount) * 100, 2)
            END AS billed_percent,
            TD.from_time,
            TD.to_time,
            {hourly_cost_expr} AS hourly_cost,
            {employee_cost_expr} AS employee_cost,
            IFNULL(BA.project_billed_amount, 0) - {employee_cost_expr} AS gross_margin
        FROM `tabTimesheet Detail` TD
        LEFT JOIN `tabTimesheet` TS ON TD.parent = TS.name
        LEFT JOIN `tabProject` PR ON TD.project = PR.name
        LEFT JOIN (
            SELECT
                SOI.project,
                SUM(SOI.base_net_amount) AS project_order_amount
            FROM `tabSales Order Item` SOI
            INNER JOIN `tabSales Order` SO ON SO.name = SOI.parent
            WHERE SO.docstatus = 1
                AND IFNULL(SOI.project, '') != ''
            GROUP BY SOI.project
        ) OA ON OA.project = TD.project
        LEFT JOIN (
            SELECT
                SII.project,
                SUM(SII.base_net_amount) AS project_billed_amount
            FROM `tabSales Invoice Item` SII
            INNER JOIN `tabSales Invoice` SI ON SI.name = SII.parent
            WHERE SI.docstatus = 1
                AND IFNULL(SII.project, '') != ''
            GROUP BY SII.project
        ) BA ON BA.project = TD.project
        WHERE {conditions}
        {group_by}
    """
    return frappe.db.sql(query, filters, as_dict=True)


def get_conditions(filters):
    conditions = ["TS.docstatus = 1"]
    if filters.get("from_date"):
        conditions.append("TD.from_time >= timestamp(%(from_date)s)")
    if filters.get("to_date"):
        conditions.append("TD.to_time <= timestamp(%(to_date)s)")
    if filters.get("project"):
        conditions.append("TD.project = %(project)s")
    if filters.get("employee"):
        conditions.append("TS.employee = %(employee)s")
    return " AND ".join(conditions)
