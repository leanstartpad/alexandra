from werkzeug.exceptions import abort

from alexandra.session import Session
from alexandra.util import respond
from alexandra.wsgi import WsgiApp


class Application:
    def __init__(self):
        self.intent_map = {}
        self.unknown_intent_fn = lambda x, y: respond(text='unknown intent')
        self.launch_fn = lambda _: respond
        self.session_end_fn = respond


    def create_wsgi_app(self, validate_requests=True):
        """Return an object that can be run by any WSGI server (uWSGI,
        etc.) to serve this Alexa application.
        """

        return WsgiApp(self, validate_requests)

    def run_debug(self, host, port, validate_requests=True):
        """Utility method to quickly get a test server up and running.

        :param validate_requests: if is False, no checking will be done to
            ensure that requests are sent by Amazon. This can be useful
            for manually testing the server.
        """

        from werkzeug.serving import run_simple

        app = self.create_wsgi_app(validate_requests)
        run_simple(host, port, app, use_reloader=True, use_debugger=True)

    def dispatch_request(self, body):
        """Called by WsgiApp """
        req_type = body['request']['type']
        session = Session(body.get('session', {}))

        if req_type == 'LaunchRequest':
            return self.launch_fn(session)

        elif req_type == 'IntentRequest':
            intent = body['request']['intent']['name']
            intent_fn = self.intent_map.get(intent, self.unknown_intent_fn)

            slots = {
                slot['name']: slot['value']
                for _, slot in
                body['request']['intent'].get('slots', {}).iteritems()
            }

            return intent_fn(slots, session)

        elif req_type == 'SessionEndedRequest':
            return self.session_end_fn()

        abort(400)

    def launch(self, func):
        """Decorator to register a function to be called whenever the
        app receives a LaunchRequest (which happens when someone
        invokes your skill without specifying an intent).

        ```
        @alexa_app.launch
        def launch_handler(session):
            pass
        ```
        """

        self.launch_fn = func
        return func

    def intent(self, intent_name):
        """Decorator to register a handler for the given intent. The
        decorated function should take two arguments: a map containing
        the slots in the IntentRequest, and a Session object.

        ```
        @alexa_app.intent('FooBarBaz')
        def foo_bar_baz_intent(slots, session):
            pass
        ```
        """

        # nested decorator so we can have params.
        def _decorator(func):
            self.intent_map[intent_name] = func
            return func

        return _decorator

    def unknown_intent(self, func):
        """Decorator to register a function to be called when an unknown intent
        is received. This should only happen when the intents/utterance file
        are malformed.
        """

        self.unknown_intent_fn = func
        return func

    def session_end(self, func):
        """ Decorator to register a function to be called when a
        SessionEndedRequest is received.
        """

        self.session_end_fn = func
        return func
