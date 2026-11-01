import { createWS } from "./base.js"

const { request } = createWS("/ws/events")


export class EventBus {
    constructor() {
        this._events = {}
        this._break_flag = {}
        this._event_loops = {}
    }

    async _event_loop(event){
        if (!this._events[event]) return

        const listen = () => request("listen", event, { timeout: 0 })
        let listener = listen()
        let attempt = 0

        while (!this._break_flag[event]) {
            try {
                const response = await listener
                if (this._break_flag[event]) break
                attempt = 0
                listener = listen()

                for (const handler of this._events[event].handlers) {
                    handler(response)
                }
            } catch (error) {
                if (this._break_flag[event]) break
                const reason = String(error?.message ?? error)

                if (reason === "timeout") {
                    listener = listen()
                    continue
                }

                if (reason === "socket closed" || reason.includes("not subscribed")) {
                    await new Promise(resolve => setTimeout(resolve, Math.min(500 * 2 ** attempt++, 10000)))
                    if (this._break_flag[event]) break
                    if (!await this._resubscribe(event)) continue
                    listener = listen()
                    continue
                }

                console.error("Error while listening:", error)
                break
            }
        }
    }

    async _resubscribe(event) {
        try {
            return !!await request("subscribe", event)
        } catch (error) {
            return String(error?.message ?? error).includes("already been subscribed")
        }
    }

    registerHandler(event, handler) {
        if (!this._events[event]) throw new Error("Event not subscribed: " + event)
        this._events[event].handlers.push(handler)

        return () => {
            const handlers = this._events[event]?.handlers
            if (!handlers) return
            const i = handlers.indexOf(handler)
            if (i !== -1) handlers.splice(i, 1)
        }
    }

    async subscribe(event) {
        if (this._events[event]) {
            this._events[event].refs++
            return
        }

        this._events[event] = { handlers: [], refs: 1 }
        this._break_flag[event] = false

        try {
            const response = await request("subscribe",  event)
            if (!response) {
                console.error("Error while subscribing... ", response)
                delete this._events[event]
                return
            }

            this._event_loops[event] = this._event_loop(event)
        } catch (error) {
            console.error("Error while subscribing: ", error)
            delete this._events[event]
        }
    }

    async unsubscribe(event) {
        const entry = this._events[event]
        if (!entry) return
        if (--entry.refs > 0) return

        delete this._events[event]
        this._break_flag[event] = true
        delete this._event_loops[event]

        try {
            const response = await request("unsubscribe",  event)
            if (!response) console.error("Error while unsubscribing... ", response)
        } catch (error) {
            console.error("Error while unsubscribing: ", error)
        }
    }
    
    async request(query, data=null) {
        try {
            const response = await request("request",  { query, data })
            if (!response) {
                console.error("Error while requesting... ", response)
                return
            }
            return response
        } catch (error) {
            console.error("Error while requesting: ", error)
        }
    }

    async trigger(event, data=null) {
        try {
            const response = await request("trigger",  { event, data })
            if (!response) {
                console.error("Error while triggering... ", response)
            }
        } catch (error) {
            console.error("Error while triggering: ", error)
        }
    }
}


window.wf.ext.events = { EventBus, eventRequest: request }
