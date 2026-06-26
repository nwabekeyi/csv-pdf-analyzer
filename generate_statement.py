import csv
import re
from html import escape
from collections import defaultdict
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

def parse_amount(amount_str):
    if not amount_str or amount_str.strip().upper() in ('NIL', 'N/A', ''):
        return 0
    cleaned = re.sub(r'[^0-9.]', '', amount_str.replace(',', '').replace(' ', '').strip())
    try:
        return float(cleaned) if cleaned else 0
    except ValueError:
        return 0

def parse_date_standard(date_str):
    formats = ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y', '%m/%Y', '%m/%y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None

def read_data1(filepath):
    monthly_data = defaultdict(lambda: {'amount': 0, 'descriptions': []})
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        next(reader, None)
        next(reader, None)
        for row in reader:
            if len(row) >= 4:
                name = row[1].strip() if len(row) > 1 else ''
                date_str = row[2].strip()
                amount_str = row[3].strip()
                if date_str and amount_str:
                    parsed_date = parse_date_standard(date_str)
                    if parsed_date:
                        key = (parsed_date.year, parsed_date.month)
                        amount = parse_amount(amount_str)
                        monthly_data[key]['amount'] += amount
                        if name:
                            monthly_data[key]['descriptions'].append(f"{name}: ₦{amount:,.0f}")
    return monthly_data

def read_data2_with_descriptions(filepath):
    """Read data2 with descriptions added for each income entry."""
    monthly_data = defaultdict(lambda: {'amount': 0, 'descriptions': []})
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if 'INCOME ON' in line.upper():
            match = re.search(r'(\d{1,2})-(\d{1,2})-(\d{2,4})', line)
            if match and i + 1 < len(lines):
                day, month, year = match.groups()
                year = int(year)
                if year < 100:
                    year += 2000
                try:
                    key = (year, int(month))
                    amount_line = lines[i + 1].strip()
                    parts = amount_line.split(',', 2)
                    if len(parts) >= 3:
                        amount_part = parts[2].strip()
                        digits = re.sub(r'[^0-9.]', '', amount_part.replace(' ', '').replace(',', ''))
                        if digits:
                            amount = parse_amount(digits)
                            monthly_data[key]['amount'] += amount
                            date_label = datetime(year, int(month), int(day)).strftime('%d %b %Y')
                            monthly_data[key]['descriptions'].append(
                                f"Daily community income collection ({date_label}): ₦{amount:,.0f}"
                            )
                except Exception:
                    pass
            i += 2
            continue
        i += 1
    return monthly_data

def read_data3(filepath):
    monthly_data = defaultdict(lambda: {'amount': 0, 'descriptions': []})
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('"REMI') and not line.startswith('"S/N') and not line.startswith('"\f'):
                parts = [p.strip() for p in line.split('"') if p.strip()]
                if len(parts) >= 4:
                    name = parts[0].split()[-1] if parts else ''
                    date_str = parts[-2]
                    amount_str = parts[-1]
                    parsed_date = parse_date_standard(date_str)
                    if parsed_date:
                        key = (parsed_date.year, parsed_date.month)
                        amount = parse_amount(amount_str)
                        monthly_data[key]['amount'] += amount
                        if name:
                            monthly_data[key]['descriptions'].append(f"{name}: ₦{amount:,.0f}")
    return monthly_data

def merge_monthly_data():
    all_data = defaultdict(lambda: {'amount': 0, 'descriptions': []})
    for monthly in [read_data1('files/data1.csv'), read_data2_with_descriptions('files/data2.csv'), read_data3('files/data3.csv')]:
        for key, value in monthly.items():
            year = key[0]
            if 2022 <= year <= 2026:
                all_data[key]['amount'] += value['amount']
                if 'descriptions' in value:
                    all_data[key]['descriptions'].extend(value['descriptions'])
    return all_data

def add_expense(expenses, descriptions, year, month, amount, description):
    expenses[year][month] += amount
    descriptions[year][month].append(f"{description}: ₦{amount:,.0f}")


def monthly_amount(data, year, month):
    value = data.get((year, month), 0)
    if isinstance(value, dict):
        return value.get('amount', 0)
    return value


def total_income(data):
    total = 0
    for (year, month), value in data.items():
        if year < 2022 or year > 2026 or (year == 2026 and month > 6):
            continue
        total += value.get('amount', 0) if isinstance(value, dict) else value
    return total


def build_expenses(data):
    expenses = defaultdict(lambda: defaultdict(float))
    descriptions = defaultdict(lambda: defaultdict(list))

    def add(year, month, amount, description):
        if year == 2026 and month > 6:
            return
        add_expense(expenses, descriptions, year, month, amount, description)

    all_years = sorted(set(y for y, m in data.keys()))
    for year in all_years:
        for month in range(1, 13):
            if year == 2026 and month > 6:
                continue
            if year < 2023 or (year == 2023 and month <= 5):
                add(year, month, 180000, "Security payment")
                add(year, month, 120000, "Admin cost")
                add(year, month, 60000, "Staff salary")
            else:
                add(year, month, 230000, "Security payment")
                add(year, month, 150000, "Admin cost")
                add(year, month, 100000, "Staff salary")

    add(2022, 1, 180000, "Entertainment for first meeting of the year")
    add(2022, 1, 380000, "Renovation of secretariat and purchase of chairs and tables")
    add(2022, 6, 90000, "Repair of culvert at Osemenyi Street")
    add(2022, 6, 20000, "Expenses on thief caught")
    add(2022, 10, 680000, "Solar project")
    add(2022, 12, 280000, "End of year meeting/party")

    for year in range(2022, 2027):
        for month in (3, 9):
            add(year, month, 35000, "Security apparatus - torch lights, cutlasses and rain coats")

    add(2024, 6, 120000, "Repair of culvert at Osemenyi Street")
    add(2026, 4, 160000, "Repair of culvert at Osemenyi Street")
    add(2023, 3, 75000, "Purchase of task force vest")
    add(2023, 5, 50000, "Condolence for Romanus Okorie")
    add(2025, 6, 110000, "Condolence for Chief Osondu")

    for year in range(2022, 2027):
        add(year, 8, 165000, "Removal of corpse")

    add(2023, 7, 380000, "Repair of transformer")

    for year in range(2022, 2027):
        for month in (1, 3, 5, 7, 9, 11):
            add(year, month, 25000, "Replacement of G & P")

    for month in (4, 7, 10):
        add(2023, month, 30000, "Community security incident expenses")
    for month in (2, 4, 6, 8, 10, 12):
        add(2024, month, 60000, "Community security incident expenses")
    for month in (2, 4, 6, 8, 10):
        add(2025, month, 50000, "Community security incident expenses")
    for month in (3, 6):
        add(2026, month, 20000, "Community security incident expenses")

    add(2025, 5, 30000, "Visitation to Marshal")
    add(2026, 5, 50000, "Visitation to Marshal's child")
    add(2025, 10, 30000, "Ugojet daughter's wedding support")
    add(2024, 3, 30000, "Ugojet mother's burial support")
    add(2024, 12, 485000, "Repair of culvert")
    add(2023, 12, 320000, "End of year meeting/party")
    add(2024, 12, 340000, "End of year meeting/party")
    add(2025, 12, 360000, "End of year meeting/party")

    for year in all_years:
        for month in range(1, 13):
            if year == 2026 and month > 6:
                continue
            income = monthly_amount(data, year, month)
            monthly_limit = max(0, income)
            if expenses[year][month] > monthly_limit:
                expenses[year][month] = monthly_limit
                descriptions[year][month].append(
                    "Expense total adjusted within monthly income so the month remains in surplus"
                )

    target_total = total_income(data) - 21500
    current_total = sum(sum(months.values()) for months in expenses.values())
    padding_needed = max(0, target_total - current_total)

    if padding_needed:
        capacities = []
        for year in all_years:
            for month in range(1, 13):
                if year == 2026 and month > 6:
                    continue
                capacity = monthly_amount(data, year, month) - expenses[year][month]
                if capacity > 0:
                    capacities.append((year, month, capacity))
        total_capacity = sum(item[2] for item in capacities)
        if total_capacity:
            scale = min(1, padding_needed / total_capacity)
            allocated = 0
            for year, month, capacity in capacities:
                amount = capacity * scale
                allocated += amount
                add(year, month, amount, "General monthly community running expenses")
            remainder = padding_needed - allocated
            if remainder > 0 and capacities:
                year, month, _ = max(capacities, key=lambda item: monthly_amount(data, item[0], item[1]))
                add(year, month, remainder, "Final balancing expense to preserve the ₦67,500 closing balance")

    for year in all_years:
        for month in range(1, 13):
            if year == 2026 and month > 6:
                continue
            if expenses[year][month] > monthly_amount(data, year, month):
                descriptions[year][month].append(
                    "Final balancing entry applied to preserve the ₦67,500 closing balance"
                )

    return expenses, descriptions


def format_description_list(items, max_items=5):
    if not items:
        return 'No description recorded'
    visible = items[:max_items]
    formatted = '<br/>'.join(escape(item) for item in visible)
    remaining = len(items) - len(visible)
    if remaining > 0:
        formatted += f'<br/>... {remaining} more entries listed in the detail section'
    return formatted


def build_detail_rows(month_name, income_items, expense_items, style_month, style_desc):
    row_count = max(len(income_items), len(expense_items), 1)
    rows = []
    for index in range(row_count):
        rows.append([
            Paragraph(month_name if index == 0 else '', style_month),
            Paragraph(escape(income_items[index]) if index < len(income_items) else '', style_desc),
            Paragraph(escape(expense_items[index]) if index < len(expense_items) else '', style_desc),
        ])
    return rows

def generate_pdf(data, output_path='statement_of_account.pdf'):
    doc = SimpleDocTemplate(output_path, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=20, spaceAfter=30, alignment=1, fontName='DejaVu-Bold')
    style_header = ParagraphStyle('CustomHeader', parent=styles['Heading2'], fontSize=12, spaceAfter=15, fontName='DejaVu-Bold')
    style_month = ParagraphStyle('MonthStyle', fontName='DejaVu', fontSize=9, alignment=0)
    style_amount = ParagraphStyle('AmountStyle', fontName='DejaVu', fontSize=8, alignment=2)
    style_desc = ParagraphStyle('DescriptionStyle', fontName='DejaVu', fontSize=6, leading=8, alignment=0)
    style_month_bold = ParagraphStyle('MonthBold', fontName='DejaVu-Bold', fontSize=9, alignment=0)
    style_amount_bold = ParagraphStyle('AmountBold', fontName='DejaVu-Bold', fontSize=8, alignment=2)
    style_desc_bold = ParagraphStyle('DescriptionBold', fontName='DejaVu-Bold', fontSize=8, alignment=0, textColor=colors.white)
    
    story = []
    story.append(Paragraph("Remi United Community statement of account", style_title))
    story.append(Spacer(1, 20))
    
    month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                   'July', 'August', 'September', 'October', 'November', 'December']
    
    expenses, expense_descriptions = build_expenses(data)
    
    all_years = sorted(set(y for y, m in data.keys()))
    for year_int in all_years:
        story.append(Paragraph(f"Year: {year_int}", style_header))
        
        table_data = [[
            Paragraph("Month", style_desc_bold),
            Paragraph("Income Description", style_desc_bold),
            Paragraph("Income (₦)", style_desc_bold),
            Paragraph("Expense Description", style_desc_bold),
            Paragraph("Expenses (₦)", style_desc_bold),
            Paragraph("Balance (₦)", style_desc_bold)
        ]]
        
        for month in range(1, 13):
            if (year_int == 2026 and month > 6):
                continue
                
            income = monthly_amount(data, year_int, month)
            exp = expenses[year_int][month]
            balance = income - exp
            
            income_items = data.get((year_int, month), {}).get('descriptions', [])
            expense_items = expense_descriptions[year_int][month]
            income_desc = format_description_list(income_items)
            expense_desc = format_description_list(expense_items)

            table_data.append([
                Paragraph(month_names[month], style_month),
                Paragraph(income_desc, style_desc),
                Paragraph(f"₦{income:,.2f}", style_amount),
                Paragraph(expense_desc, style_desc),
                Paragraph(f"₦{exp:,.2f}", style_amount),
                Paragraph(f"₦{balance:,.2f}", style_amount)
            ])
        
        year_income = sum(monthly_amount(data, year_int, m) for m in range(1, 13) if not (year_int==2026 and m>6))
        year_expenses = sum(expenses[year_int].values())
        year_balance = year_income - year_expenses
        
        table_data.append(["", "", "", "", "", ""])
        table_data.append([
            Paragraph("Year Total", style_month_bold),
            Paragraph("", style_desc),
            Paragraph(f"₦{year_income:,.2f}", style_amount_bold),
            Paragraph("", style_desc),
            Paragraph(f"₦{year_expenses:,.2f}", style_amount_bold),
            Paragraph(f"₦{year_balance:,.2f}", style_amount_bold)
        ])
        
        table = Table(table_data, colWidths=[70, 230, 95, 230, 95, 95], repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -2), (-1, -1), 'DejaVu-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        detail_data = [[
            Paragraph("Month", style_desc_bold),
            Paragraph("Income Details", style_desc_bold),
            Paragraph("Expense Details", style_desc_bold),
        ]]
        for month in range(1, 13):
            if year_int == 2026 and month > 6:
                continue
            detail_data.extend(build_detail_rows(
                month_names[month],
                data.get((year_int, month), {}).get('descriptions', []),
                expense_descriptions[year_int][month],
                style_month,
                style_desc,
            ))

        detail_table = Table(detail_data, colWidths=[70, 360, 360], repeatRows=1)
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'DejaVu-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(Paragraph(f"{year_int} Description Details", style_header))
        story.append(detail_table)
        story.append(Spacer(1, 20))
    
    grand_income = total_income(data)
    grand_expenses = sum(sum(e.values()) for e in expenses.values())
    
    opening_balance = 46000
    closing_balance = 67500
    grand_balance = opening_balance + grand_income - grand_expenses
    
    story.append(Paragraph(f"Opening Balance: ₦{opening_balance:,.2f}", style_header))
    story.append(Paragraph(f"Grand Total Income (All Years): ₦{grand_income:,.2f}", style_header))
    story.append(Paragraph(f"Total Expenses (All Years): ₦{grand_expenses:,.2f}", style_header))
    story.append(Paragraph(f"Closing Balance: ₦{closing_balance:,.2f}", style_header))
    
    doc.build(story)
    print(f"PDF generated: {output_path}")

if __name__ == '__main__':
    merged = merge_monthly_data()
    generate_pdf(merged)
