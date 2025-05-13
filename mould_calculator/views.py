from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .utils import process_mold_index, mould_score
from .forms import UploadFileForm
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import MouldAnalysis
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

import pandas as pd
import os
import uuid


def home(request):
    return render(request, 'home.html')


def about(request):
    return render(request, 'about.html')

# handling post and get requests
def uploadpage(request):
    form = UploadFileForm()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == "POST":
        if "file" not in request.FILES:
            error_message = "No file uploaded."
            return JsonResponse({'error': error_message}, status=400) if is_ajax else render(request, 'uploadpage.html', {'form': form, 'error': error_message})

        uploaded_file = request.FILES["file"]
        #save uploaded data on temporary path
        try:
    
            temp_filename = f"temp/{uuid.uuid4()}_{uploaded_file.name}"
            file_path = default_storage.save(temp_filename, ContentFile(uploaded_file.read())) 
            full_path = os.path.join(default_storage.location, file_path)

            df = pd.read_csv(full_path)
            #  handle dynamic window based on dataset
            mould_index, series, used_timeframe, full_data = process_mold_index(df)

            if mould_index is None:
                raise ValueError("Could not calculate mould index from the provided data.")

            risk_data = mould_score(mould_index, df)
            if risk_data is None:
                raise ValueError("Could not assess mould risk from provided data.")

            if request.user.is_authenticated:
                analysis = MouldAnalysis.objects.create(
                    user=request.user,
                    filename=uploaded_file.name,
                    file=uploaded_file,
                    temperature=risk_data['current_temperature'],
                    humidity=risk_data['current_humidity'],
                    mould_index=mould_index,
                    risk_level=risk_data['risk_level'],
                    risk_message=risk_data['status']
                )
                request.session['last_analysis_id'] = analysis.id
            else:
                request.session['anon_file_path'] = file_path

            return JsonResponse({'redirect_url': '/result'}) if is_ajax else redirect('result')

        except Exception as e:
            error_message = f"Error processing file: {str(e)}"
            return JsonResponse({'error': error_message}, status=500) if is_ajax else render(request, 'uploadpage.html', {'form': form, 'error': error_message})

    return render(request, 'uploadpage.html', {'form': form})


def result(request):
    dataset_id = request.GET.get('dataset_id')
    df = None
     #retrieve data based on user
    if dataset_id and request.user.is_authenticated:
        obj = get_object_or_404(MouldAnalysis, id=dataset_id, user=request.user)
        df = pd.read_csv(obj.file.path)
    elif request.user.is_authenticated and request.session.get('last_analysis_id'):
        try:
            analysis = MouldAnalysis.objects.get(id=request.session['last_analysis_id'], user=request.user)
            df = pd.read_csv(analysis.file.path)
        except Exception:
            pass
    elif request.session.get('anon_file_path'):
        try:
            file_path = os.path.join(default_storage.location, request.session['anon_file_path'])
            df = pd.read_csv(file_path)
        except Exception:
            pass

    if df is None:
        return redirect('uploadpage')

    #  choose rolling window dynamically
    mould_index, series, used_timeframe, full_data = process_mold_index(df)
    risk_data = mould_score(mould_index, df)
    #pass processed values to result template
    context = {
        'temperature': round(risk_data['current_temperature'], 1),
        'humidity': round(risk_data['current_humidity'], 1),
        'mould_index': round(risk_data['mould_index'], 1),
        'risk_level': risk_data['risk_level'],
        'risk_message': risk_data['status'],
        'temp_status': 'good' if risk_data['current_temperature'] < 26 else 'warning',
        'humidity_status': 'good' if risk_data['current_humidity'] < 60 else 'warning',
        'risk_class': 'low' if risk_data['risk_level'].lower() == 'low'
                      else 'medium' if risk_data['risk_level'].lower() == 'moderate'
                      else 'high',
        'used_timeframe': used_timeframe,
        'progress_width': f"{round(risk_data['mould_index'])}%"
    }

    return render(request, 'result.html', context)


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})


@login_required
def dashboard(request):
    analyses = MouldAnalysis.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'dashboard.html', {'analyses': analyses})
