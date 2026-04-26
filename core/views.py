from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from characters.models import Character
from scenarios.models import Scenario, ScenarioPlayer
from .models import User


def home(request):
    """Homepage - redirect to dashboard if logged in"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


@login_required
def dashboard(request):
    """User dashboard showing characters and scenarios"""
    user = request.user

    # Get user's alive characters
    alive_characters = Character.objects.filter(
        owner=user,
        is_alive=True,
        character_type='PC'
    )

    # Get ongoing scenarios user is participating in
    ongoing_scenarios = Scenario.objects.filter(
        players__player=user,
        status__in=['PLANNING', 'ACTIVE', 'PAUSED']
    ).distinct()

    # Get scenarios user is keeping
    keeping_scenarios = Scenario.objects.filter(
        keeper=user,
        status__in=['PLANNING', 'ACTIVE', 'PAUSED']
    )

    context = {
        'alive_characters': alive_characters,
        'ongoing_scenarios': ongoing_scenarios,
        'keeping_scenarios': keeping_scenarios,
        'is_keeper': user.is_keeper(),
    }

    return render(request, 'core/dashboard.html', context)


def register(request):
    """User registration"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.PLAYER  # Default role
            user.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome to Cthulhu RPG Manager.')
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'core/register.html', {'form': form})


def logout_view(request):
    """User logout - handles both GET and POST"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')