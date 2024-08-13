import datetime

cached = dict()

def memoize(func):
    key_func = str(func)
    cached[key_func] = dict()
    print(cached)
    def ret(*args):
        key = ""
        for arg in args:
            if isinstance(arg, tuple) or isinstance(arg, list):
                key += arg.join(", ")
            else:
                key += "_" + str(arg)
        if key not in cached[key_func]:
            cached[key_func][key] = func(*args)
        return cached[key_func][key]
    return ret

def timed_memoized(seconds):
    def inter_memoized(func):
        key_func = str(func)
        cached[key_func] = dict()
        def ret(*args):
            key = ""
            for arg in args:
                if isinstance(arg, tuple) or isinstance(arg, list):
                    key += arg.join(", ")
                else:
                    key += "_" + str(arg)
            if key not in cached[key_func]:
                cached[key_func][key] = {"data":func(*args), "expires":datetime.datetime.now() + datetime.timedelta(seconds=seconds)}
            return cached[key_func][key]["data"]
        return ret
    return inter_memoized

def verify_cache():
    for cache_for_function in cached.values():
        expired_keys = []
        for key, data in cache_for_function.items():
            now = datetime.datetime.now()
            expires = data["expires"]
            if (now - expires).total_seconds() >= 0:
                expired_keys.append(key)
        for key in expired_keys:
            if key in cache_for_function:
                del cache_for_function[key]
                


