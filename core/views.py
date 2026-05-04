from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from characters.models import Character
from scenarios.models import Scenario
from .models import User
from .forms import CustomUserCreationForm, AuthenticationForm


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


@require_http_methods(["GET", "POST"])
def login_view(request):
    """Custom login view with error handling"""
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')

        if not username or not password:
            messages.error(request, 'Будь ласка, введіть ім\'я користувача та пароль.')
            form = AuthenticationForm()
            return render(request, 'core/login.html', {'form': form})

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Ласкаво просимо, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Неправильне ім\'я користувача або пароль.')
            form = AuthenticationForm()
            return render(request, 'core/login.html', {'form': form})

    form = AuthenticationForm()
    return render(request, 'core/login.html', {'form': form})


def register(request):
    """User registration with enhanced error handling"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.role = User.Role.PLAYER  # Default role
                user.save()
                login(request, user)
                messages.success(request, 'Реєстрація успішна! Ласкаво просимо до Cthulhu RPG Manager.')
                return redirect('dashboard')
            except Exception as e:
                messages.error(request, f'Помилка при реєстрації: {str(e)}')
                return render(request, 'core/register.html', {'form': form})
        else:
            # Form validation errors are displayed in template
            if form.non_field_errors():
                for error in form.non_field_errors():
                    messages.error(request, str(error))
    else:
        form = CustomUserCreationForm()

    return render(request, 'core/register.html', {'form': form})


def logout_view(request):
    """User logout - handles both GET and POST"""
    logout(request)
    messages.success(request, 'Ви успішно вийшли.')
    return redirect('home')