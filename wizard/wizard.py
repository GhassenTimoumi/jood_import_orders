from datetime import datetime, time
import xlrd, math
import logging
import tempfile
import binascii
from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

try:
	import csv
except ImportError:
	_logger.debug('Cannot `import csv`.')
try:
	import xlwt
except ImportError:
	_logger.debug('Cannot `import xlwt`.')
try:
	import cStringIO
except ImportError:
	_logger.debug('Cannot `import cStringIO`.')

try:
	import base64
except ImportError:
	_logger.debug('Cannot `import base64`.')

DEFAULT_SERVER_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_SERVER_TIME_FORMAT = "%H:%M:%S"
DEFAULT_SERVER_DATETIME_FORMAT = "%s %s" % (DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT)
from pytz import timezone, UTC
tz = 'Asia/Riyadh'



class ImportHrAttendanceWizard(models.TransientModel):
    _name = 'jood.import'

    file = fields.Binary('File')
    filename = fields.Char('Filename')
    branch_id = fields.Many2one('res.company', 'Branch', required=True)

    def import_file(self):
        if not self.file:
            raise ValidationError(_("Please Upload File to Import Donations !"))

        try:
            file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            file.write(binascii.a2b_base64(self.file))
            file.seek(0)
            workbook = xlrd.open_workbook(file.name)
            sheet = workbook.sheet_by_index(0)
        except Exception:
            raise ValidationError(_("Please Select Valid File Format !"))

        list = []
        for row_no in range(1, sheet.nrows):
            dt = datetime(*xlrd.xldate.xldate_as_tuple(sheet.cell(row_no, 11).value, workbook.datemode))
            year, month, day, hour, minute, second = xlrd.xldate_as_tuple(sheet.cell(row_no, 11).value, workbook.datemode)

            vals = {
                'number': sheet.cell(row_no, 0).value,
                'partner': sheet.cell(row_no, 1).value,
                'mobile': str(int(sheet.cell(row_no, 2).value)),
                'project_title': sheet.cell(row_no, 3).value,
                'title': sheet.cell(row_no, 4).value,
                'categ': sheet.cell(row_no, 5).value,
                'type': sheet.cell(row_no, 6).value,
                'amount': sheet.cell(row_no, 8).value,
                'payment_method': sheet.cell(row_no, 9).value,
                'bank_acc': sheet.cell(row_no, 10).value,
                'date': timezone(tz).localize(
                        datetime.combine(dt, time(int(hour), int(minute), int(second)))).astimezone(UTC).replace(tzinfo=None),
                'state': sheet.cell(row_no, 12).value,
            }
            list.append(vals)
        self.create_donations(list)

    def create_donations(self, list):
        Donation = self.env['donation.donation']
        for line in list:
            partner = self.env['res.partner'].search([('name', 'like', line['partner']), ('mobile', '=', str(int(line['mobile'])))])
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': line['partner'] if line['partner'] else line['mobile'],
                    'mobile': str(int(line['mobile'])),
                    'is_donor': True
                })
            payment_method_type = 'cash'
            if line['payment_method'] == 'بطاقة ائتمانية':
                payment_method_type = 'card'
            instruction = ''
            if len(line['project_title'].split(' / ')) == 1:
                product = self.env['product.product'].search([('name', 'like', line['project_title'])], limit=1)
            else:
                product = self.env['product.product'].search([('name', 'like', line['project_title'].split(' / ')[0])], limit=1)
                instruction = line['project_title'].split(' / ')[1]

            if not product:
                product = self.env['product.product'].search([('name', 'like', 'الصدقه النقديه العامه')], limit=1)
            Donation.create({
                'donation_date': line['date'],
                'partner_id': partner.id,
                'branch_id': self.branch_id.id,
                'donation_type': 'money',
                'payment_method_type': payment_method_type,
                'donation_line':[(0, 0, {
                    'product_id': product.id,
                    'product_qty': 1,
                    'unit_price': line['amount'],
                    'instruction': instruction
                })]
            })
