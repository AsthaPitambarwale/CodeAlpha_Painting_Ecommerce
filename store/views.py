from django.shortcuts import render, redirect
from .models import Product, Order
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Product  # if you have a Product model
from django.views.decorators.http import require_POST

def register_user(request):
    if request.method == 'POST':
        User.objects.create_user(username=request.POST['username'], password=request.POST['password'])
        return redirect('login')
    return render(request, 'store/register.html')

def login_user(request):
    if request.method == 'POST':
        user = authenticate(username=request.POST['username'], password=request.POST['password'])
        if user:
            login(request, user)
            return redirect('index')
    return render(request, 'store/login.html')

def logout_user(request):
    logout(request)
    return redirect('index')

# INDEX + SEARCH
def index(request):
    query = request.GET.get('q')
    products = Product.objects.filter(name__icontains=query) if query else Product.objects.all()
    return render(request, 'store/index.html', {'products': products})

def product_detail(request, id):
    product = Product.objects.get(id=id)
    return render(request, 'store/product_detail.html', {'product': product})

@login_required(login_url='/login/')
def add_to_cart(request, id):
    cart = request.session.get('cart', {})
    cart[str(id)] = cart.get(str(id), 0) + 1
    request.session['cart'] = cart
    return redirect('cart')

@login_required
def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            subtotal = product.price * quantity
            cart_items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
            total += subtotal
        except Product.DoesNotExist:
            continue

    return render(request, 'store/cart.html', {'cart_items': cart_items, 'total': total})

@require_POST
@login_required
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
    return redirect('cart')

import stripe
from django.http import JsonResponse
from .models import CartItem

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_cart_checkout_session(request):
    cart = request.session.get('cart', {})
    cart_items = []
    line_items = []

    if not cart:
        return render(request, 'store/cart.html', {'error': 'Cart is empty!'})

    total = 0
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            subtotal = product.price * quantity
            cart_items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
            total += subtotal

            line_items.append({
                'price_data': {
                    'currency': 'inr',
                    'product_data': {
                        'name': product.name,
                    },
                    'unit_amount': int(product.price * 100),  # convert to paisa
                },
                'quantity': quantity,
            })
        except Product.DoesNotExist:
            continue

    if not line_items:
        return render(request, 'store/cart.html', {'error': 'Cart is empty or invalid items!'})

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url='http://127.0.0.1:8000/payment-success/',
        cancel_url='http://127.0.0.1:8000/payment-cancel/',
    )

    return redirect(session.url)

@login_required
def payment_success(request):
    CartItem.objects.filter(user=request.user).delete()
    return render(request, 'store/payment_success.html')

@login_required
def payment_cancel(request):
    return render(request, 'store/payment_cancel.html')