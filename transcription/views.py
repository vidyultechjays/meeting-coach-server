import json
import os
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import requests


CHUNK_SIZE: int = 5000

@csrf_exempt
def google_auth(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'No token provided'}, status=400)
            
        user_info_response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {token}'}
        )
        
        if not user_info_response.ok:
            return JsonResponse({'error': 'Failed to verify token'}, status=401)
            
        user_info = user_info_response.json()
        email = user_info.get('email', '')
        
        # Check domain
        if not email.endswith('@techjays.com'):
            return JsonResponse({
                'error': 'Unauthorized domain',
                'message': 'Only Techjays employees are authorized'
            }, status=403)
            
        return JsonResponse({
            'status': 'success',
            'user': user_info
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def revoke_token(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'error': 'No token provided'}, status=400)
            
        # Revoke token with Google
        revoke_response = requests.get(f'https://accounts.google.com/o/oauth2/revoke?token={token}')
        
        if not revoke_response.ok:
            return JsonResponse({'error': 'Failed to revoke token'}, status=400)
            
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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




def split_text(text, size):
    """Split the input text into chunks of max `size` characters."""
    return [text[i:i + size] for i in range(0, len(text), size)]


def summarize_chunk(chunk):
    """Call OpenAI to summarize a transcript chunk."""
    summary_prompt = [
        {'role': 'system', 'content': 'You are a helpful assistant summarizing a meeting transcript.'},
        {'role': 'user', 'content': f"Summarize the following part of the meeting transcript:\n\n{chunk}"}
    ]

    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'model': 'gpt-4o',
            'messages': summary_prompt,
            'temperature': 0.3,
        }
    )

    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']


@csrf_exempt
def coaching(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        body = json.loads(request.body)
        agenda = body.get('agenda')
        transcript = body.get('transcript', '').strip()
        question = body.get('question')
        response_text = body.get('responseText', '').strip()
        follow_up_text = body.get('followUpText', '').strip()


        if not agenda or not transcript or not question:
            return JsonResponse({'error': 'Missing required fields'}, status=400)

        # Step 1: Split and summarize transcript
        transcript_chunks = split_text(transcript, CHUNK_SIZE)
        summaries = []

        for chunk in transcript_chunks:
            summary = summarize_chunk(chunk)
            summaries.append(summary)

        summarized_transcript = "\n\n".join(summaries)

        # Step 2: Build user content
        user_content = f"Agenda:\n{agenda}\n\nTranscript Summary:\n{summarized_transcript}\n\nQuestion:\n{question}"

        if response_text:
            user_content += f"\n\nResponse:\n{response_text}"

        if follow_up_text:
            user_content += f"\n\nFollow-up:\n{follow_up_text}"

        # Step 3: Final coaching prompt
        messages = [
            {'role': 'system', 'content': 'You are a professional meeting coach. This is a live meeting transcript.'},
            {'role': 'user', 'content': user_content}
        ]

        data = {
            'model': 'gpt-4o',
            'messages': messages,
            'temperature': 0.7,
        }

        headers = {
            'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
            'Content-Type': 'application/json',
        }

        # print("Final coaching payload:", json.dumps(data, indent=2))

        final_response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data
        )

        print("Status Code:", final_response.status_code)
        print("OpenAI Final Response:", final_response.text)

        final_response.raise_for_status()
        return JsonResponse(final_response.json())

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except requests.exceptions.HTTPError as http_err:
        return JsonResponse({'error': 'OpenAI API error', 'details': final_response.text}, status=final_response.status_code)
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
