import frappe


def is_float(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def execute(filters=None):
    filters = filters or {}
    columns = get_columns(filters)
    data = get_data(get_conditions(filters), filters)

    data_chart = {}
    for row in data:
        asset_name = row.get("asset_name")
        if not asset_name:
            continue
        data_chart.setdefault(asset_name, 0)
        if is_float(row.get("hours")):
            data_chart[asset_name] += float(row.get("hours"))

    chart = {
        "data": {
            "labels": list(data_chart.keys()),
            "datasets": [{"values": list(data_chart.values())}],
        },
        "type": "bar",
    }
    return columns, data, None, chart


def get_columns(filters=None):
    return [
        {"label": "Type", "fieldname": "type", "fieldtype": "Data", "width": 160},
        {"label": "Asset Name", "fieldname": "asset_name", "fieldtype": "Link", "options": "Asset", "width": 160},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Data", "width": 160},
        {"label": "From Time", "fieldname": "from_time", "fieldtype": "Datetime", "width": 160},
        {"label": "To Time", "fieldname": "to_time", "fieldtype": "Datetime", "width": 160},
        {"label": "Hrs", "fieldname": "hours", "fieldtype": "Float", "width": 100},
        {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 160},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 140},
        {"label": "Timesheet / Reference", "fieldname": "reference", "fieldtype": "Data", "width": 160},
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
        {"label": "Employee", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 160},
        {"label": "Work Order", "fieldname": "work_order", "fieldtype": "Data", "width": 140},
        {"label": "Equipment ID", "fieldname": "tag_sap", "fieldtype": "Data", "width": 140},
        {"label": "Ticket Sodexo", "fieldname": "ticket_sodexo_link", "fieldtype": "Data", "width": 160},
        {"label": "Remarque", "fieldname": "comments", "fieldtype": "Small Text", "width": 220},
        {"label": "Document Status", "fieldname": "docstatus", "fieldtype": "Int", "width": 110},
    ]


def get_conditions(filters):
    conditions = {}
    selected_modules = str(filters.get("module") or "")
    conditions["Timesheet"] = 1 if "Timesheet" in selected_modules else 0
    conditions["Asset_Maintenance"] = 1 if "Asset Maintenance" in selected_modules else 0
    conditions["Asset_Repair"] = 1 if "Asset Repair" in selected_modules else 0

    asset_name = filters.get("asset_name")
    conditions["asset_name_TD"] = f"AND asset_name = '{asset_name}'" if asset_name else ""
    conditions["asset_name_AL"] = f"AND AL.asset_name = '{asset_name}'" if asset_name else ""
    conditions["asset_name_AR"] = f"AND AR.asset_name = '{asset_name}'" if asset_name else ""

    doc_name = filters.get("doc_name")
    conditions["comments"] = (
        "AND (TD.tag_sap LIKE '%%{0}%%' OR TD.work_order LIKE '%%{0}%%')".format(doc_name)
        if doc_name
        else ""
    )

    start_date, end_date = filters.get("start_date"), filters.get("end_date")
    if start_date and end_date:
        conditions["date_TD"] = f" AND TD.from_time BETWEEN '{start_date} 00:00:00.000' AND '{end_date} 23:59:59.998'"
        conditions["date_AL"] = f" AND AL.tasks_completed_on BETWEEN '{start_date} 00:00:00.000' AND '{end_date} 23:59:59.998'"
        conditions["date_AR"] = f" AND AR.completion_date BETWEEN '{start_date} 00:00:00.000' AND '{end_date} 23:59:59.998'"
    else:
        conditions["date_TD"] = ""
        conditions["date_AL"] = ""
        conditions["date_AR"] = ""

    employee = filters.get("employee")
    conditions["employee"] = f"AND TT.employee = '{employee}'" if employee else ""

    item_group = filters.get("item_group")
    conditions["item_group"] = f"AND TA.item_group = '{item_group}'" if item_group else ""

    asset_category = filters.get("asset_category")
    conditions["asset_category"] = f"AND TA.asset_category = '{asset_category}'" if asset_category else ""

    project = filters.get("project")
    conditions["project"] = f"AND TD.project = '{project}'" if project else ""
    return conditions


def get_data(conditions=None, filters=None):
    conditions = conditions or {}
    unions = []
    for i in range(1, 25):
        unions.append(
            f"""
            SELECT
                TD.etalon_{i} AS asset_name,
                TA.item_group,
                TD.project,
                TD.from_time AS from_time,
                TD.to_time AS to_time,
                TD.hours,
                TT.employee,
                TD.parent AS reference,
                TD.work_order,
                TD.tag_sap,
                TD.ticket_sodexo_link,
                TD.infos_complémentaires AS comments,
                'Timesheet' AS type,
                TT.docstatus,
                'N/A' AS status,
                TD.info_complémentaire_project_id AS description,
                TA.asset_category
            FROM `tabTimesheet Detail` TD
            LEFT JOIN `tabTimesheet` TT ON TD.parent = TT.name
            LEFT JOIN `tabAsset` TA ON TD.etalon_{i} = TA.name
            WHERE
                {conditions['Timesheet']} = 1 AND asset_name IS NOT NULL
                {conditions['asset_name_TD']}
                {conditions['comments']}
                {conditions['date_TD']}
                {conditions['employee']}
                {conditions['item_group']}
                {conditions['project']}
                {conditions['asset_category']}
            """
        )

    unions.append(
        f"""
        SELECT
            AL.asset_name,
            TA.item_group,
            'N/A' AS project,
            AL.start_date AS from_time,
            AL.tasks_completed_on AS to_time,
            'N/A' AS hours,
            'N/A' AS employee,
            AL.name AS reference,
            'N/A' AS work_order,
            'N/A' AS tag_sap,
            'N/A' AS ticket_sodexo_link,
            AL._comments AS comments,
            'Asset Maintenance' AS type,
            AL.docstatus,
            AL.as_found_result AS status,
            AL.maintenance_type AS description,
            TA.asset_category
        FROM `tabAsset Maintenance Log` AL
        LEFT JOIN `tabAsset` TA ON AL.asset_name = TA.name
        WHERE
            {conditions['Asset_Maintenance']} = 1 AND AL.docstatus != 0
            {conditions['asset_name_AL']}
            {conditions['date_AL']}
            {conditions['item_group']}
            {conditions['asset_category']}
        """
    )

    unions.append(
        f"""
        SELECT
            AR.asset_name,
            TA.item_group,
            'N/A' AS project,
            AR.failure_date AS from_time,
            AR.completion_date AS to_time,
            'N/A' AS hours,
            'N/A' AS employee,
            AR.name AS reference,
            'N/A' AS work_order,
            'N/A' AS tag_sap,
            'N/A' AS ticket_sodexo_link,
            AR.actions_performed AS comments,
            'Asset Repair' AS type,
            AR.docstatus,
            AR.repair_status AS status,
            AR.description AS description,
            TA.asset_category
        FROM `tabAsset Repair` AR
        LEFT JOIN `tabAsset` TA ON AR.asset_name = TA.name
        WHERE
            {conditions['Asset_Repair']} = 1
            {conditions['asset_name_AR']}
            {conditions['date_AR']}
            {conditions['item_group']}
            {conditions['asset_category']}
        """
    )

    query = "\nUNION\n".join(unions)
    return frappe.db.sql(query, filters or {}, as_dict=True)
