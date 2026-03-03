from django import forms

class CandidateForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your full name',
            'class': 'w-full px-4 py-2 rounded-md',
            'required': True
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'placeholder': 'Enter valid email to send result',
            'class': 'w-full px-4 py-2 rounded-md',
            'required': True
        })
    )
    job_description = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Example: Python Developer',
            'class': 'w-full px-4 py-2 rounded-md',
            'rows': 3,
            'required': True
        })
    )


class AnswerForm(forms.Form):
    answer = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Type your answer here or use the microphone button to speak',
            'class': 'w-full px-4 py-2 rounded-md',
            'rows': 6,
            'required': True
        })
    )
