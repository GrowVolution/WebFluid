import { createWS } from "./base.js"

const { request } = createWS("/ws/events")


export class EventManager {
    constructor() {
        this._events = {}
        this._break_flag = {}
        this._event_loops = {}
    }

    async _event_loop(event){
        if (!this._events[event]) return

        let listener = request("listen", event)

        while (!this._break_flag[event]) {
            try {
                const response = await listener
                if (this._break_flag[event]) break
                listener = request("listen", event)

                for (const handler of this._events[event].handlers) {
                    handler(response)
                }
            } catch (error) {
                if (error === "timeout" || error?.message === "timeout") {
                    listener = request("listen", event)
                    continue
                }

                console.error("Error while listening:", error)
                break
            }
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


window.wf.ext.events = { EventManager, eventRequest: request }
