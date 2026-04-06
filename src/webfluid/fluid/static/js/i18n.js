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

        const config = await fetch("/server-config")
            .then(res => res.json())
            .catch(() => ({}))
        this.frameworkFallback = config?.framework_id

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

    _(message) {
        const pluralForm = this.pluralForm(1)
        const get = (domain) => {
            return (
                (this.translations[domain] || {})
                    [`${pluralForm}:${message}`] || {}
            )[""]
        }

        for (const domain of this.fallbackEscalation()) {
            const msg = get(domain)
            if (msg) return msg
        }

        return message
    }

    _n(singular, plural, num) {
        let msg

        if (num === 1) msg = singular
        else msg = plural

        const pluralForm = this.pluralForm(num)
        const get = (domain) => {
            return (
                (this.translations[domain] || {}
                )[`${pluralForm}:${msg}`] || {}
            )[""]
        }

        for (const domain of this.fallbackEscalation()) {
            const m = get(domain)
            if (m) return m
        }

        return  msg
    }

    _p(context, message) {
        const pluralForm = this.pluralForm(1)
        const get = (domain) => {
            return (
                (this.translations[domain] || {}
                )[`${pluralForm}:${message}`] || {}
            )[context]
        }

        for (const domain of this.fallbackEscalation()) {
            const msg = get(domain)
            if (msg) return msg
        }

        return this._(message)
    }

    _np(context, singular, plural, num) {
        let msg

        if (num === 1) msg = singular
        else msg = plural

        const pluralForm = this.pluralForm(num)
        const get = (domain) => {
            return (
                (this.translations[domain] || {}
                )[`${pluralForm}:${msg}`] || {}
            )[context]
        }

        for (const domain of this.fallbackEscalation()) {
            const m = get(domain)
            if (m) return m
        }

        return this._n(singular, plural, num)
    }
}

async function loadTranslations(locale) {
    const data = await request("cache", { locale })
    localStorage.setItem("i18n", JSON.stringify(data || {}))
    return data
}

window.wf.ext.i18n = { Translations, i18nRequest: request }
