app_name = "symbiose_reports"
app_title = "Symbiose Reports"
app_publisher = "CAC Consultants"
app_description = "Custom Script Reports for Symbiose on ERPNext"
app_email = "support@caconsultants.be"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

permission_query_conditions = {
    "Diffusion": "symbiose_reports.permissions.diffusion_query_conditions",
}

has_permission = {
    "Diffusion": "symbiose_reports.permissions.diffusion_has_permission",
}
