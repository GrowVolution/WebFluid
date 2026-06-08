import { createWS } from "./base.js"

const { request } = createWS("/ws/i18n")


export class Translations {
    constructor(locale=null, defaultDomain="messages") {
        this.locale = locale
        this.defaultDomain = defaultDomain
        this.currentDomain = defaultDomain
        this.fallbackDomain = "__fallback__"
        this.frameworkFallback = null

        const lc = this.locale?.replace("_", "-")
        this.pluralForm = (n) =>
            new Intl.PluralRules(lc).select(n)
    }

    async init() {
        let data = localStorage.getItem("i18n")

        if (data === null) {
            await this.update()
        } else {
            const { locale, translations } = JSON.parse(data)
            if (locale !== this.locale) {
                await this.update()
            } else {
                this.translations = translations
            }
        }

        const identity = await fetch("/wf-identity")
            .then(res => res.json())
            .catch(() => ({ id: "fluid" }))
        this.frameworkFallback = identity?.id

        return this
    }

    async update() {
        const { locale, translations } = await loadTranslations(this.locale)
        this.locale = locale
        this.translations = translations
    }

    withDomain(domain, handler) {
        return new Promise((resolve) => {
            this.currentDomain = domain
            const result = handler()
            this.currentDomain = this.defaultDomain
            resolve(result)
        })
    }

    fallbackEscalation() {
        const escalation = [this.currentDomain]
        if (this.defaultDomain !== this.currentDomain)
            escalation.push(this.defaultDomain)
        escalation.push(this.fallbackDomain)
        escalation.push(this.frameworkFallback)
        return escalation
    }

    format(result, variables) {
        for (const [key, value] of Object.entries(variables))
            result = result.replaceAll(
                new RegExp(`%\\(${key}\\)[a-z]`, 'g'),
                value
            )
        return result
    }

    _(message, variables = {}) {
        return this.format((() => {
            const pluralForm = this.pluralForm(1)
            const get = (domain) => {
                return (((this.translations[domain] || {})
                    [message] || {})[pluralForm] || {})[""]
            }

            for (const domain of this.fallbackEscalation()) {
                const msg = get(domain)
                if (msg) return msg
            }

            return message
        })(), variables)
    }

    _n(singular, plural, num, variables = {}) {
        variables["num"] = num

        return this.format((() => {
            let msg

            if (num === 1) msg = singular
            else msg = plural

            const pluralForm = this.pluralForm(num)
            const get = (domain) => {
                return (((this.translations[domain] || {})
                    [msg] || {})[pluralForm] || {})[""]
            }

            for (const domain of this.fallbackEscalation()) {
                const m = get(domain)
                if (m) return m
            }

            return  msg
        })(), variables)
    }

    _p(context, message, variables = {}) {
        return this.format((() => {
            const pluralForm = this.pluralForm(1)
            const get = (domain) => {
                return (((this.translations[domain] || {})
                    [message] || {})[pluralForm] || {})[context]
            }

            for (const domain of this.fallbackEscalation()) {
                const msg = get(domain)
                if (msg) return msg
            }

            return this._(message)
        })(), variables)
    }

    _np(context, singular, plural, num, variables = {}) {
        return this.format((() => {
            let msg

            if (num === 1) msg = singular
            else msg = plural

            const pluralForm = this.pluralForm(num)
            const get = (domain) => {
                return (((this.translations[domain] || {})
                    [msg] || {})[pluralForm] || {})[context]
            }

            for (const domain of this.fallbackEscalation()) {
                const m = get(domain)
                if (m) return m
            }

            return this._n(singular, plural, num)
        })(), variables)
    }

    live = {
        _: async (string, variables = {}) => await request(
            "translate", {
                domain: this.currentDomain,
                args: [ string ], variables
            }
        ),
        _n: async (singular, plural, num, variables = {}) => await request(
            "translate", {
                fn: "ngettext", domain: this.currentDomain,
                args: [ singular, plural, num ], variables
            }
        ),
        _p: async (context, string, variables = {}) => await request(
            "translate", {
                fn: "pgettext", domain: this.currentDomain,
                args: [ string, context ], variables
            }
        ),
        _np: async (context, singular, plural, num, variables = {}) => await request(
            "translate", {
                fn: "npgettext", domain: this.currentDomain,
                args: [ singular, plural, num, context ], variables
            }
        )
    }
}

async function loadTranslations(locale) {
    const data = await request("cache", { locale })
    localStorage.setItem("i18n", JSON.stringify(data || {}))
    return data
}

window.wf.ext.i18n = { Translations, i18nRequest: request }
