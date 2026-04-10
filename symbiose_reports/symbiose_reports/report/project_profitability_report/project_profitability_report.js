frappe.query_reports["Project Profitability Report"] = {
    filters: [
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project",
        },
        {
            fieldname: "employee",
            label: __("Employee"),
            fieldtype: "Link",
            options: "Employee",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start(
                frappe.datetime.add_months(frappe.datetime.get_today(), -6)
            ),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end(frappe.datetime.get_today()),
        },
        {
            fieldname: "details",
            label: __("Details"),
            fieldtype: "Check",
            default: 0,
        },
    ],
};
