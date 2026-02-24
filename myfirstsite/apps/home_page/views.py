from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Profile
from .forms import ProfileForm, SkillFormSet


def dashboard(request):
    profile = Profile.objects.prefetch_related('skills').first()
    return render(request, 'home_page/index.html', {'profile': profile})


@login_required
def edit_profile(request):
    profile = Profile.objects.prefetch_related('skills').first()
    if request.method == 'POST':
        form    = ProfileForm(request.POST, request.FILES, instance=profile)
        formset = SkillFormSet(request.POST, instance=profile)
        if form.is_valid() and formset.is_valid():
            saved_profile    = form.save()
            formset.instance = saved_profile  # 重新指定，確保 profile=None 時也能正確關聯
            formset.save()
            return redirect('home_page:index')
    else:
        form    = ProfileForm(instance=profile)
        formset = SkillFormSet(instance=profile)
    return render(request, 'home_page/edit_profile.html', {
        'form': form, 'formset': formset, 'profile': profile,
    })
