from odoo import models


class DonationLine(models.Model):
    _inherit = 'donation.line'

    def name_get(self):
        res = []
        for line in self:
            if line.instruction:
                res.append((line.id, '%s' % (line.instruction)))
            else:
                res.append((line.id, line.product_id.name))
        return res
