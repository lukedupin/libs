from django.http import HttpResponse
from website.helpers.util import xstr, xint, xfloat, xbool
import json, re, math

#Value conversion
def convertData( key, typ, raw, default ):
    val = None
    err = "Unknown type for %s" % key

    if issubclass( typ, str ):
        val = xstr( raw, default )
        err = None if val is not None else "Couldn't parse %s as string" % key
    elif issubclass( typ, bool ):
        val = xbool( raw, none=default, undefined=default)
        err = None if val is not None else "Couldn't parse %s as bool" % key
    elif issubclass( typ, int ):
        val = xint( raw, default )
        err = None if val is not None else "Couldn't parse %s as int" % key
    elif issubclass( typ, float ):
        val = xfloat( raw, default )
        err = None if val is not None else "Couldn't parse %s as float" % key
    elif issubclass( typ, dict ) or issubclass( typ, list ):
        contains = tuple() if default is None else default
        err = None
        try:
            #Testing cases mostly, we already have a dict of data
            if isinstance(raw, dict):
                return (raw, None)

            #Convert the string
            val = json.loads( raw )
            if val is None:
                return ( None, "Error, couldn't load valid json for %s" % key )

            #If json, check for contain keys, if the format is invalid, quit
            if len(contains) > 0 and not all(k in val for k in contains):
                missing = []
                for k in contains:
                    if k not in val:
                        missing.append( k )
                        val = None

                if len(missing) > 0:
                    err = "Invalid %s format. Required %s missing %s" % ( key, contains, missing)

        except json.decoder.JSONDecodeError as e:
            return ( None, "Error processing json object %s [%s]" % (key, str(e)) )

    return ( val, err )

#Internal function which runs the assignment action
def pullArgs( kwargs, req_args, request_args, req_dict, missing ):
    errs = []
    for x in request_args:
        if len(x) < 2:
            return "Invalid json value, must have at least key and type"

        #Pull my info out
        key = x[0]
        type = x[1]
        default = None if len(x) == 2 else x[2]

        #Don't allow args that already exist to be overwritten!
        if key in kwargs:
            req_args[key] = kwargs[key]
            continue

        #Parse the key
        val, err = convertData( key, type, req_dict[key], default) if key in req_dict and req_dict[key] is not None else (default, None)
        kwargs[key] = val

        # Add any errors, we don't want to block the other variables
        if err is not None:
            errs.append(err)

        #Store the data
        if val is not None:
            kwargs[key] = req_args[key] = val
        elif missing is not None:
            missing.append( key )

    # Return errors? or no error if everythign worked
    return None if len(errs) <= 0 else ', '.join(errs)

#Request args wrapper class
class reqArgs:
    def __init__(self, auth=None, sess_req=[], sess_opt=[], get_req=[], get_opt=[], post_req=[], post_opt=[], body_req=[], body_opt=[] ):
        def _args( args ):
            return args if isinstance( args, tuple) or isinstance( args, list ) else (args,)

        self.auth = auth
        self.sess_req = _args( sess_req )
        self.get_req = _args( get_req )
        self.post_req = _args( post_req )
        self.body_req = _args( body_req )

        self.sess_opt = _args( sess_opt )
        self.get_opt = _args( get_opt )
        self.post_opt = _args( post_opt )
        self.body_opt = _args( body_opt )

    def __call__(self, func):
        def wrapper( *args, **kwargs ):
            #Get my request object
            req_args = {}
            request = kwargs['request'] if 'request' in kwargs else args[0]
            #print("Nuts")
            #print(kwargs)
            #print( request.POST )
            #print( request.GET )
            get_missing = []
            post_missing = []
            sess_missing = []
            body_missing = []
            #print(request.POST)

            # Map the body to js?
            body_js = {}
            if len(self.body_req) + len(self.body_opt) > 0:
                # Map the body
                err_msg = None
                try:
                    body_js = json.loads(request.body.decode('ascii'))
                except json.JSONDecodeError as e:
                    err_msg = str(e)
                if body_js is None or err_msg is not None:
                    return errResponse(request, "Couldn't map posted body: %s" % err_msg)

            #Required args
            err = pullArgs( kwargs, req_args, self.sess_req, request.session, sess_missing )
            if err is not None:
                return errResponse( request, err )
            err = pullArgs( kwargs, req_args, self.post_req, request.POST, post_missing )
            if err is not None:
                return errResponse( request, err )
            err = pullArgs( kwargs, req_args, self.get_req, request.GET, get_missing )
            if err is not None:
                return errResponse( request, err )
            err = pullArgs( kwargs, req_args, self.body_req, body_js, body_missing )
            if err is not None:
                return errResponse( request, err )

            #Optional args, no missing accumulation
            err = pullArgs( kwargs, req_args, self.sess_opt, request.session, None )
            if err is not None:
                return errResponse( request, err )
            err = pullArgs( kwargs, req_args, self.post_opt, request.POST, None )
            if err is not None:
                return errResponse( request, err )
            err = pullArgs( kwargs, req_args, self.get_opt, request.GET, None )
            if err is not None:
                return errResponse( request, err )
            err = pullArgs( kwargs, req_args, self.body_opt, body_js, None )
            if err is not None:
                return errResponse( request, err )

            #Are we good?
            if len(get_missing) + len(post_missing) + len(sess_missing) + len(body_missing) > 0:
                return errResponse( request, 'Missing required argument(s): GET%s POST%s SESS%s BODY%s' % (str(get_missing), str(post_missing), str(sess_missing), str(body_missing)))

            #Store all args into the requested args hash
            kwargs['req_args'] = req_args

            #Auth check?
            if self.auth is not None:
                #True for check authentication with default system auth
                if isinstance( self.auth, bool ):
                    if self.auth:
                        if not request.user.is_authenticated():
                            return errResponse( request, "Not logged in")

                #Custom user authentication, we just just need a true/false
                elif hasattr( self.auth, '__call__'):
                    if not self.auth( *args, **kwargs ):
                        return errResponse( request, "Not logged in")

                #Not sure what we were pass, default to system authentication
                else:
                    print("Unknown auth type, running default authentication to be safe")
                    if not request.user.is_authenticated():
                        return errResponse( request, "Not logged in")

            return func( *args, **kwargs)
        return wrapper

  #Json response
def jsonResponse( request, objs={} ):
    objs['successful'] = True
    callback = request.GET['callback'] if 'callback' in request.GET else None

    return rawResponse( json.dumps( objs ), status=200, content='application/json', callback=callback )

  #Return an error response
def errResponse( request, reason, extra={} ):
    print( reason )
    objs = { 'successful': False, 'reason': reason }
    objs.update( extra )
    callback = request.GET['callback'] if 'callback' in request.GET else None

    return rawResponse( json.dumps( objs ), status=201, content='application/json', callback=callback )

  #Raw response Info
def rawResponse( objs, status, content, callback=None ):
    if callback:
        return HttpResponse( "%s(%s)" % (callback, objs),
                             status=status, content_type=content )
    else:
        return HttpResponse( objs, status=status, content_type=content )
