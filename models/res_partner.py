import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    credit_amount = fields.Monetary(compute="_compute_client_credits_amount")

    def action_view_payments_in_favor(self):
        domain = self._payment_balance_customer_domain()

        domain.append(("balance", "<", 0.0))

        move_lines = self.env["account.move.line"].search(domain)

        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_account_payments"
        )

        action["domain"] = [("id", "in", move_lines.payment_id.ids)]
        return action

    def _compute_client_credits_amount(self):
        for partner in self:
            partner.credit_amount = 0
            customer_credit = 0

            domain = self._payment_balance_customer_domain()

            domain.append(("balance", "<", 0.0))

            currency = self.env.company.currency_id

            for line in self.env["account.move.line"].search(domain):

                if line.currency_id == self.env.company.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = line.company_currency_id._convert(
                        abs(line.amount_residual),
                        currency,
                        self.env.company,
                        line.date,
                    )

                if currency.is_zero(amount):
                    continue

                customer_credit += amount

            partner.credit_amount = customer_credit

    def _payment_balance_customer_domain(self):
        self.ensure_one()

        domain = [
            (
                "account_id.account_type",
                "in",
                ("asset_receivable", "liability_payable"),
            ),
            ("parent_state", "=", "posted"),
            ("partner_id", "=", self.id),
            ("reconciled", "=", False),
            "|",
            ("amount_residual", "!=", 0.0),
            ("amount_residual_currency", "!=", 0.0),
        ]

        return domain
