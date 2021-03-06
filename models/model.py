# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import models, api


class ResPartner(models.Model):

    _inherit = 'res.partner'

    @api.constrains('vat', 'country_id')
    def check_vat(self):
        if self.env.context.get('company_id'):
            company = self.env['res.company'].browse(
                self.env.context['company_id'])
        else:
            company = self.env.company
        eu_countries = self.env.ref('base.europe').country_ids
        for partner in self:
            if not partner.vat:
                continue

            if company.vat_check_vies and partner.commercial_partner_id.country_id in eu_countries:
                # force full VIES online check
                check_func = self.vies_vat_check
            else:
                # quick and partial off-line checksum validation
                check_func = self.simple_vat_check

            failed_check = False
            # check with country code as prefix of the TIN
            vat_country_code, vat_number = self._split_vat(partner.vat)
            vat_guessed_country = self.env['res.country'].search(
                [('code', '=', vat_country_code.upper())])
            if vat_guessed_country:
                failed_check = not check_func(vat_country_code, vat_number)

            # if fails, check with country code from country
            partner_country_code = partner.commercial_partner_id.country_id.code
            if (not vat_guessed_country or failed_check) and partner_country_code:
                failed_check = not check_func(
                    partner_country_code.lower(), partner.vat)

            # We allow any number if it doesn't start with a country code and the partner has no country.
            # This is necessary to support an ORM limitation: setting vat and country_id together on a company
            # triggers two distinct write on res.partner, one for each field, both triggering this constraint.
            # If vat is set before country_id, the constraint must not break.

            if failed_check and company.vat_check_vies:
                country_code = partner_country_code or vat_country_code
                msg = partner._construct_constraint_msg(
                    country_code.lower() if country_code else None)
                raise ValidationError(msg)
