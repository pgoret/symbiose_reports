frappe.query_reports["Project Profitability Report"] = {
    filters: [
        {
            fieldname: "view_mode",
            label: "View Mode",
            fieldtype: "Select",
            options: "\nPar projet\nPar employé",
            default: "Par projet",
            reqd: 1,
            on_change: function() { frappe.query_report.refresh(); }
        },
        {
            fieldname: "project",
            label: "Project",
            fieldtype: "Link",
            options: "Project",
            on_change: function() { frappe.query_report.refresh(); }
        },
        // NOUVEAU FILTRE : Statut du Projet
        {
            fieldname: "project_status",
            label: "Statut Projet",
            fieldtype: "Select",
            options: "\nOpen\nCompleted\nCancelled",
            on_change: function() { frappe.query_report.refresh(); }
        },
        {
            fieldname: "employee",
            label: "Employee",
            fieldtype: "Link",
            options: "Employee",
            depends_on: 'eval:doc.view_mode=="Par employé"',
            on_change: function() { frappe.query_report.refresh(); }
        },
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.month_start(),
            on_change: function() { frappe.query_report.refresh(); }
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.month_end(),
            on_change: function() { frappe.query_report.refresh(); }
        },
        {
            fieldname: "details",
            label: "Details",
            fieldtype: "Check",
            default: 0,
            on_change: function() { frappe.query_report.refresh(); }
        },
        {
            fieldname: "billing_scope",
            label: "Billing Scope",
            fieldtype: "Select",
            options: "\nPériode filtrée\nHistorique complet",
            default: "Période filtrée",
            depends_on: 'eval:doc.details==1',
            on_change: function() { frappe.query_report.refresh(); }
        },
        {
            fieldname: "show_unlinked",
            label: "Afficher liaisons incomplètes",
            fieldtype: "Check",
            default: 0,
            on_change: function() { frappe.query_report.refresh(); }
        }
    ],
    // FORMATAGE DYNAMIQUE
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (data && data.project !== "TOTAL GLOBAL") {
            if (column.fieldname == "hourly_cost" && (!data.hourly_cost || data.hourly_cost === 0)) {
                value = "<span style='color:red; font-weight:bold;'>⚠️ Manquant</span>";
            }
            if (column.fieldname == "sales_order" || column.fieldname == "sales_invoice") {
                if (!data[column.fieldname]) {
                    value = "<span style='color:#ff8a65; font-style:italic;'>Non lié</span>";
                }
            }
        }

        if (column.fieldname == "gross_margin" || column.fieldname == "profit_percent") {
            if (data && data[column.fieldname] < 0) {
                value = "<span style='color:red; font-weight:bold;'>" + value + "</span>";
            } else if (data && data[column.fieldname] > 0) {
                value = "<span style='color:green; font-weight:bold;'>" + value + "</span>";
            }
        }
        
        return value;
    }
};