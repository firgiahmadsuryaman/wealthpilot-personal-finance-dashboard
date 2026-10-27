import unittest
from app.main import _calculate_portfolio


def tx(i, tx_type, asset, quantity=0, unit_price=0, currency='IDR', fx_rate=1, fee_idr=0, amount_idr=0):
    return {
        'id': i, 'tx_type': tx_type, 'asset': asset,
        'quantity': quantity, 'unit_price': unit_price,
        'currency': currency, 'fx_rate': fx_rate,
        'fee_idr': fee_idr, 'amount_idr': amount_idr,
    }


class PortfolioAccountingTests(unittest.TestCase):
    def setUp(self):
        self.gold = {'customer_buy_idr_g': 1_900_000, 'customer_sell_idr_g': 1_800_000}
        self.no_spy = {'status': 'not_configured', 'price': None}

    def test_modal_and_market_value_are_separate(self):
        transactions = [
            tx(1, 'DEPOSIT', 'CASH', amount_idr=10_000_000),
            tx(2, 'BUY', 'GOLD', quantity=5, unit_price=1_900_000),
        ]
        p = _calculate_portfolio(transactions, self.gold, self.no_spy, None)
        self.assertEqual(p['net_contributions_idr'], 10_000_000)
        self.assertEqual(p['cash_balance_idr'], 500_000)
        self.assertEqual(p['portfolio_value_idr'], 9_500_000)
        self.assertEqual(p['total_pnl_idr'], -500_000)

    def test_missing_market_price_never_becomes_zero_valuation(self):
        transactions = [tx(1, 'OPENING', 'GOLD', quantity=5, unit_price=1_900_000)]
        p = _calculate_portfolio(transactions, None, self.no_spy, None)
        self.assertFalse(p['valuation_complete'])
        self.assertIsNone(p['portfolio_value_idr'])
        self.assertIsNone(p['total_pnl_idr'])


    def test_total_pnl_matches_realized_plus_unrealized_pnl(self):
        transactions = [
            tx(1, 'DEPOSIT', 'CASH', amount_idr=10_000_000),
            tx(2, 'BUY', 'GOLD', quantity=2, unit_price=1_500_000),
            tx(3, 'BUY', 'GOLD', quantity=2, unit_price=1_700_000),
            tx(4, 'SELL', 'GOLD', quantity=1, unit_price=1_800_000, fee_idr=1_000),
        ]
        p = _calculate_portfolio(transactions, self.gold, self.no_spy, None)
        self.assertEqual(p['total_pnl_idr'], 799_000)
        self.assertEqual(p['realized_pnl_idr'], 199_000)
        self.assertEqual(p['unrealized_pnl_idr'], 600_000)
        self.assertEqual(p['total_pnl_idr'], p['realized_pnl_idr'] + p['unrealized_pnl_idr'])

    def test_sell_uses_weighted_average_basis(self):
        transactions = [
            tx(1, 'DEPOSIT', 'CASH', amount_idr=10_000_000),
            tx(2, 'BUY', 'GOLD', quantity=2, unit_price=1_500_000),
            tx(3, 'BUY', 'GOLD', quantity=2, unit_price=1_700_000),
            tx(4, 'SELL', 'GOLD', quantity=1, unit_price=1_800_000, fee_idr=1_000),
        ]
        p = _calculate_portfolio(transactions, self.gold, self.no_spy, None)
        self.assertAlmostEqual(p['holdings']['GOLD']['quantity'], 3)
        self.assertAlmostEqual(p['holdings']['GOLD']['cost_basis_idr'], 4_800_000)
        self.assertAlmostEqual(p['realized_pnl_idr'], 199_000)
        self.assertAlmostEqual(p['holdings']['GOLD']['unrealized_pnl_idr'], 600_000)


if __name__ == '__main__':
    unittest.main()
