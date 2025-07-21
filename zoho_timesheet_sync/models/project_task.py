from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = "project.task"

    x_priority_score = fields.Integer("Score Priorité")
    x_last_sync = fields.Datetime("Dernière synchro")