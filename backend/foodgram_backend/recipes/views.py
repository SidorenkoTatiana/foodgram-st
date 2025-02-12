from django.shortcuts import redirect


def short_link_redirect(request, pk):
    return redirect(f'/recipes/{pk}')
