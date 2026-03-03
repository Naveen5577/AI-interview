import json
import re
from django.conf import settings
from django.shortcuts import render, redirect
from .forms import CandidateForm, AnswerForm
from .models import Candidate, InterviewResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

import google.generativeai as genai

genai.configure(api_key=settings.GOOGLE_API_KEY)

def generate_question(messages, job_description):
    # Count how many questions have been asked
    question_count = len([m for m in messages if 'content' in m]) // 2 + 1
    
    prompt = (
        f"You are conducting a technical interview for the position: {job_description}\n\n"
        f"This is question {question_count} of 5.\n"
        f"Generate ONE specific technical or behavioral interview question that directly tests skills, knowledge, or experience required for a {job_description}.\n\n"
        f"Requirements:\n"
        f"- Question must be highly relevant to {job_description}\n"
        f"- Focus on technical skills, tools, frameworks, or methodologies used in this role\n"
        f"- Make it specific and practical, not generic\n"
        f"- Keep it concise (1-2 sentences)\n"
        f"- Do NOT include any explanation or context, just the question\n\n"
        f"Example for 'Python Developer': 'Explain the difference between list and tuple in Python and when you would use each.'\n"
        f"Example for 'Data Scientist': 'How would you handle missing data in a dataset before building a machine learning model?'\n\n"
        f"Now generate a question for: {job_description}"
    )
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        question = response.text.strip()
        # Remove any quotes or extra formatting
        question = question.strip('"').strip("'").strip()
        return question if question else f"Describe your experience with {job_description}."
    except Exception as e:
        print(f"ERROR: Question generation failed - {str(e)}")
        return f"Tell me about your experience as a {job_description}."

def evaluate_answer(question, answer):
    prompt = (
        f"Evaluate the following candidate answer to the interview question.\n\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        f"Respond in JSON format like:\n"
        f'{{"score": <0-5>, "qualified": "yes" or "no"}}\n'
        f"Only respond with valid JSON. No explanations."
    )

    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        content = response.text.strip()

        try:
            parsed = json.loads(content)
            score = int(parsed.get("score", 0))
            qualified = parsed.get("qualified", "no")
            return {"score": score, "qualified": qualified}
        except Exception:
            try:
                match = re.search(r'{.*}', content)
                if match:
                    parsed = json.loads(match.group())
                    score = int(parsed.get("score", 0))
                    qualified = parsed.get("qualified", "no")
                    return {"score": score, "qualified": qualified}
            except:
                pass
    except Exception as e:
        print(f"ERROR: Evaluation API call failed - {str(e)}")

    return {"score": 0, "qualified": "no"}


def start_interview(request):
    if request.method == 'POST':
        form = CandidateForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            job_description = form.cleaned_data['job_description']
            
            # Check attempts for same email and role
            attempt_count = Candidate.objects.filter(
                email=email,
                job_description=job_description
            ).count()
            
            if attempt_count >= 3:
                return render(request, 'users/start.html', {
                    'form': form,
                    'error_message': f'You have already applied 3 times for this role. Maximum attempts reached.'
                })
            
            candidate = Candidate.objects.create(
                name=form.cleaned_data['name'],
                email=email,
                job_description=job_description,
                interview_start_time=timezone.now()
            )

            request.session['candidate_id'] = candidate.id
            request.session['job_description'] = candidate.job_description
            request.session['messages'] = []
            request.session['interview_start_time'] = timezone.now().isoformat()

            # First role-based question
            first_question = generate_question([], candidate.job_description)

            request.session['messages'].append({"content": first_question})

            return render(request, 'users/question.html', {
                'question': first_question,
                'form': AnswerForm()
            })
        else:
            # Form is not valid, show errors
            return render(request, 'users/start.html', {
                'form': form,
                'error_message': 'Please fill all fields correctly.'
            })

    else:
        form = CandidateForm()

    return render(request, 'users/start.html', {'form': form})



def answer_question(request):
    candidate_id = request.session.get('candidate_id')
    messages = request.session.get('messages', [])
    job_description = request.session.get('job_description')

    candidate = Candidate.objects.get(id=candidate_id)
    
    # Check if disqualified
    if candidate.is_disqualified:
        return redirect('interview_results', candidate_id=candidate.id)

    if request.method == 'POST':
        form = AnswerForm(request.POST)
        if form.is_valid():
            answer = form.cleaned_data['answer']
            last_question = messages[-1]['content']

            # Save answer WITHOUT evaluation (save API calls)
            InterviewResponse.objects.create(
                candidate=candidate,
                question=last_question,
                answer=answer,
                score=None  # Will evaluate later
            )

            # Count how many responses we have now
            total_responses = InterviewResponse.objects.filter(candidate=candidate).count()
            print(f"DEBUG: Saved response {total_responses}/5")

            # If we have 5 responses, evaluate ALL at once and show results
            if total_responses >= 5:
                print(f"DEBUG: All 5 questions answered. Evaluating all answers now...")
                
                # Evaluate all 5 answers in one batch
                responses = InterviewResponse.objects.filter(candidate=candidate)
                for response in responses:
                    try:
                        evaluation = evaluate_answer(response.question, response.answer)
                        response.score = evaluation.get("score", 0)
                        response.save()
                        print(f"DEBUG: Evaluated - Score: {response.score}")
                    except Exception as e:
                        print(f"DEBUG: Evaluation failed - {str(e)}")
                        response.score = 0
                        response.save()
                
                return redirect('interview_results', candidate_id=candidate.id)

            # Save answer in history
            messages.append({"content": answer})

            # Generate next question
            next_question = generate_question(messages, job_description)
            messages.append({"content": next_question})
            request.session['messages'] = messages

            print(f"DEBUG: Generated question {total_responses + 1}")

            return render(request, 'users/question.html', {
                'question': next_question,
                'form': AnswerForm(),
                'question_number': total_responses + 1
            })

    return render(request, 'users/question.html', {
        'question': messages[-1]['content'],
        'form': AnswerForm(),
        'question_number': InterviewResponse.objects.filter(candidate=candidate).count() + 1
    })



from django.core.mail import send_mail
def interview_results(request, candidate_id):
    candidate = Candidate.objects.get(id=candidate_id)
    candidate.interview_end_time = timezone.now()
    candidate.save()
    
    responses = InterviewResponse.objects.filter(candidate=candidate)
    
    # Check if any responses need evaluation (score is None)
    unevaluated = responses.filter(score__isnull=True)
    if unevaluated.exists():
        print(f"DEBUG: Found {unevaluated.count()} unevaluated responses. Evaluating now...")
        for response in unevaluated:
            try:
                evaluation = evaluate_answer(response.question, response.answer)
                response.score = evaluation.get("score", 0)
                response.save()
            except:
                response.score = 0
                response.save()
    
    # Refresh responses after evaluation
    responses = InterviewResponse.objects.filter(candidate=candidate)
    total_score = sum(r.score for r in responses if r.score is not None)
    avg_score = total_score / len(responses) if responses else 0
    
    # Check disqualification first
    if candidate.is_disqualified:
        status = "Disqualified"
    else:
        status = "Qualified" if avg_score >= 3 else "Disqualified"
    
    # Calculate interview duration
    duration = None
    duration_minutes = 0
    if candidate.interview_start_time and candidate.interview_end_time:
        duration = candidate.interview_end_time - candidate.interview_start_time
        duration_minutes = int(duration.total_seconds() / 60)

    # Email subject and body based on status
    if candidate.is_disqualified:
        subject = "❌ Interview Disqualification Notice"
        message = (
            f"Dear {candidate.name},\n\n"
            f"We regret to inform you that you have been disqualified from the interview.\n"
            f"Reason: {candidate.disqualification_reason}\n\n"
            f"We maintain strict integrity standards during our interview process.\n\n"
            f"Regards,\nAI Interview Team"
        )
    elif status == "Qualified":
        subject = "🎉 Congratulations! You are Qualified"
        message = (
            f"Dear {candidate.name},\n\n"
            f"Congratulations on successfully completing your interview for the position of {candidate.job_description}.\n"
            f"Your average score is {avg_score:.2f}. We are happy to inform you that you are qualified & offer letter should be released soon.\n\n"
            f"Regards,\nAI Interview Team"
        )
    else:
        subject = "📩 Interview Result - Not Qualified"
        message = (
            f"Dear {candidate.name},\n\n"
            f"Thank you for attending the interview for the position of {candidate.job_description}.\n"
            f"Your average score is {avg_score:.2f}. Unfortunately, you have not qualified this time.\n\n"
            f"We encourage you to keep learning and try again.\n\n"
            f"Best wishes,\nAI Interview Team"
        )

    # Send email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [candidate.email],
        fail_silently=False,
    )

    return render(request, 'users/results.html', {
        'candidate': candidate,
        'responses': responses,
        'avg_score': avg_score,
        'qualification_status': status,
        'duration_minutes': duration_minutes if duration else 0
    })
def all_results(request):
    candidates = Candidate.objects.all().order_by('-id')
    results = []
    for c in candidates:
        responses = InterviewResponse.objects.filter(candidate=c)
        total_score = sum(r.score for r in responses if r.score is not None)
        avg_score = total_score / len(responses) if responses else 0
        status = "Qualified" if avg_score >= 3 else "Disqualified"
        results.append({
            'candidate': c,
            'avg_score': avg_score,
            'status': status,
        })
    return render(request, 'users/all_results.html', {'results': results})

###  code for home and logins
def index(request):
    return render(request, 'index.html')



from django.shortcuts import render, redirect
from .models import RegisteredUser
from django.core.files.storage import FileSystemStorage

def register_view(request):
    msg = ''
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        image = request.FILES.get('image')

        # Basic validation
        if not (name and email and mobile and password and image):
            msg = "All fields are required."
        else:
            # Save image manually
            fs = FileSystemStorage()
            filename = fs.save(image.name, image)
            img_url = fs.url(filename)

            # Save user with is_active=False
            RegisteredUser.objects.create(
                name=name,
                email=email,
                mobile=mobile,
                password=password,
                image=filename,
                is_active=False
            )
            msg = "Registered successfully! Wait for admin approval."

    return render(request, 'register.html', {'msg': msg})

from django.utils import timezone

from django.utils import timezone
import pytz

def user_login(request):
    msg = ''
    if request.method == 'POST':
        name = request.POST.get('name')
        password = request.POST.get('password')

        try:
            user = RegisteredUser.objects.get(name=name, password=password)
            if user.is_active:
                # Convert current time to IST
                ist = pytz.timezone('Asia/Kolkata')
                local_time = timezone.now().astimezone(ist)

                # Save user info in session
                request.session['user_id'] = user.id
                request.session['user_name'] = user.name
                request.session['user_image'] = user.image.url  # image URL
                request.session['login_time'] = local_time.strftime('%I:%M:%S %p')

                return redirect('user_homepage')
            else:
                msg = "Your account is not activated yet."
        except RegisteredUser.DoesNotExist:
            msg = "Invalid credentials."

    return render(request, 'user_login.html', {'msg': msg})

def admin_login(request):
    msg = ''
    if request.method == 'POST':
        name = request.POST.get('name')
        password = request.POST.get('password')

        if name == 'admin' and password == 'admin':
            return redirect('admin_home')
        else:
            msg = "Invalid admin credentials."

    return render(request, 'admin_login.html', {'msg': msg})

def admin_home(request):
    return render(request, 'admin_home.html')
    
def admin_dashboard(request):
    users = RegisteredUser.objects.all()
    return render(request, 'admin_dashboard.html', {'users': users})

def activate_user(request, user_id):
    user = RegisteredUser.objects.get(id=user_id)
    user.is_active = True
    user.save()
    return redirect('admin_dashboard')

def deactivate_user(request, user_id):
    user = RegisteredUser.objects.get(id=user_id)
    user.is_active = False
    user.save()
    return redirect('admin_dashboard')

def delete_user(request, user_id):
    user = RegisteredUser.objects.get(id=user_id)
    user.delete()
    return redirect('admin_dashboard')



def home(request):
    return render(request, 'home.html')

def user_homepage(request):
    if 'user_id' not in request.session:
        # User not logged in, redirect to login page
        return redirect('user_login')

    user_name = request.session.get('user_name')
    user_image = request.session.get('user_image')
    login_time = request.session.get('login_time')

    context = {
        'user_name': user_name,
        'user_image': user_image,
        'login_time': login_time,
    }
    return render(request, 'users/user_homepage.html', context)

def user_logout(request):
    request.session.flush()  # Clears all session data
    return redirect('user_login')



import random
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from .models import RegisteredUser

otp_storage = {}  # Temporary dictionary to store OTPs

def send_otp(email):
    otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
    otp_storage[email] = otp

    subject = "Password Reset OTP"
    message = f"Your OTP for password reset is: {otp}"
    from_email = "saikumardatapoint1@gmail.com"  # Change this to your email
    send_mail(subject, message, from_email, [email])

    return otp

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if RegisteredUser.objects.filter(email=email).exists():
            send_otp(email)
            request.session["reset_email"] = email  # Store email in session
            return redirect("verify_otp")
        else:
            messages.error(request, "Email not registered!")

    return render(request, "forgot_password.html")

def verify_otp(request):
    if request.method == "POST":
        otp_entered = request.POST.get("otp")
        email = request.session.get("reset_email")

        if otp_storage.get(email) and str(otp_storage[email]) == otp_entered:
            return redirect("reset_password")
        else:
            messages.error(request, "Invalid OTP!")

    return render(request, "verify_otp.html")

def reset_password(request):
    if request.method == "POST":
        new_password = request.POST.get("new_password")
        email = request.session.get("reset_email")

        if RegisteredUser.objects.filter(email=email).exists():
            user = RegisteredUser.objects.get(email=email)
            user.password = new_password  # Updating password
            user.save()
            messages.success(request, "Password reset successful! Please log in.")
            return redirect("user_login")

    return render(request, "reset_password.html")


@csrf_exempt
def track_violation(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        violation_type = data.get('type')
        candidate_id = request.session.get('candidate_id')
        
        if candidate_id:
            candidate = Candidate.objects.get(id=candidate_id)
            
            if violation_type == 'tab_switch':
                candidate.tab_switch_count += 1
                candidate.save()
                
                if candidate.tab_switch_count >= 2:
                    candidate.is_disqualified = True
                    candidate.disqualification_reason = f"Switched tabs {candidate.tab_switch_count} times during interview"
                    candidate.save()
                    return JsonResponse({'status': 'disqualified', 'count': candidate.tab_switch_count})
                
                return JsonResponse({'status': 'warning', 'count': candidate.tab_switch_count})
            
            elif violation_type in ['copy', 'paste', 'right_click']:
                candidate.is_disqualified = True
                candidate.disqualification_reason = f"Attempted to {violation_type} during interview"
                candidate.save()
                return JsonResponse({'status': 'disqualified', 'reason': violation_type})
        
        return JsonResponse({'status': 'error'})
    return JsonResponse({'status': 'error'})


def send_interview_link(request):
    msg = ''
    if request.method == 'POST':
        candidate_name = request.POST.get('name')
        candidate_email = request.POST.get('email')
        job_role = request.POST.get('job_role')
        
        if candidate_name and candidate_email and job_role:
            interview_link = request.build_absolute_uri('/start/')
            
            subject = "🎯 Interview Invitation - AI Interviewer"
            message = (
                f"Dear {candidate_name},\n\n"
                f"You have been invited to attend an interview for the position of {job_role}.\n\n"
                f"Please click the link below to start your interview:\n"
                f"{interview_link}\n\n"
                f"Interview Guidelines:\n"
                f"- Time Limit: 20 minutes total for entire interview\n"
                f"- Do not switch tabs or windows during the interview\n"
                f"- No copy/paste allowed\n"
                f"- Answer honestly based on your knowledge\n\n"
                f"Best of luck!\n\n"
                f"Regards,\nAI Interview Team"
            )
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [candidate_email],
                fail_silently=False,
            )
            msg = f"Interview link sent successfully to {candidate_email}"
        else:
            msg = "All fields are required."
    
    return render(request, 'send_interview_link.html', {'msg': msg})

