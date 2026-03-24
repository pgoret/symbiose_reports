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
        {"label": _("Sales Order"), "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 150},
        {"label": _("Client Reference"), "fieldname": "ref_client", "fieldtype": "Data", "width": 150},
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 150},
        {"label": _("Total HTVA"), "fieldname": "total", "fieldtype": "Currency", "width": 150},
        {"label": _("Hours"), "fieldname": "hours", "fieldtype": "Float", "width": 120},
        {"label": _("Hourly Cost"), "fieldname": "hourly_cost", "fieldtype": "Currency", "width": 150},
        {"label": _("Employee Cost"), "fieldname": "employee_cost", "fieldtype": "Currency", "width": 150},
    ]
    if filters.get("details"):
        columns.append({"label": _("From Time"), "fieldname": "from_time", "fieldtype": "Datetime", "width": 150})
        columns.append({"label": _("To Time"), "fieldname": "to_time", "fieldtype": "Datetime", "width": 150})
    return columns


def get_data(conditions, filters):
    aggregate = "" if filters.get("details") else "SUM"
    group_by = "" if filters.get("details") else "GROUP BY ID"
    query = f"""
        SELECT
            TS.employee,
            IFNULL(TD.project, 'N/A') AS project,
            {aggregate}(TD.hours) AS hours,
            PR.ref_client,
            TD.from_time,
            TD.to_time,
            SD.base AS hourly_cost,
            {aggregate}(SD.base * TD.hours) AS employee_cost,
            SO.total,
            SO.name AS sales_order,
            CONCAT(TD.project, '-', TS.employee, '-', IFNULL(SD.base, 0)) AS ID
        FROM `tabTimesheet Detail` TD
        LEFT JOIN `tabTimesheet` TS ON TD.parent = TS.name
        LEFT JOIN `tabProject` PR ON TD.project = PR.name
        LEFT JOIN `tabSalary Structure Assignment` SA ON TS.employee = SA.employee
        LEFT JOIN `tabSalary Structure Assignment Details` SD
            ON SD.parent = SA.name AND TD.from_time BETWEEN SD.from_date AND SD.end_date
        LEFT JOIN `tabSales Order` SO ON SO.name LIKE CONCAT(TD.project, '%%') AND SO.status NOT LIKE 'Cancelled'
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
