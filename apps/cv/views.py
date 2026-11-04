from django.shortcuts import render


def cv_view(request):
    return render(request, "cv/cv.html")
