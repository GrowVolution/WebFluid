import { createWS } from "./base.js"

const { request } = createWS("/ws/i18n")

export class Translations {
    constructor(locale=null, defaultDomain="messages") {
        this.locale = locale
        this.currentDomain = defaultDomain

        const lc = this.locale?.replace("_", "-")
        this.pluralForm = (n) =>
            new Intl.PluralRules(lc).select(n)
    }

    async init() {
        let translations = localStorage.getItem("i18n")

        if (translations === null) {
            await this.update()
        } else {
            this.translations = JSON.parse(translations)
        }

        return this
    }

    async update() {
        this.translations = await loadTranslations(this.locale)
    }

    withDomain(domain, handler) {
        return new Promise((resolve) => {
            const defaultDomain = this.currentDomain
            this.currentDomain = domain
            const result = handler()
            this.currentDomain = defaultDomain
            resolve(result)
        })
    }

    _(message) {
       return (
           (this.translations[this.currentDomain] || {}
           )[`${this.pluralForm(1)}:${message}`] || {}
       )[""] || message
    }

    _n(singular, plural, num) {
        let msg

        if (num === 1) msg = singular
        else msg = plural

        return (
            (this.translations[this.currentDomain] || {}
            )[`${this.pluralForm(num)}:${msg}`] || {}
        )[""] || msg
    }

    _p(context, message) {
        return (
            (this.translations[this.currentDomain] || {}
            )[`${this.pluralForm(1)}:${message}`] || {}
        )[context] || this._(message)
    }

    _np(context, singular, plural, num) {
        let msg

        if (num === 1) msg = singular
        else msg = plural

        return (
            (this.translations[this.currentDomain] || {}
            )[`${this.pluralForm(num)}:${msg}`] || {}
        )[context] || this._n(singular, plural, num)
    }
}

async function loadTranslations(locale) {
    const translations = await request("cache", { locale })
    localStorage.setItem("i18n", JSON.stringify(translations || {}))
    return translations
}

window.wf.ext.i18n = { Translations, i18nRequest: request }
