"""ReportLab rendering for wallet account statements."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


def _money(amount, currency):
    return f'{currency} {amount:,.2f}'


def _footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#CBD5E1'))
    canvas.line(document.leftMargin, 13 * mm, A4[0] - document.rightMargin, 13 * mm)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.HexColor('#64748B'))
    canvas.drawString(document.leftMargin, 8 * mm, 'NexusPay · Account Statement')
    canvas.drawRightString(A4[0] - document.rightMargin, 8 * mm, f'Page {document.page}')
    canvas.restoreState()


def generate_statement_pdf(wallet, user, verification, statement):
    """Return a paginated bank-style statement PDF as bytes."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=17 * mm, bottomMargin=20 * mm,
        title='NexusPay Account Statement', author='NexusPay',
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle('StatementTitle', parent=styles['Heading1'], fontName='Helvetica-Bold',
                           fontSize=22, leading=26, textColor=colors.HexColor('#0F172A'), alignment=TA_RIGHT)
    subtitle = ParagraphStyle('StatementSubtitle', parent=styles['Normal'], fontSize=10,
                              leading=14, textColor=colors.HexColor('#475569'), alignment=TA_RIGHT)
    section = ParagraphStyle('StatementSection', parent=styles['Heading2'], fontName='Helvetica-Bold',
                             fontSize=10, leading=14, textColor=colors.HexColor('#0F172A'), spaceBefore=12, spaceAfter=5)
    normal = ParagraphStyle('StatementNormal', parent=styles['Normal'], fontSize=9, leading=13,
                            textColor=colors.HexColor('#334155'))
    small = ParagraphStyle('StatementSmall', parent=normal, fontSize=8, leading=11)
    right = ParagraphStyle('StatementRight', parent=normal, alignment=TA_RIGHT)

    period = f"{statement['start']:%b %d, %Y} – {statement['end']:%b %d, %Y}"
    address = escape(verification.address if verification and verification.address else 'Not provided')
    holder_name = escape(user.full_name or user.get_full_name() or user.username)
    wallet_number = escape(wallet.wallet_number)
    story = [
        Table([[Paragraph('<b>NEXUS<span color="#2563EB">PAY</span></b>', ParagraphStyle('Brand', parent=styles['Normal'], fontSize=19, textColor=colors.HexColor('#0F172A'))),
                [Paragraph('ACCOUNT STATEMENT', title), Paragraph(f'For period: {period}', subtitle)]]],
              colWidths=[78 * mm, 100 * mm], style=[('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]),
        Spacer(1, 9 * mm), HRFlowable(width='100%', thickness=0.7, color=colors.HexColor('#CBD5E1')),
        Spacer(1, 5 * mm),
        Table([
            [Paragraph('<b>CUSTOMER INFORMATION</b>', section), Paragraph('<b>ACCOUNT DETAILS</b>', section)],
            [Paragraph(f'<b>{holder_name}</b><br/>{address}', normal),
             Paragraph(f'Account Holder Name&nbsp;&nbsp;&nbsp; {holder_name}<br/>Account No.&nbsp;&nbsp;&nbsp; {wallet_number}<br/>Account Currency&nbsp;&nbsp;&nbsp; {wallet.currency}', normal)],
        ], colWidths=[86 * mm, 92 * mm], style=[('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0)]),
        Paragraph('ACCOUNT SUMMARY', section),
    ]
    summary_rows = [
        ['Opening Balance', _money(statement['opening_balance'], wallet.currency)],
        ['Total Money In', _money(statement['total_money_in'], wallet.currency)],
        ['Total Money Out', _money(statement['total_money_out'], wallet.currency)],
        ['<b>Ending Balance</b>', f"<b>{_money(statement['ending_balance'], wallet.currency)}</b>"],
    ]
    summary = Table([[Paragraph(label, normal), Paragraph(value, right)] for label, value in summary_rows], colWidths=[86 * mm, 92 * mm])
    summary.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, 0), 0.7, colors.HexColor('#94A3B8')), ('LINEBELOW', (0, -1), (-1, -1), 0.7, colors.HexColor('#94A3B8')), ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3)]))
    story.extend([summary, Paragraph('ACCOUNT ACTIVITY', section)])
    rows = [[Paragraph('<b>Date</b>', small), Paragraph('<b>Transaction Details</b>', small), Paragraph('<b>Money In</b>', small), Paragraph('<b>Money Out</b>', small), Paragraph('<b>Balance</b>', small)]]
    for entry in statement['entries']:
        details = escape(entry.description)
        if entry.reference:
            details += f'<br/><font color="#64748B">{escape(entry.reference)}</font>'
        rows.append([
            Paragraph(entry.created_at.strftime('%b %d, %Y<br/>%I:%M %p'), small),
            Paragraph(details, small),
            Paragraph(_money(entry.money_in, wallet.currency) if entry.money_in else '—', small),
            Paragraph(_money(entry.money_out, wallet.currency) if entry.money_out else '—', small),
            Paragraph(_money(entry.balance, wallet.currency), small),
        ])
    if not statement['entries']:
        rows.append([Paragraph('No transactions during this period.', normal), '', '', '', ''])
    activity = Table(rows, colWidths=[28 * mm, 67 * mm, 28 * mm, 28 * mm, 27 * mm], repeatRows=1)
    activity.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E2E8F0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#CBD5E1')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
    ]))
    story.append(activity)
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
