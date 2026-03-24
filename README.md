# symbiose_reports

Custom Frappe/ERPNext app for Symbiose custom Script Reports on ERPNext v15.

Included reports:
- Asset Logbook
- Project – Employee costs

## Notes
- Built for ERPNext/Frappe v15.
- These reports read existing data from the current MariaDB database. If your v13 data was migrated to v15 and the required tables/fields still exist, the reports can reuse that data.
- Several custom fields are referenced by `Asset Logbook` (`etalon_1`..`etalon_24`, `work_order`, `tag_sap`, `ticket_sodexo_link`, `infos_complémentaires`, `info_complémentaire_project_id`). Verify they still exist in v15.
- `Project – Employee costs` assumes a child table `tabSalary Structure Assignment Details` with fields `base`, `from_date`, `end_date`.

## Suggested install flow
1. Add the app to your custom image or mount it into the bench.
2. Install it on DEV first:
   ```bash
   bench get-app /path/to/symbiose_reports
   bench --site dev-symbiose.caconsultants.be install-app symbiose_reports
   bench --site dev-symbiose.caconsultants.be migrate
   bench --site dev-symbiose.caconsultants.be clear-cache
   ```
3. Test the reports in the UI.
4. Promote to production only after DEV validation.

## Docker image approach
Recommended: create a custom image based on `frappe/erpnext:v15.82.1`, copy this repo into `/home/frappe/frappe-bench/apps/`, install the app, then rebuild.
