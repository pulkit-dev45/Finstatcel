import os
import logging
import concurrent.futures
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.http import HttpResponse, Http404, JsonResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from .forms import StatementUploadForm, RegisterForm, LoginForm
from django.contrib.auth.forms import UserCreationForm
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from .models import StatementUpload
from .forms import StatementUploadForm
from .statement_parser import parse_statement_pdf

logger = logging.getLogger(__name__)


def home(request):
    return render(request, 'converter/home.html')


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'redirect': reverse('upload')})
            messages.success(request, 'Account created successfully!')
            return redirect('upload')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'converter/profile.html')

COLUMN_WIDTHS = {
    'A': 16,
    'B': 50,
    'C': 18,
    'D': 18,
    'E': 18,
}


def _style_excel(ws):
    header_font = Font(name='Calibri', bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='2F5496', end_color='2F5496', fill_type='solid')
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin'),
    )

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border

    for col_letter, width in COLUMN_WIDTHS.items():
        ws.column_dimensions[col_letter].width = width

    data_font = Font(name='Calibri', size=10)
    data_alignment = Alignment(vertical='center', wrap_text=True)
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, max_col=5):
        for cell in row:
            cell.font = data_font
            cell.alignment = data_alignment
            cell.border = thin_border

    ws.row_dimensions[1].height = 25


@login_required
def upload_statement(request):
    if request.method == 'POST':
        form = StatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            bank = form.cleaned_data.get('bank_name', 'auto')
            upload = StatementUpload(pdf_file=form.cleaned_data['pdf_file'])
            upload.save()
            try:
                pdf_path = upload.pdf_file.path
                logger.info(f"Processing PDF ({bank}): {pdf_path}")
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(parse_statement_pdf, pdf_path, bank)
                    try:
                        df = future.result(timeout=settings.PDF_PROCESSING_TIMEOUT)
                    except concurrent.futures.TimeoutError:
                        logger.error("PDF parsing timed out")
                        os.remove(pdf_path)
                        upload.delete()
                        messages.error(request, 'PDF processing timed out. The file may be too large or in an unsupported format.')
                        return render(request, 'converter/upload.html', {'form': StatementUploadForm()})
                if df.empty:
                    os.remove(pdf_path)
                    upload.delete()
                    messages.error(request, 'Could not extract any transaction data from this PDF.')
                    return render(request, 'converter/upload.html', {'form': StatementUploadForm()})

                excel_filename = f"{upload.filename()}_converted.xlsx"
                excel_path = os.path.join(settings.MEDIA_ROOT, 'exports', excel_filename)
                os.makedirs(os.path.dirname(excel_path), exist_ok=True)

                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = 'Statement'

                headers = ['Date', 'Particulars', 'Withdrawn amount', 'Deposit amount', 'Balance']
                ws.append(headers)

                for _, row in df.iterrows():
                    ws.append([
                        row.get('Date', ''),
                        row.get('Particulars', ''),
                        row.get('Withdrawn amount', ''),
                        row.get('Deposit amount', ''),
                        row.get('Balance', ''),
                    ])

                _style_excel(ws)
                wb.save(excel_path)

                upload.excel_file.name = f'exports/{excel_filename}'
                upload.processed = True
                upload.save()

                raw_preview = df.head(15).to_dict('records')
                preview_rows = []
                for r in raw_preview:
                    preview_rows.append({
                        'd': r.get('Date', ''),
                        'p': r.get('Particulars', ''),
                        'w': r.get('Withdrawn amount', 0),
                        'dep': r.get('Deposit amount', 0),
                        'b': r.get('Balance', 0),
                    })
                messages.success(request, f'Successfully extracted {len(df)} transactions.')
                return render(request, 'converter/upload.html', {
                    'form': StatementUploadForm(),
                    'upload': upload,
                    'row_count': len(df),
                    'preview_rows': preview_rows,
                })

            except Exception as e:
                logger.exception(f"Error processing PDF: {e}")
                messages.error(request, f'Error processing PDF: {str(e)}')
                try:
                    upload.delete()
                except Exception:
                    pass
                return render(request, 'converter/upload.html', {'form': StatementUploadForm()})
    else:
        form = StatementUploadForm()

    return render(request, 'converter/upload.html', {'form': form})


@login_required
def download_excel(request, pk):
    upload = get_object_or_404(StatementUpload, pk=pk)
    if not upload.excel_file:
        raise Http404('Excel file not found.')
    file_path = upload.excel_file.path
    if not os.path.exists(file_path):
        raise Http404('Excel file not found on disk.')
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
