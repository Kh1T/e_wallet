"""Statement date and ledger calculations for wallet account statements."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from wallet.models import Transaction, Transfer


VALID_STATEMENT_PERIODS = {'this_month', '1_month', '3_months', '6_months'}
ZERO = Decimal('0.00')


@dataclass
class StatementEntry:
    created_at: datetime
    description: str
    reference: str
    money_in: Decimal
    money_out: Decimal
    sequence: int
    balance: Decimal = ZERO


def _subtract_months(value, months):
    """Return the same day in a previous month, clamped to that month's end."""
    month_index = value.month - months
    year = value.year + (month_index - 1) // 12
    month = (month_index - 1) % 12 + 1
    return value.replace(day=min(value.day, monthrange(year, month)[1]))


def get_statement_period(period, now=None):
    """Return an inclusive-aware [start, end] range for an allowed period."""
    if period not in VALID_STATEMENT_PERIODS:
        raise ValueError('Unsupported statement period.')

    now = now or timezone.now()
    if period == 'this_month':
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        months = int(period.split('_')[0])
        start = _subtract_months(now, months)
    return start, now


def _transaction_direction(transaction):
    """Classify transaction types that affect a wallet's balance."""
    if transaction.transaction_type in {'topup', 'bill_payment_received'}:
        return 'in'
    if transaction.transaction_type in {'transfer', 'bill_payment', 'withdrawal'}:
        return 'out'
    return None


def _wallet_entries(wallet, end):
    """Return all completed wallet ledger events through ``end`` in time order.

    Incoming P2P transfers do not have a Transaction owned by the recipient
    wallet in this application, so they are included from Transfer separately.
    """
    entries = []
    transactions = (
        Transaction.objects.filter(wallet=wallet, status='completed', created_at__lte=end)
        .order_by('created_at', 'id')
    )
    for tx in transactions:
        direction = _transaction_direction(tx)
        if direction is None:
            continue
        entries.append(StatementEntry(
            created_at=tx.created_at,
            description=tx.description or tx.transaction_type.replace('_', ' ').title(),
            reference=tx.reference or '',
            money_in=tx.amount if direction == 'in' else ZERO,
            money_out=tx.amount if direction == 'out' else ZERO,
            sequence=tx.id * 2,
        ))

    incoming_transfers = (
        Transfer.objects.filter(
            receiver_wallet=wallet,
            transaction__status='completed',
            created_at__lte=end,
        )
        .select_related('transaction', 'sender_wallet__user')
        .order_by('created_at', 'id')
    )
    for transfer in incoming_transfers:
        sender_name = transfer.sender_wallet.user.full_name or transfer.sender_wallet.wallet_number
        entries.append(StatementEntry(
            created_at=transfer.created_at,
            description=transfer.transaction.description or f'Received from {sender_name}',
            reference=transfer.transaction.reference or '',
            money_in=transfer.transaction.amount,
            money_out=ZERO,
            sequence=transfer.id * 2 + 1,
        ))

    return sorted(entries, key=lambda entry: (entry.created_at, entry.sequence))


def build_statement(wallet, start, end):
    """Build a statement using only server-side wallet and ledger data.

    Wallets store their current balance rather than a per-transaction running
    balance.  The balance at the selected end date is reconstructed by removing
    every completed ledger movement after that date from the current balance.
    """
    entries_through_end = _wallet_entries(wallet, end)
    all_entries = _wallet_entries(wallet, timezone.now())
    movements_after_end = sum(
        (entry.money_in - entry.money_out for entry in all_entries if entry.created_at > end),
        ZERO,
    )
    ending_balance = wallet.balance - movements_after_end
    period_entries = [entry for entry in entries_through_end if entry.created_at >= start]
    period_net = sum((entry.money_in - entry.money_out for entry in period_entries), ZERO)
    opening_balance = ending_balance - period_net

    running_balance = opening_balance
    for entry in period_entries:
        running_balance += entry.money_in - entry.money_out
        entry.balance = running_balance

    return {
        'start': start,
        'end': end,
        'opening_balance': opening_balance,
        'total_money_in': sum((entry.money_in for entry in period_entries), ZERO),
        'total_money_out': sum((entry.money_out for entry in period_entries), ZERO),
        'ending_balance': ending_balance,
        'entries': period_entries,
    }
