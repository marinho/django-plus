def path_to_object(path):
    """Returns a Python object from a string path"""
    dot = '.' in path and path.rindex('.') or None
    
    if dot:
        f_mod, f_obj = path[:dot], path[dot+1:]

        mod = __import__(f_mod, {}, {}, [''])
        obj = getattr(mod, f_obj)
    else:
        obj = __import__(path, {}, {}, [''])

    return obj

def split1000(s, sep=','):
    """http://www.python.org.br/wiki/FormatarNumeros"""
    minus = s.startswith('-')
    if minus: s = s[1:]
    res = len(s) <= 3 and s or split1000(s[:-3], sep) + sep + s[-3:]

    return (minus and '-' or '') + res

def get_admin_url(obj):
    from django.contrib import admin
    admin_root_path = admin.site.root_path

    # Try method 'get_admin_url' before use ordinary way
    try:
        return getattr(obj, 'get_admin_url')()
    except AttributeError:
        pass

    return '%s%s/%s/%s/'%(
            admin_root_path,
            obj._meta.app_label,
            obj.__class__.__name__.lower(),
            obj.pk,
            )

def get_full_url(url):
    from django.contrib.sites.models import Site
    site = Site.objects.get_current()

    url = url.startswith('/') and url or '/' + url

    return 'http://%s%s'%(site.domain, url)

