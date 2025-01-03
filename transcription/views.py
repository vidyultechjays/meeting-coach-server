# transcription/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests
import json

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
