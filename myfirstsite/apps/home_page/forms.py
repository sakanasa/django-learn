from django import forms
from django.forms import inlineformset_factory
from .models import Profile, Skill


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = Profile
        fields = ['display_name', 'role', 'bio', 'avatar']
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyrene-pink transition-colors'}),
            'role':         forms.TextInput(attrs={'class': 'w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-cyrene-lavender transition-colors'}),
            'bio':          forms.Textarea(attrs={'rows': 4, 'class': 'w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white leading-relaxed resize-y focus:outline-none focus:border-cyrene-lavender transition-colors'}),
            'avatar':       forms.ClearableFileInput(attrs={'class': 'text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-cyrene-pink/10 file:text-cyrene-pink hover:file:bg-cyrene-pink/20 cursor-pointer', 'accept': 'image/*'}),
        }


class SkillForm(forms.ModelForm):
    class Meta:
        model  = Skill
        fields = ['name', 'percentage', 'gradient', 'label_color', 'order']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyrene-blue transition-colors'}),
            'percentage':  forms.NumberInput(attrs={'class': 'w-20 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm text-center focus:outline-none focus:border-cyrene-pink transition-colors', 'min': 0, 'max': 100}),
            'gradient':    forms.Select(attrs={'class': 'bg-cyrene-dark border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none transition-colors'}),
            'label_color': forms.Select(attrs={'class': 'bg-cyrene-dark border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none transition-colors'}),
            'order':       forms.NumberInput(attrs={'class': 'w-16 bg-white/5 border border-white/10 rounded-lg px-2 py-2 text-white text-sm text-center focus:outline-none transition-colors'}),
        }


SkillFormSet = inlineformset_factory(
    Profile, Skill, form=SkillForm,
    extra=1, can_delete=True, min_num=0, validate_min=False,
)
