
_default = "{}"

_keys = [
    "BRAND",

    "ERROR",
    "ERROR_TITLE",
    "ERROR_MSG",
    "NOT_FOUND_TITLE",
    "NOT_FOUND_MSG",
    "FORBIDDEN_TITLE",
    "FORBIDDEN_MSG",
    "BACK_HOME",

    "BAD_REQUEST_TITLE",
    "BAD_REQUEST_MSG",
    "UNAUTHORIZED_TITLE",
    "UNAUTHORIZED_MSG",
    "NOT_ALLOWED_TITLE",
    "NOT_ALLOWED_MSG",
    "TOO_MANY_TITLE",
    "TOO_MANY_MSG",
    "BAD_GATEWAY_TITLE",
    "BAD_GATEWAY_MSG",
    "UNAVAILABLE_TITLE",
    "UNAVAILABLE_MSG",

]

translations = lambda: {
    "en": {
        _keys[0]: {
            _default: "WebFluid"
        },

        _keys[1]: {
            _default: "Error"
        },
        _keys[2]: {
            _default: "Internal Server Error"
        },
        _keys[3]: {
            _default: "Something went wrong, please try again later."
        },
        _keys[4]: {
            _default: "Not Found"
        },
        _keys[5]: {
            _default: "The page you are looking for is not available."
        },
        _keys[6]: {
            _default: "Forbidden"
        },
        _keys[7]: {
            _default: "You are not authorized to access this page."
        },
        _keys[8]: {
            _default: "Back Home"
        },

        _keys[9]: {
            _default: "Bad Request"
        },
        _keys[10]: {
            _default: "The request could not be understood by the server."
        },
        _keys[11]: {
            _default: "Unauthorized"
        },
        _keys[12]: {
            _default: "You need to sign in to access this page."
        },
        _keys[13]: {
            _default: "Method Not Allowed"
        },
        _keys[14]: {
            _default: "This method is not allowed on the requested resource."
        },
        _keys[15]: {
            _default: "Too Many Requests"
        },
        _keys[16]: {
            _default: "You are sending requests too quickly, please slow down."
        },
        _keys[17]: {
            _default: "Bad Gateway"
        },
        _keys[18]: {
            _default: "The upstream server sent an invalid response."
        },
        _keys[19]: {
            _default: "Service Unavailable"
        },
        _keys[20]: {
            _default: "The service is temporarily unavailable, please try again later."
        },

    },
    "de": {
        _keys[0]: {
            _default: "WebFluid"
        },

        _keys[1]: {
            _default: "Fehler"
        },
        _keys[2]: {
            _default: "Interner Serverfehler"
        },
        _keys[3]: {
            _default: "Etwas ist schiefgelaufen, bitte versuche es später erneut."
        },
        _keys[4]: {
            _default: "Nicht gefunden"
        },
        _keys[5]: {
            _default: "Die angefragte Seite konnte nicht gefunden werden."
        },
        _keys[6]: {
            _default: "Gesperrt"
        },
        _keys[7]: {
            _default: "Du bist nicht berechtigt, auf diese Seite zuzugreifen."
        },
        _keys[8]: {
            _default: "Zur Startseite"
        },

        _keys[9]: {
            _default: "Ungültige Anfrage"
        },
        _keys[10]: {
            _default: "Die Anfrage konnte vom Server nicht verarbeitet werden."
        },
        _keys[11]: {
            _default: "Nicht angemeldet"
        },
        _keys[12]: {
            _default: "Du musst dich anmelden, um auf diese Seite zuzugreifen."
        },
        _keys[13]: {
            _default: "Methode nicht erlaubt"
        },
        _keys[14]: {
            _default: "Diese Methode ist für die angefragte Ressource nicht erlaubt."
        },
        _keys[15]: {
            _default: "Zu viele Anfragen"
        },
        _keys[16]: {
            _default: "Du sendest zu viele Anfragen, bitte verlangsame das Tempo."
        },
        _keys[17]: {
            _default: "Ungültiges Gateway"
        },
        _keys[18]: {
            _default: "Der vorgelagerte Server hat eine ungültige Antwort gesendet."
        },
        _keys[19]: {
            _default: "Dienst nicht verfügbar"
        },
        _keys[20]: {
            _default: "Der Dienst ist vorübergehend nicht verfügbar, bitte versuche es später erneut."
        },

    }
}
