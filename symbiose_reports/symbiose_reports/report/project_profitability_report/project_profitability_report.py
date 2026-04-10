def execute(filters=None):
    filters = filters or {}

    view_mode = filters.get("view_mode") or "Par projet"
    details = 1 if filters.get("details") else 0
    billing_scope = filters.get("billing_scope") or "Période filtrée"
    show_unlinked = 1 if filters.get("show_unlinked") else 0

    def safe_float(v):
        return float(v or 0)

    def pct(valeur, total):
        total = safe_float(total)
        valeur = safe_float(valeur)
        if total == 0:
            return 0
        return round((valeur / total) * 100, 2)

    def to_date_if_any(value):
        if not value:
            return None
        return frappe.utils.getdate(value)

    def get_date_only(d):
        if not d:
            return None
        try:
            return frappe.utils.getdate(d)
        except:
            return None

    def get_status_indicator(status):
        if not status:
            return ""
        s = str(status).lower()
        color = "blue"
        if "termin" in s or "complet" in s or "clos" in s:
            color = "green"
        elif "annul" in s or "cancel" in s:
            color = "red"
        return f'<span class="indicator {color}">{status}</span>'

    def build_timesheet_conditions(include_date_filters):
        conditions = ["TS.docstatus = 1", "IFNULL(TD.project, '') != ''"]

        if include_date_filters:
            if filters.get("from_date"):
                conditions.append("DATE(TD.from_time) >= %(from_date)s")
            if filters.get("to_date"):
                conditions.append("DATE(TD.to_time) <= %(to_date)s")

        if filters.get("project"):
            conditions.append("TD.project = %(project)s")
            
        if filters.get("project_status"):
            conditions.append("PR.status = %(project_status)s")

        if view_mode == "Par employé" and filters.get("employee"):
            conditions.append("TS.employee = %(employee)s")

        return " AND ".join(conditions)

    def build_timesheet_rows(include_date_filters):
        conditions_sql = build_timesheet_conditions(include_date_filters)

        hourly_cost_expr = """
            COALESCE(
                NULLIF(TD.costing_rate, 0),
                (
                    SELECT SD.base
                    FROM `tabSalary Structure Assignment` SA
                    INNER JOIN `tabSalary Structure Assignment Details` SD
                        ON SD.parent = SA.name
                    WHERE SA.employee = TS.employee
                      AND SA.docstatus = 1
                      AND DATE(TD.from_time) >= SD.from_date
                      AND DATE(TD.from_time) <= SD.end_date
                    ORDER BY SD.from_date DESC
                    LIMIT 1
                ),
                0
            )
        """

        employee_cost_expr = """
            COALESCE(
                NULLIF(TD.costing_amount, 0),
                (
                    COALESCE(
                        NULLIF(TD.costing_rate, 0),
                        (
                            SELECT SD.base
                            FROM `tabSalary Structure Assignment` SA
                            INNER JOIN `tabSalary Structure Assignment Details` SD
                                ON SD.parent = SA.name
                            WHERE SA.employee = TS.employee
                              AND SA.docstatus = 1
                              AND DATE(TD.from_time) >= SD.from_date
                              AND DATE(TD.from_time) <= SD.end_date
                            ORDER BY SD.from_date DESC
                            LIMIT 1
                        ),
                        0
                    ) * TD.hours
                ),
                0
            )
        """

        query = f"""
            SELECT
                TD.project AS project,
                PR.status AS project_status,
                (SELECT name FROM `tabSales Order` WHERE project = TD.project AND docstatus = 1 ORDER BY modified DESC LIMIT 1) AS sales_order,
                COALESCE(
                    (SELECT customer_name FROM `tabSales Order` WHERE project = TD.project AND docstatus = 1 ORDER BY modified DESC LIMIT 1),
                    PR.customer
                ) AS customer_name,
                PR.ref_client AS ref_client,
                TS.employee AS employee,
                TD.activity_type AS activity_type,
                TD.hours AS hours,
                {hourly_cost_expr} AS hourly_cost,
                {employee_cost_expr} AS employee_cost,
                IFNULL((SELECT SUM(base_net_total) FROM `tabSales Order` WHERE project = TD.project AND docstatus = 1), 0) AS project_order_amount,
                IFNULL((SELECT SUM(SI.base_net_total) FROM `tabSales Invoice` SI INNER JOIN `tabSales Order` SO ON SO.name = SI.internal_reference WHERE SO.project = TD.project AND SI.docstatus = 1), 0) AS project_billed_amount,
                TD.from_time,
                TD.to_time
            FROM `tabTimesheet Detail` TD
            INNER JOIN `tabTimesheet` TS ON TS.name = TD.parent
            LEFT JOIN `tabProject` PR ON PR.name = TD.project
            WHERE {conditions_sql}
            ORDER BY TD.project, TS.employee, TD.from_time
        """

        rows = frappe.db.sql(query, filters, as_dict=True)

        cleaned = []
        for r in rows:
            r["is_unlinked"] = 0 if r.get("sales_order") else 1
            if show_unlinked or r.get("sales_order"):
                cleaned.append(r)

        return cleaned

    def build_invoice_conditions(include_date_filters):
        conditions = ["SI.docstatus = 1", "IFNULL(SO.project, '') != ''"]

        if include_date_filters:
            if filters.get("from_date"):
                conditions.append("SI.posting_date >= %(from_date)s")
            if filters.get("to_date"):
                conditions.append("SI.posting_date <= %(to_date)s")

        if filters.get("project"):
            conditions.append("SO.project = %(project)s")
            
        if filters.get("project_status"):
            conditions.append("PR.status = %(project_status)s")

        return " AND ".join(conditions)

    def build_invoice_rows(include_date_filters):
        conditions_sql = build_invoice_conditions(include_date_filters)

        query = f"""
            SELECT
                SO.project AS project,
                SO.name AS sales_order,
                SO.customer_name AS customer_name,
                PR.ref_client AS ref_client,
                SI.name AS sales_invoice,
                SI.posting_date AS invoice_date,
                IFNULL(SI.base_net_total, 0) AS invoice_amount,
                IFNULL((SELECT SUM(base_net_total) FROM `tabSales Order` WHERE project = SO.project AND docstatus = 1), 0) AS project_order_amount_total,
                IFNULL((SELECT SUM(SI2.base_net_total) FROM `tabSales Invoice` SI2 INNER JOIN `tabSales Order` SO2 ON SO2.name = SI2.internal_reference WHERE SO2.project = SO.project AND SI2.docstatus = 1), 0) AS project_billed_amount_total
            FROM `tabSales Invoice` SI
            INNER JOIN `tabSales Order` SO ON SO.name = SI.internal_reference
            LEFT JOIN `tabProject` PR ON PR.name = SO.project
            WHERE {conditions_sql}
            ORDER BY SO.project, SI.posting_date, SI.name
        """

        rows = frappe.db.sql(query, filters, as_dict=True)

        for r in rows:
            r["invoice_date"] = to_date_if_any(r.get("invoice_date"))

        return rows

    # ==================================================================
    # Ligne de Total personnalisée mathématiquement
    # ==================================================================
    def add_custom_total_row(rows_list):
        if not rows_list:
            return rows_list

        total_hours = sum(safe_float(r.get("hours")) for r in rows_list)
        total_employee_cost = sum(safe_float(r.get("employee_cost")) for r in rows_list)
        total_order_amount = sum(safe_float(r.get("project_order_amount")) for r in rows_list)
        total_gross_margin = sum(safe_float(r.get("gross_margin")) for r in rows_list)
        
        total_invoice_amount = sum(safe_float(r.get("invoice_amount")) for r in rows_list)
        total_project_billed_amount = sum(safe_float(r.get("project_billed_amount")) for r in rows_list)

        total_row = {
            "project": "TOTAL GLOBAL",
            "project_status": "",
            "hours": round(total_hours, 3),
            "employee_cost": round(total_employee_cost, 2),
            "project_order_amount": round(total_order_amount, 2),
            "gross_margin": round(total_gross_margin, 2),
            "hourly_cost": round(total_employee_cost / total_hours, 2) if total_hours else 0,
        }

        has_invoice = any("invoice_amount" in r for r in rows_list)
        has_billed = any("project_billed_amount" in r for r in rows_list)

        if has_invoice:
            total_row["invoice_amount"] = round(total_invoice_amount, 2)
            total_row["billed_percent"] = pct(total_invoice_amount, total_order_amount)
            total_row["profit_percent"] = pct(total_gross_margin, total_invoice_amount)
        elif has_billed:
            total_row["project_billed_amount"] = round(total_project_billed_amount, 2)
            total_row["billed_percent"] = pct(total_project_billed_amount, total_order_amount)
            total_row["profit_percent"] = pct(total_gross_margin, total_project_billed_amount)
        else:
            total_row["billed_percent"] = 0.0
            total_row["profit_percent"] = 0.0

        rows_list.append(total_row)
        return rows_list

    # ==================================================================
    # NOUVEAU : Fonction de génération du graphique MIXTE Chronologique
    # ==================================================================
    def get_chart_data(current_view, ts_rows, inv_rows):
        if not ts_rows and not inv_rows:
            return None

        chart = {}
        
        # Graphique chronologique : Bâtons positifs/négatifs + Ligne de Marge
        if current_view == "Par projet":
            monthly_data = {}
            
            # Extraction des coûts mois par mois
            for ts in ts_rows:
                d = get_date_only(ts.get("from_time"))
                if not d: continue
                m = f"{d.year:04d}-{d.month:02d}" # Format YYYY-MM
                if m not in monthly_data:
                    monthly_data[m] = {"cost": 0.0, "billed": 0.0}
                monthly_data[m]["cost"] = monthly_data[m]["cost"] + safe_float(ts.get("employee_cost"))
                
            # Extraction de la facturation mois par mois
            for inv in inv_rows:
                d = get_date_only(inv.get("invoice_date"))
                if not d: continue
                m = f"{d.year:04d}-{d.month:02d}" # Format YYYY-MM
                if m not in monthly_data:
                    monthly_data[m] = {"cost": 0.0, "billed": 0.0}
                monthly_data[m]["billed"] = monthly_data[m]["billed"] + safe_float(inv.get("invoice_amount"))
                
            sorted_months = sorted(monthly_data.keys())
            labels = sorted_months
            costs = []
            billed = []
            margins = []
            
            for m in sorted_months:
                c = monthly_data[m]["cost"]
                b = monthly_data[m]["billed"]
                costs.append(-round(c, 2))  # On passe le coût en négatif pour que le bâton aille vers le bas
                billed.append(round(b, 2))
                margins.append(round(b - c, 2)) # La ligne représente la Marge Brute
                
            chart = {
                "data": {
                    "labels": labels,
                    "datasets": [
                        {"name": "Facturé (€)", "chartType": "bar", "values": billed},
                        {"name": "Coût Techniciens (€)", "chartType": "bar", "values": costs},
                        {"name": "Marge Brute (€)", "chartType": "line", "values": margins}
                    ]
                },
                "type": "axis-mixed",
                "colors": ["#28a745", "#fc4f51", "#007bff"] # Vert, Rouge, Bleu
            }

        # Pour la vue employé : un anneau simple de répartition du temps (pour différencier)
        elif current_view == "Par employé":
            employees_data = {}
            for r in ts_rows:
                e = r.get("employee")
                if not e: continue
                if e not in employees_data:
                    employees_data[e] = 0.0
                employees_data[e] = employees_data[e] + safe_float(r.get("hours"))

            labels = list(employees_data.keys())[:30]
            hours = [employees_data[e] for e in labels]

            chart = {
                "data": {
                    "labels": labels,
                    "datasets": [
                        {"name": "Heures Travaillées", "values": hours}
                    ]
                },
                "type": "donut",
                "colors": ["#3498db", "#fd7e14", "#20c997", "#e83e8c", "#6f42c1", "#6610f2"]
            }

        return chart

    # ------------------------------------------------------------------
    # Colonnes
    # ------------------------------------------------------------------
    if view_mode == "Par projet" and not details:
        columns = [
            {"label": "Projet", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
            {"label": "Statut Projet", "fieldname": "project_status", "fieldtype": "Data", "width": 120},
            {"label": "Commande Client", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
            {"label": "Client", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
            {"label": "Réf. Client", "fieldname": "ref_client", "fieldtype": "Data", "width": 180},
            {"label": "Heures", "fieldname": "hours", "fieldtype": "Float", "width": 100},
            {"label": "Coût Horaire Moyen", "fieldname": "hourly_cost", "fieldtype": "Currency", "width": 140},
            {"label": "Coût Employé", "fieldname": "employee_cost", "fieldtype": "Currency", "width": 140},
            {"label": "Montant Commande", "fieldname": "project_order_amount", "fieldtype": "Currency", "width": 150},
            {"label": "Montant Facturé", "fieldname": "project_billed_amount", "fieldtype": "Currency", "width": 150},
            {"label": "% Facturé", "fieldname": "billed_percent", "fieldtype": "Percent", "width": 100},
            {"label": "Marge Brute", "fieldname": "gross_margin", "fieldtype": "Currency", "width": 140},
            {"label": "Bénéfice (%)", "fieldname": "profit_percent", "fieldtype": "Percent", "width": 110},
        ]

    elif view_mode == "Par projet" and details:
        columns = [
            {"label": "Projet", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
            {"label": "Statut Projet", "fieldname": "project_status", "fieldtype": "Data", "width": 120},
            {"label": "Commande Client", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
            {"label": "Client", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
            {"label": "Facture", "fieldname": "sales_invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 140},
            {"label": "Date Facture", "fieldname": "invoice_date", "fieldtype": "Date", "width": 110},
            {"label": "Réf. Client", "fieldname": "ref_client", "fieldtype": "Data", "width": 180},
            {"label": "Heures (Période)", "fieldname": "hours", "fieldtype": "Float", "width": 140},
            {"label": "Coût Horaire", "fieldname": "hourly_cost", "fieldtype": "Currency", "width": 120},
            {"label": "Coût Employé", "fieldname": "employee_cost", "fieldtype": "Currency", "width": 140},
            {"label": "Commande (Allouée)", "fieldname": "project_order_amount", "fieldtype": "Currency", "width": 160},
            {"label": "Montant Facture", "fieldname": "invoice_amount", "fieldtype": "Currency", "width": 140},
            {"label": "% Facturé", "fieldname": "billed_percent", "fieldtype": "Percent", "width": 100},
            {"label": "Marge Brute", "fieldname": "gross_margin", "fieldtype": "Currency", "width": 140},
            {"label": "Bénéfice (%)", "fieldname": "profit_percent", "fieldtype": "Percent", "width": 110},
        ]

    elif view_mode == "Par employé" and not details:
        columns = [
            {"label": "Projet", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
            {"label": "Statut Projet", "fieldname": "project_status", "fieldtype": "Data", "width": 120},
            {"label": "Commande Client", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
            {"label": "Client", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
            {"label": "Réf. Client", "fieldname": "ref_client", "fieldtype": "Data", "width": 180},
            {"label": "Employé", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
            {"label": "Heures", "fieldname": "hours", "fieldtype": "Float", "width": 100},
            {"label": "Coût Horaire", "fieldname": "hourly_cost", "fieldtype": "Currency", "width": 120},
            {"label": "Coût Employé", "fieldname": "employee_cost", "fieldtype": "Currency", "width": 140},
            {"label": "Commande (Allouée)", "fieldname": "project_order_amount", "fieldtype": "Currency", "width": 160},
            {"label": "Facturé (Alloué)", "fieldname": "project_billed_amount", "fieldtype": "Currency", "width": 160},
            {"label": "% Facturé", "fieldname": "billed_percent", "fieldtype": "Percent", "width": 100},
            {"label": "Marge Brute", "fieldname": "gross_margin", "fieldtype": "Currency", "width": 140},
            {"label": "Bénéfice (%)", "fieldname": "profit_percent", "fieldtype": "Percent", "width": 110},
        ]

    else:
        columns = [
            {"label": "Projet", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 140},
            {"label": "Statut Projet", "fieldname": "project_status", "fieldtype": "Data", "width": 120},
            {"label": "Commande Client", "fieldname": "sales_order", "fieldtype": "Link", "options": "Sales Order", "width": 140},
            {"label": "Client", "fieldname": "customer_name", "fieldtype": "Data", "width": 200},
            {"label": "Réf. Client", "fieldname": "ref_client", "fieldtype": "Data", "width": 180},
            {"label": "Employé", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 140},
            {"label": "Type d'activité", "fieldname": "activity_type", "fieldtype": "Link", "options": "Activity Type", "width": 140},
            {"label": "Début", "fieldname": "from_time", "fieldtype": "Datetime", "width": 150},
            {"label": "Fin", "fieldname": "to_time", "fieldtype": "Datetime", "width": 150},
            {"label": "Heures", "fieldname": "hours", "fieldtype": "Float", "width": 100},
            {"label": "Coût Horaire", "fieldname": "hourly_cost", "fieldtype": "Currency", "width": 120},
            {"label": "Coût Employé", "fieldname": "employee_cost", "fieldtype": "Currency", "width": 140},
            {"label": "Commande (Allouée)", "fieldname": "project_order_amount", "fieldtype": "Currency", "width": 160},
            {"label": "Facturé (Alloué)", "fieldname": "project_billed_amount", "fieldtype": "Currency", "width": 160},
            {"label": "% Facturé", "fieldname": "billed_percent", "fieldtype": "Percent", "width": 100},
            {"label": "Marge Brute", "fieldname": "gross_margin", "fieldtype": "Currency", "width": 140},
            {"label": "Bénéfice (%)", "fieldname": "profit_percent", "fieldtype": "Percent", "width": 110},
        ]

    # ------------------------------------------------------------------
    # Jeux de données
    # ------------------------------------------------------------------
    filter_invoices_by_date = False if billing_scope == "Historique complet" else True
    
    visible_ts_rows = build_timesheet_rows(True)
    visible_invoice_rows = build_invoice_rows(filter_invoices_by_date)

    visible_invoices_by_project = {}
    for r in visible_invoice_rows:
        project = r.get("project")
        if project not in visible_invoices_by_project:
            visible_invoices_by_project[project] = []
        visible_invoices_by_project[project].append(r)

    visible_ts_by_project = {}
    for r in visible_ts_rows:
        project = r.get("project")
        if project not in visible_ts_by_project:
            visible_ts_by_project[project] = []
        visible_ts_by_project[project].append(r)

    # Création du Graphique avant le formatage des rows
    chart = get_chart_data(view_mode, visible_ts_rows, visible_invoice_rows)

    # ------------------------------------------------------------------
    # Vue PAR PROJET - sans détail
    # ------------------------------------------------------------------
    if view_mode == "Par projet" and not details:
        grouped = {}

        for r in visible_ts_rows:
            key = r.get("project")

            if key not in grouped:
                grouped[key] = {
                    "project": r.get("project"),
                    "project_status": r.get("project_status"),
                    "sales_order": r.get("sales_order"),
                    "customer_name": r.get("customer_name"),
                    "ref_client": r.get("ref_client"),
                    "hours": 0.0,
                    "employee_cost": 0.0,
                    "project_order_amount": safe_float(r.get("project_order_amount")),
                    "project_billed_amount": safe_float(r.get("project_billed_amount")),
                }

            grouped[key]["hours"] = grouped[key]["hours"] + safe_float(r.get("hours"))
            grouped[key]["employee_cost"] = grouped[key]["employee_cost"] + safe_float(r.get("employee_cost"))

        rows = []
        for key in grouped:
            row = grouped[key]
            row["hourly_cost"] = round(row["employee_cost"] / row["hours"], 2) if row["hours"] else 0
            row["billed_percent"] = pct(row["project_billed_amount"], row["project_order_amount"])
            row["gross_margin"] = round(row["project_billed_amount"] - row["employee_cost"], 2)
            row["profit_percent"] = pct(row["gross_margin"], row["project_billed_amount"])
            row["project_status"] = get_status_indicator(row["project_status"])
            rows.append(row)

        rows.sort(key=lambda x: (x.get("project") or ""))
        
        # Passage du `chart` à l'interface ERPNext
        return columns, add_custom_total_row(rows), None, chart, None, True

    # ------------------------------------------------------------------
    # Vue PAR PROJET - détail
    # ------------------------------------------------------------------
    if view_mode == "Par projet" and details:
        rows = []

        project_meta = {}
        for r in visible_ts_rows:
            project = r.get("project")
            if project not in project_meta:
                project_meta[project] = {
                    "project": r.get("project"),
                    "project_status": r.get("project_status"),
                    "sales_order": r.get("sales_order"),
                    "customer_name": r.get("customer_name"),
                    "ref_client": r.get("ref_client"),
                    "project_order_amount_total": safe_float(r.get("project_order_amount")),
                    "project_billed_amount_total": safe_float(r.get("project_billed_amount")),
                }

        for project in project_meta:
            meta = project_meta[project]
            project_ts = visible_ts_by_project.get(project, [])
            project_invoices = visible_invoices_by_project.get(project, [])

            total_project_hours = sum([safe_float(ts.get("hours")) for ts in project_ts])
            total_project_cost = sum([safe_float(ts.get("employee_cost")) for ts in project_ts])

            if not meta.get("sales_order") or len(project_invoices) == 0:
                if show_unlinked:
                    rows.append({
                        "project": project,
                        "project_status": get_status_indicator(meta.get("project_status")),
                        "sales_order": meta.get("sales_order"),
                        "customer_name": meta.get("customer_name"),
                        "sales_invoice": None,
                        "invoice_date": None,
                        "ref_client": meta.get("ref_client"),
                        "hours": round(total_project_hours, 3),
                        "hourly_cost": round(total_project_cost / total_project_hours, 2) if total_project_hours else 0,
                        "employee_cost": round(total_project_cost, 2),
                        "project_order_amount": round(meta.get("project_order_amount_total"), 2),
                        "invoice_amount": 0.0,
                        "billed_percent": 0.0,
                        "gross_margin": round(0.0 - total_project_cost, 2),
                        "profit_percent": pct((0.0 - total_project_cost), 0.0),
                    })
                continue

            for inv in project_invoices:
                inv["_date_obj"] = get_date_only(inv.get("invoice_date"))
                inv["matched_hours"] = 0.0
                inv["matched_cost"] = 0.0
            
            project_invoices.sort(key=lambda x: x.get("_date_obj") or frappe.utils.getdate("1900-01-01"))

            for ts in project_ts:
                ts_date = get_date_only(ts.get("from_time"))
                assigned = False
                
                for inv in project_invoices:
                    if inv.get("_date_obj") and ts_date and ts_date <= inv.get("_date_obj"):
                        inv["matched_hours"] = inv["matched_hours"] + safe_float(ts.get("hours"))
                        inv["matched_cost"] = inv["matched_cost"] + safe_float(ts.get("employee_cost"))
                        assigned = True
                        break
                
                if not assigned:
                    project_invoices[-1]["matched_hours"] = project_invoices[-1]["matched_hours"] + safe_float(ts.get("hours"))
                    project_invoices[-1]["matched_cost"] = project_invoices[-1]["matched_cost"] + safe_float(ts.get("employee_cost"))

            visible_billed_total = sum([safe_float(inv.get("invoice_amount")) for inv in project_invoices])

            for inv in project_invoices:
                invoice_amount = safe_float(inv.get("invoice_amount"))
                
                if visible_billed_total > 0:
                    invoice_ratio = invoice_amount / visible_billed_total
                else:
                    invoice_ratio = 1.0 / len(project_invoices)
                
                order_alloc = safe_float(meta.get("project_order_amount_total")) * invoice_ratio
                
                hours_alloc = inv.get("matched_hours", 0)
                cost_alloc = inv.get("matched_cost", 0)
                gross_margin = invoice_amount - cost_alloc

                rows.append({
                    "project": project,
                    "project_status": get_status_indicator(meta.get("project_status")),
                    "sales_order": inv.get("sales_order"),
                    "customer_name": inv.get("customer_name") or meta.get("customer_name"),
                    "sales_invoice": inv.get("sales_invoice"),
                    "invoice_date": inv.get("invoice_date"),
                    "ref_client": inv.get("ref_client"),
                    "hours": round(hours_alloc, 3),
                    "hourly_cost": round(cost_alloc / hours_alloc, 2) if hours_alloc else 0,
                    "employee_cost": round(cost_alloc, 2),
                    "project_order_amount": round(order_alloc, 2),
                    "invoice_amount": round(invoice_amount, 2),
                    "billed_percent": pct(invoice_amount, meta.get("project_order_amount_total")),
                    "gross_margin": round(gross_margin, 2),
                    "profit_percent": pct(gross_margin, invoice_amount),
                })

        rows.sort(key=lambda x: (
            x.get("project") or "",
            x.get("invoice_date") or frappe.utils.getdate("1900-01-01"),
            x.get("sales_invoice") or ""
        ))
        
        return columns, add_custom_total_row(rows), None, chart, None, True

    # ------------------------------------------------------------------
    # Vue PAR EMPLOYÉ - sans détail
    # ------------------------------------------------------------------
    if view_mode == "Par employé" and not details:
        grouped = {}

        for r in visible_ts_rows:
            rate_key = round(safe_float(r.get("hourly_cost")), 6)
            key = (r.get("project"), r.get("employee"), rate_key)

            if key not in grouped:
                grouped[key] = {
                    "project": r.get("project"),
                    "project_status": r.get("project_status"),
                    "sales_order": r.get("sales_order"),
                    "customer_name": r.get("customer_name"),
                    "ref_client": r.get("ref_client"),
                    "employee": r.get("employee"),
                    "hours": 0.0,
                    "hourly_cost": safe_float(r.get("hourly_cost")),
                    "employee_cost": 0.0,
                    "project_order_amount_total": safe_float(r.get("project_order_amount")),
                    "project_billed_amount_total": safe_float(r.get("project_billed_amount")),
                }

            grouped[key]["hours"] = grouped[key]["hours"] + safe_float(r.get("hours"))
            grouped[key]["employee_cost"] = grouped[key]["employee_cost"] + safe_float(r.get("employee_cost"))

        project_totals = {}
        for key in grouped:
            project = grouped[key]["project"]
            if project not in project_totals:
                project_totals[project] = {
                    "employee_cost_total": 0.0,
                    "hours_total": 0.0,
                    "line_count": 0,
                }
            project_totals[project]["employee_cost_total"] = project_totals[project]["employee_cost_total"] + safe_float(grouped[key]["employee_cost"])
            project_totals[project]["hours_total"] = project_totals[project]["hours_total"] + safe_float(grouped[key]["hours"])
            project_totals[project]["line_count"] = project_totals[project]["line_count"] + 1

        rows = []
        for key in grouped:
            row = grouped[key]
            totals = project_totals.get(row["project"], {})
            project_cost_total = safe_float(totals.get("employee_cost_total"))
            project_hours_total = safe_float(totals.get("hours_total"))
            line_count = totals.get("line_count") or 1

            ratio = 0
            if project_cost_total > 0:
                ratio = safe_float(row["employee_cost"]) / project_cost_total
            elif project_hours_total > 0:
                ratio = safe_float(row["hours"]) / project_hours_total
            else:
                ratio = 1.0 / line_count

            ordered_alloc = safe_float(row["project_order_amount_total"]) * ratio
            billed_alloc = safe_float(row["project_billed_amount_total"]) * ratio
            gross_margin = billed_alloc - row["employee_cost"]

            rows.append({
                "project": row["project"],
                "project_status": get_status_indicator(row["project_status"]),
                "sales_order": row["sales_order"],
                "customer_name": row["customer_name"],
                "ref_client": row["ref_client"],
                "employee": row["employee"],
                "hours": round(row["hours"], 3),
                "hourly_cost": round(row["hourly_cost"], 2),
                "employee_cost": round(row["employee_cost"], 2),
                "project_order_amount": round(ordered_alloc, 2),
                "project_billed_amount": round(billed_alloc, 2),
                "billed_percent": pct(row["project_billed_amount_total"], row["project_order_amount_total"]),
                "gross_margin": round(gross_margin, 2),
                "profit_percent": pct(gross_margin, billed_alloc),
            })

        rows.sort(key=lambda x: (x.get("project") or "", x.get("employee") or "", safe_float(x.get("hourly_cost"))))
        
        return columns, add_custom_total_row(rows), None, chart, None, True

    # ------------------------------------------------------------------
    # Vue PAR EMPLOYÉ - détail
    # ------------------------------------------------------------------
    rows = []

    groups = {}
    for r in visible_ts_rows:
        rate_key = round(safe_float(r.get("hourly_cost")), 6)
        key = (r.get("project"), r.get("employee"), rate_key)

        if key not in groups:
            groups[key] = {
                "project": r.get("project"),
                "project_status": r.get("project_status"),
                "employee": r.get("employee"),
                "hourly_cost": safe_float(r.get("hourly_cost")),
                "sales_order": r.get("sales_order"),
                "customer_name": r.get("customer_name"),
                "ref_client": r.get("ref_client"),
                "project_order_amount_total": safe_float(r.get("project_order_amount")),
                "project_billed_amount_total": safe_float(r.get("project_billed_amount")),
                "total_cost": 0.0,
                "total_hours": 0.0,
                "lines": []
            }

        groups[key]["total_cost"] = groups[key]["total_cost"] + safe_float(r.get("employee_cost"))
        groups[key]["total_hours"] = groups[key]["total_hours"] + safe_float(r.get("hours"))
        groups[key]["lines"].append(r)

    project_totals = {}
    for r in visible_ts_rows:
        project = r.get("project")
        if project not in project_totals:
            project_totals[project] = {
                "employee_cost_total": 0.0,
                "hours_total": 0.0
            }
        project_totals[project]["employee_cost_total"] = project_totals[project]["employee_cost_total"] + safe_float(r.get("employee_cost"))
        project_totals[project]["hours_total"] = project_totals[project]["hours_total"] + safe_float(r.get("hours"))

    for key in groups:
        group = groups[key]
        project = group["project"]

        project_total_cost = safe_float(project_totals.get(project, {}).get("employee_cost_total"))
        project_total_hours = safe_float(project_totals.get(project, {}).get("hours_total"))

        if project_total_cost > 0:
            group_ratio = safe_float(group["total_cost"]) / project_total_cost
        elif project_total_hours > 0:
            group_ratio = safe_float(group["total_hours"]) / project_total_hours
        else:
            group_ratio = 0

        group_order_alloc_total = safe_float(group["project_order_amount_total"]) * group_ratio
        group_billed_alloc_total = safe_float(group["project_billed_amount_total"]) * group_ratio

        line_count = len(group["lines"])

        for line in group["lines"]:
            line_cost = safe_float(line.get("employee_cost"))
            line_hours = safe_float(line.get("hours"))

            if safe_float(group["total_cost"]) > 0:
                line_ratio = line_cost / safe_float(group["total_cost"])
            elif safe_float(group["total_hours"]) > 0:
                line_ratio = line_hours / safe_float(group["total_hours"])
            else:
                line_ratio = 1.0 / line_count if line_count else 0

            order_alloc = group_order_alloc_total * line_ratio
            billed_alloc = group_billed_alloc_total * line_ratio
            gross_margin = billed_alloc - line_cost

            row = {
                "project": line.get("project"),
                "project_status": get_status_indicator(line.get("project_status")),
                "sales_order": line.get("sales_order"),
                "customer_name": line.get("customer_name"),
                "ref_client": line.get("ref_client"),
                "employee": line.get("employee"),
                "activity_type": line.get("activity_type"),
                "from_time": line.get("from_time"),
                "to_time": line.get("to_time"),
                "hours": round(line_hours, 3),
                "hourly_cost": round(safe_float(line.get("hourly_cost")), 2),
                "employee_cost": round(line_cost, 2),
                "project_order_amount": round(order_alloc, 2),
                "project_billed_amount": round(billed_alloc, 2),
                "billed_percent": pct(
                    safe_float(group["project_billed_amount_total"]),
                    safe_float(group["project_order_amount_total"])
                ),
                "gross_margin": round(gross_margin, 2),
                "profit_percent": pct(gross_margin, billed_alloc),
            }

            if show_unlinked or row.get("sales_order"):
                rows.append(row)

    rows.sort(key=lambda x: (
        x.get("project") or "",
        x.get("employee") or "",
        safe_float(x.get("hourly_cost")),
        x.get("from_time") or frappe.utils.getdate("1900-01-01")
    ))
    
    return columns, add_custom_total_row(rows), None, chart, None, True
