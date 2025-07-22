{
    "name": "Zoho Timesheet Synchronization",
    "summary": "Synchronize timesheets with Zoho Suite (Mail, Cliq, WorkDrive)",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Your Company",
    "website": "https://github.com/your-repo/timesheet",
    "depends": ["hr_timesheet", "project"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/project_project_view.xml",
        "views/project_task_view.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}