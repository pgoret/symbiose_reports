frappe.query_reports["Project Employee costs"] = {
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
            default: moment().subtract(6, "month").startOf("month").format("YYYY-MM-DD"),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: moment().endOf("month").format("YYYY-MM-DD"),
        },
        {
            fieldname: "details",
            label: __("Details"),
            fieldtype: "Check",
            default: 0,
        },
    ],
};
