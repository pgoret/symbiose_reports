frappe.query_reports["Asset Logbook"] = {
    filters: [
        {
            fieldname: "module",
            label: __("Module"),
            fieldtype: "MultiSelect",
            options: ["Timesheet", "Asset Maintenance", "Asset Repair"],
            default: "Timesheet,Asset Maintenance,Asset Repair,",
        },
        {
            fieldname: "asset_name",
            label: __("Asset Name"),
            fieldtype: "Link",
            options: "Asset",
        },
        {
            fieldname: "doc_name",
            label: __("Référence"),
            fieldtype: "Data",
        },
        {
            fieldname: "start_date",
            label: __("Start Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_days(frappe.datetime.nowdate(), -160),
        },
        {
            fieldname: "end_date",
            label: __("End Date"),
            fieldtype: "Date",
            default: frappe.datetime.nowdate(),
        },
        {
            fieldname: "asset_category",
            label: __("Asset Category"),
            fieldtype: "Select",
            options: ["", "Etalons", "Non étalon"],
        },
        {
            fieldname: "item_group",
            label: __("Item Group"),
            fieldtype: "Link",
            options: "Item Group",
        },
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
    ],
};
