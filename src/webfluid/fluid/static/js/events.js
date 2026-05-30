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

                for (const handler of this._events[event]) {
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
        this._events[event].push(handler)
    }

    async subscribe(event) {
        if (this._events[event]) throw new Error("Event already subscribed: " + event)

        try {
            const response = await request("subscribe",  event)
            if (!response) {
                console.error("Error while subscribing... ", response)
                return
            }

            this._events[event] = []
            this._break_flag[event] = false
            this._event_loops[event] = this._event_loop(event)
        } catch (error) {
            console.error("Error while subscribing: ", error)
        }
    }

    async unsubscribe(event) {
        if (!this._events[event]) throw new Error("Event not subscribed: " + event)

        try {
            const response = await request("unsubscribe",  event)
            if (!response) {
                console.error("Error while unsubscribing... ", response)
                return
            }

            delete this._events[event]
            this._break_flag[event] = true
            await this._event_loops[event]
            delete this._event_loops[event]
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
}


window.wf.ext.events = { EventManager, eventRequest: request }
