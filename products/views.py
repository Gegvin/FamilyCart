from django.shortcuts import render, HttpResponse

def index(request):
    return render (request, 'products/index.html')
def catalog(request):
    return render (request, 'products/catalog.html')

# Create your views here.
