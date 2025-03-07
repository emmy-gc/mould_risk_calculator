from django.shortcuts import render, redirect
from django.http import JsonResponse
from .utils import process_mold_index
from .utils import mould_score
from .forms import UploadFileForm
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import pandas as pd
import os


def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def uploadpage(request):
    form = UploadFileForm()
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == "POST":
        if "file" not in request.FILES:
            error_message = "No file uploaded."
            return JsonResponse({'error': error_message}, status=400) if is_ajax else render(request, 'uploadpage.html', {'form': form, 'error': error_message})

        uploaded_file = request.FILES["file"]

        try:
            file_path = default_storage.save(uploaded_file.name, ContentFile(uploaded_file.read())) 
            full_path = os.path.join(default_storage.location, file_path)  

        
            df = pd.read_csv(full_path)
            print("\nOriginal CSV columns:", df.columns.tolist())
            print("\nFirst few rows of original data:")
            print(df.head())

            default_storage.delete(file_path)

            latest_mould_index = process_mold_index(df)
            if latest_mould_index is None:
                raise ValueError("Could not calculate mould index from the provided data.")
            
            risk_data = mould_score(latest_mould_index, df)
            if risk_data is None:
                raise ValueError("Could not assess mould risk from provided data.")
            
            
            request.session['analysis_results'] = {
                'current_temperature': float(risk_data['current_temperature']),
                'current_humidity': float(risk_data['current_humidity']),
                'risk_level': risk_data['risk_level'],
                'mould_index': latest_mould_index
            }
            
            return JsonResponse({'redirect_url': '/result'}) if is_ajax else redirect('result')
        except Exception as e:
            error_message = f"Error processing file: {str(e)}"
            print("\nError processing file:", str(e))
            print("Type of error:", type(e))
            return JsonResponse({'error': error_message}, status=500) if is_ajax else render(request, 'uploadpage.html', {'form': form, 'error': error_message})
    return render(request, 'uploadpage.html', {'form': form})

def result(request):
    if 'analysis_results' in request.session:
        results = request.session['analysis_results']
        
        
        temperature = float(results.get('current_temperature', 0))
        if temperature < 20:
            temp_status = "good"
            temp_message = "Normal Temperature Range"
        elif temperature < 25:
            temp_status = "warning"
            temp_message = "Elevated Temperature"
        else:
            temp_status = "danger"
            temp_message = "High Temperature Risk"

       
        humidity = float(results.get('current_humidity', 0))
        if humidity < 60:
            humidity_status = "good"
            humidity_message = "Normal Humidity Range"
        elif humidity < 70:
            humidity_status = "warning"
            humidity_message = "Elevated Humidity"
        else:
            humidity_status = "danger"
            humidity_message = "High Humidity Risk"

       
        risk_level = results.get('risk_level', 'Unknown')
        mould_index = results.get('mould_index',0)
        
        if risk_level.lower() == 'low':
            risk_class = 'low'
            risk_message = "Low risk of mould growth"
        elif risk_level.lower() == 'medium':
            risk_class = 'medium'
            risk_message = "Moderate risk - monitor conditions"
        else:
            risk_class = 'high'
            risk_message = "High risk - take action immediately"

        context = {
            'temperature': f"{temperature:.1f}",
            'humidity': f"{humidity:.1f}",
            'mould_index': f"{mould_index:.2f}",
            'temp_status': temp_status,
            'temp_message': temp_message,
            'humidity_status': humidity_status,
            'humidity_message': humidity_message,
            'risk_level': risk_level,
            'risk_class': risk_class,
            'risk_message': risk_message
        }
        
        return render(request, 'result.html', context)
    
    return redirect('uploadpage')

