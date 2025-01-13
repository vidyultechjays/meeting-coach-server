# transcription/views.py
import json
import os
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests


@csrf_exempt
def transcribe(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Get the audio file from the request
        audio_file = request.FILES.get('file')
        if not audio_file:
            return JsonResponse({'error': 'No audio file provided'}, status=400)
        
        # Prepare the request to OpenAI
        url = 'https://api.openai.com/v1/audio/transcriptions'
        headers = {
            'Authorization': f'Bearer {settings.OPENAI_API_KEY}'
        }
        
        files = {
            'file': ('audio.wav', audio_file, 'audio/wav'),
        }
        
        data = {
            'model': 'whisper-1',
            'language': 'en',
            'prompt': 'This is a continuation of the previous transcription.'
        }
        
        # Make the request to OpenAI
        response = requests.post(url, headers=headers, files=files, data=data)
        
        # Return the response to the client
        return JsonResponse(response.json())
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def coaching(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        # Parse the JSON body
        body = json.loads(request.body)
        agenda = body.get('agenda')
        transcript = body.get('transcript')
        question = body.get('question')
        
        if not agenda or not transcript or not question:
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Prepare the request to OpenAI
        url = 'https://api.openai.com/v1/chat/completions'
        headers = {
            'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
            'Content-Type': 'application/json',
        }
        
        messages = [
            {'role': 'system', 'content': 'You are a professional meeting coach. This is a live meeting transcript.'},
            {'role': 'user', 'content': f'Agenda:\n{agenda}\n\nTranscript:\n{transcript}\n\nThe user asks:\n{question}'}
        ]
        
        data = {
            'model': 'gpt-4o',
            'messages': messages,
            'temperature': 0.7,
        }
        
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an error for bad responses
        
        # Return the response to the client
        return JsonResponse(response.json())
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def landing_page(request):
    return render(request, 'download_extension.html')

def download_extension(request):
    extension_path = os.path.join(settings.BASE_DIR, 'static', 'meeting_coach.zip')
    
    if os.path.exists(extension_path):
        response = FileResponse(
            open(extension_path, 'rb'),
            content_type='application/zip'
        )
        response['Content-Disposition'] = 'attachment; filename="meeting-coach.zip"'
        return response
    else:
        return JsonResponse({'error': 'Extension file not found'}, status=404)
